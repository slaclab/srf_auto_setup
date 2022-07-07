import dataclasses
from typing import Dict, List

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)
from lcls_tools.common.pyepics_tools.pyepicsUtils import PV, PVInvalidError
from lcls_tools.superconducting.scLinac import L1BHL, LINAC_TUPLES
from lcls_tools.superconducting.scLinacUtils import SSACalibrationError, StepperError
from pydm import Display
from pydm.widgets import PyDMLabel
from qtpy.QtCore import Signal

from auto_setup import DetuneError, SETUP_CRYOMODULES, SSACalError, SetupCavity


class Worker(QThread):
    finished = Signal(str)
    progress = Signal(int)
    error = Signal(str)
    status = Signal(str)
    
    def __init__(self, cavity: SetupCavity, desAmp: float = 5):
        super().__init__()
        self.cavity: SetupCavity = cavity
        self.desAmp = desAmp
    
    def run(self):
        try:
            self.status.emit("Setting Up")
            self.cavity.setup(self.desAmp)
            self.status.emit("Cavity Set Up")
        except (StepperError, DetuneError, SSACalError,
                SSACalibrationError, PVInvalidError) as e:
            self.error.emit(str(e))


@dataclasses.dataclass
class GUICavity:
    number: int
    prefix: str
    cm: str
    
    def __post_init__(self):
        self.amax_pv: PV = PV(self.prefix + "ADES_MAX")
        self.setup_button = QPushButton(f"Set Up Cavity {self.number}")
        self.worker = None
        self.setup_button.clicked.connect(self.launch_worker)
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.prefix + "AACTMEAN")
        self.readback_label.showUnits = True
        
        # Putting this here because it otherwise gets garbage collected (?!)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setValue(5)
        
        self.status_label: QLabel = QLabel("Ready for Setup")
    
    def launch_worker(self):
        self.worker = Worker(SETUP_CRYOMODULES[self.cm].cavities[self.number],
                             self.spinbox.value())
        self.worker.error.connect(print)
        self.worker.error.connect(self.status_label.setText)
        self.worker.status.connect(self.status_label.setText)
        self.worker.start()


@dataclasses.dataclass
class GUICryomodule:
    linac_idx: int
    name: str
    
    def __post_init__(self):
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.editingFinished.connect(self.set_cavity_amps)
        self.spinbox.setValue(40)
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.linac_idx}B:{self.name}00:AACTMEANSUM")
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        self.setup_button.clicked.connect(self.launch_cavity_workers)
        self.gui_cavities: Dict[int, GUICavity] = {}
        
        for cav_num in range(1, 9):
            gui_cavity = GUICavity(cav_num,
                                   f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:",
                                   self.name)
            self.gui_cavities[cav_num] = gui_cavity
    
    def launch_cavity_workers(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.launch_worker()
            
    def set_cavity_amps(self):
        cav_des_amp = self.spinbox.value()/8.0
        total_remainder = 0.0
        cavities_at_amax = []
        
        for gui_cavity in self.gui_cavities.values():
            if gui_cavity.amax_pv.value < cav_des_amp:
                total_remainder += cav_des_amp - gui_cavity.amax_pv.value
                
        cav_remainder = total_remainder/(8 - len(cavities_at_amax))
        
        for cavity_num, gui_cavity in self. gui_cavities.items():
            if cavity_num in cavities_at_amax:
                gui_cavity.spinbox.setValue(gui_cavity.amax_pv.value)
            else:
                gui_cavity.spinbox.setValue(cav_des_amp + cav_remainder)
            
            


@dataclasses.dataclass
class Linac:
    name: str
    idx: int
    cryomodule_names: List[str]
    
    def __post_init__(self):
        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.setup_button.clicked.connect(self.launch_cm_workers)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setRange(0, 16.6 * 8 * len(self.cryomodule_names))
        self.spinbox.setValue(40 * len(self.cryomodule_names))
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.idx}B:1:AACTMEANSUM")
        self.cryomodules: List[GUICryomodule] = []
        self.cm_tab_widget: QTabWidget = QTabWidget()
        self.cm_widgets: Dict[str, GUICryomodule] = {}
        
        for cm_name in self.cryomodule_names:
            self.add_cm_tab(cm_name)
    
    def launch_cm_workers(self):
        for cm_widget in self.cm_widgets.values():
            cm_widget.launch_cavity_workers()
    
    def add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")
        
        widgets = GUICryomodule(linac_idx=self.idx, name=cm_name)
        self.cm_widgets[cm_name] = widgets
        hlayout: QHBoxLayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QLabel(f"CM{cm_name} Amplitude:"))
        hlayout.addWidget(widgets.spinbox)
        hlayout.addWidget(QLabel("MV"))
        hlayout.addWidget(widgets.readback_label)
        hlayout.addWidget(widgets.setup_button)
        hlayout.addStretch()
        
        vlayout.addLayout(hlayout)
        
        groupbox: QGroupBox = QGroupBox()
        all_cav_layout: QGridLayout = QGridLayout()
        groupbox.setLayout(all_cav_layout)
        vlayout.addWidget(groupbox)
        for cav_num in range(1, 9):
            cav_groupbox: QGroupBox = QGroupBox(f"CM{cm_name} Cavity {cav_num}")
            cav_layout: QVBoxLayout = QVBoxLayout()
            cav_groupbox.setLayout(cav_layout)
            cav_widgets = widgets.gui_cavities[cav_num]
            cav_hlayout_des: QHBoxLayout = QHBoxLayout()
            cav_hlayout_des.addStretch()
            cav_hlayout_des.addWidget(QLabel("Desired: "))
            cav_hlayout_des.addWidget(cav_widgets.spinbox)
            cav_hlayout_des.addWidget(QLabel("MV"))
            cav_hlayout_des.addStretch()
            cav_hlayout_act: QHBoxLayout = QHBoxLayout()
            cav_hlayout_act.addStretch()
            cav_hlayout_act.addWidget(QLabel("Actual: "))
            cav_hlayout_act.addWidget(cav_widgets.readback_label)
            cav_hlayout_act.addWidget(QLabel("MV"))
            cav_hlayout_act.addStretch()
            cav_layout.addLayout(cav_hlayout_des)
            cav_layout.addLayout(cav_hlayout_act)
            cav_layout.addWidget(cav_widgets.setup_button)
            cav_layout.addWidget(cav_widgets.status_label)
            all_cav_layout.addWidget(cav_groupbox,
                                     0 if cav_num in range(1, 5) else 1,
                                     (cav_num - 1) % 4)


class SetupGUI(Display):
    def ui_filename(self):
        return 'setup.ui'
    
    def add_linac_tab(self, linac_idx: int):
        pass
    
    def __init__(self, parent=None, args=None):
        super(SetupGUI, self).__init__(parent=parent, args=args)
        self.ui.machine_spinbox.setRange(0, 37 * 8 * 16.6)
        self.ui.machine_spinbox.setValue(40 * 37)
        self.linac_widgets: List[Linac] = []
        for linac_idx in range(0, 4):
            self.linac_widgets.append(Linac(f"L{linac_idx}B", linac_idx, LINAC_TUPLES[linac_idx][1]))
        
        self.linac_widgets.insert(2, Linac("L1BHL", 1, L1BHL))
        
        linac_tab_widget: QTabWidget = self.ui.tabWidget_linac
        
        for linac in self.linac_widgets:
            page: QWidget = QWidget()
            vlayout: QVBoxLayout = QVBoxLayout()
            page.setLayout(vlayout)
            linac_tab_widget.addTab(page, linac.name)
            
            hlayout: QHBoxLayout = QHBoxLayout()
            hlayout.addStretch()
            hlayout.addWidget(QLabel(f"{linac.name} Amplitude:"))
            hlayout.addWidget(linac.spinbox)
            hlayout.addWidget(QLabel("MV"))
            hlayout.addWidget(linac.readback_label)
            hlayout.addWidget(linac.setup_button)
            hlayout.addStretch()
            
            vlayout.addLayout(hlayout)
            vlayout.addWidget(linac.cm_tab_widget)
