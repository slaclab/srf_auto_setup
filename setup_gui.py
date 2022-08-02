import dataclasses
from time import sleep
from typing import Callable, Dict, List

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QMessageBox, QPushButton,
                             QRadioButton, QTabWidget, QVBoxLayout, QWidget)
from epics import caget, camonitor
from lcls_tools.common.pyepics_tools.pyepicsUtils import PVInvalidError
from lcls_tools.superconducting import scLinacUtils
from lcls_tools.superconducting.scLinac import (CRYOMODULE_OBJECTS, Cavity,
                                                L1BHL, LINAC_TUPLES)
from pydm import Display
from pydm.widgets import PyDMLabel
from qtpy.QtCore import Signal, Slot


class Worker(QThread):
    finished = Signal(str)
    progress = Signal(int)
    error = Signal(str)
    status = Signal(str)
    
    def __init__(self, cavity: Cavity, desAmp: float = 5, selap=True):
        super().__init__()
        self.cavity: Cavity = cavity
        self.desAmp = desAmp
        self.selap = selap
    
    def run(self):
        try:
            if not self.desAmp:
                self.status.emit(f"Ignoring CM{self.cavity.cryomodule.name}"
                                 f" cavity {self.cavity.number}")
            else:
                if self.selap:
                    self.status.emit("Setting up in SELAP")
                    self.cavity.setup_SELAP(self.desAmp)
                    self.status.emit("Cavity set up in SELAP")
                else:
                    self.status.emit("Setting up in SELA")
                    self.cavity.setup_SELA(self.desAmp)
                    self.status.emit("Cavity set up in SELA")
        except (scLinacUtils.StepperError, scLinacUtils.DetuneError,
                scLinacUtils.SSACalibrationError, PVInvalidError,
                scLinacUtils.QuenchError,
                scLinacUtils.CavityQLoadedCalibrationError,
                scLinacUtils.CavityScaleFactorCalibrationError,
                scLinacUtils.SSAFaultError) as e:
            self.error.emit(str(e))


@Slot(str)
def handle_error(message: str):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error")
    msg.setInformativeText(message)
    msg.setWindowTitle("Error")
    msg.exec_()


@dataclasses.dataclass
class GUICavity:
    number: int
    prefix: str
    cm: str
    cm_spinbox_update_func: Callable
    cm_spinbox_range_func: Callable
    sela_button: QRadioButton
    selap_button: QRadioButton
    
    def __post_init__(self):
        self.amax_pv: str = self.prefix + "ADES_MAX"
        self.setup_button = QPushButton(f"Set Up Cavity {self.number}")
        self.worker = None
        self.setup_button.clicked.connect(self.launch_worker)
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.prefix + "AACTMEAN")
        self.readback_label.showUnits = True
        
        # Putting this here because it otherwise gets garbage collected (?!)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setToolTip("Press enter to update CM and Linac spinboxes")
        self.spinbox.setValue(5)
        
        while caget(self.amax_pv) is None:
            print(f"waiting for {self.amax_pv} to connect")
            sleep(0.0001)
        
        self.spinbox.setRange(0, caget(self.amax_pv))
        
        self.status_label: QLabel = QLabel("Ready for Setup")
    
    def connect_spinbox(self):
        self.spinbox.editingFinished.connect(self.cm_spinbox_update_func)
        camonitor(self.amax_pv, callback=self.amax_callback)
    
    def launch_worker(self):
        self.worker = Worker(CRYOMODULE_OBJECTS[self.cm].cavities[self.number],
                             self.spinbox.value(),
                             selap=self.selap_button.isChecked())
        self.worker.error.connect(print)
        self.worker.error.connect(self.status_label.setText)
        self.worker.error.connect(handle_error)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(print)
        self.worker.start()
    
    def amax_callback(self, value, **kwargs):
        self.spinbox.setRange(0, value)
        self.cm_spinbox_range_func()


@dataclasses.dataclass
class GUICryomodule:
    linac_idx: int
    name: str
    sela_button: QRadioButton
    selap_button: QRadioButton
    
    def __post_init__(self):
        
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setValue(40)
        self.spinbox.setToolTip("Press enter to update cavity spinboxes")
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.linac_idx}B:{self.name}00:AACTMEANSUM")
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        self.setup_button.clicked.connect(self.launch_cavity_workers)
        self.gui_cavities: Dict[int, GUICavity] = {}
        
        for cav_num in range(1, 9):
            gui_cavity = GUICavity(cav_num,
                                   f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:",
                                   self.name, self.update_amp, self.update_max_amp,
                                   sela_button=self.sela_button,
                                   selap_button=self.selap_button)
            self.gui_cavities[cav_num] = gui_cavity
        
        self.max_amp = 0
        self.amax_pv = f"ACCL:L{self.linac_idx}B:{self.name}00:ADES_MAX"
        self.update_max_amp()
        
        for gui_cavity in self.gui_cavities.values():
            gui_cavity.connect_spinbox()
        
        self.spinbox.editingFinished.connect(self.set_cavity_amps)
    
    def update_max_amp(self):
        max_amp = caget(self.amax_pv)
        
        print(f"CM{self.name} max amp: {max_amp}")
        self.spinbox.setRange(0, max_amp)
    
    def launch_cavity_workers(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.launch_worker()
    
    def update_amp(self):
        total_amp = 0
        for cavity_widget in self.gui_cavities.values():
            total_amp += cavity_widget.spinbox.value()
        
        if total_amp == self.spinbox.value():
            return
        
        self.spinbox.setValue(total_amp)
    
    def set_cavity_amps(self):
        cav_des_amp = self.spinbox.value() / 8.0
        total_remainder = 0.0
        cavities_at_amax = []
        current_sum = 0.0
        
        for gui_cavity in self.gui_cavities.values():
            current_sum += gui_cavity.spinbox.value()
            if caget(gui_cavity.amax_pv) < cav_des_amp:
                total_remainder += cav_des_amp - caget(gui_cavity.amax_pv)
                cavities_at_amax.append(gui_cavity.number)
        
        if current_sum == self.spinbox.value():
            return
        
        cav_remainder = total_remainder / (8 - len(cavities_at_amax))
        
        for cavity_num, gui_cavity in self.gui_cavities.items():
            if cavity_num in cavities_at_amax:
                gui_cavity.spinbox.setValue(caget(gui_cavity.amax_pv))
            else:
                gui_cavity.spinbox.setValue(cav_des_amp + cav_remainder)


@dataclasses.dataclass
class Linac:
    name: str
    idx: int
    cryomodule_names: List[str]
    sela_button: QRadioButton
    selap_button: QRadioButton
    
    def __post_init__(self):
        self.amax = 0
        self.amax_pv = f"ACCL:L{self.idx}B:1:ADES_MAX"
        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.setup_button.clicked.connect(self.launch_cm_workers)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.update_amax()
        self.spinbox.setValue(40 * len(self.cryomodule_names))
        self.spinbox.setEnabled(False)
        self.aact_pv = f"ACCL:L{self.idx}B:1:AACTMEANSUM"
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.cryomodules: List[GUICryomodule] = []
        self.cm_tab_widget: QTabWidget = QTabWidget()
        self.gui_cryomodules: Dict[str, GUICryomodule] = {}
        
        for cm_name in self.cryomodule_names:
            self.add_cm_tab(cm_name)
    
    def update_amax(self):
        self.spinbox.setRange(0, caget(self.amax_pv))
    
    def update_cm_amps(self):
        # TODO distribute desired linac amplitude among component CMs
        pass
    
    def launch_cm_workers(self):
        for gui_cm in self.gui_cryomodules.values():
            gui_cm.launch_cavity_workers()
    
    def add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")
        
        gui_cryomodule = GUICryomodule(linac_idx=self.idx, name=cm_name,
                                       sela_button=self.sela_button,
                                       selap_button=self.selap_button)
        self.gui_cryomodules[cm_name] = gui_cryomodule
        hlayout: QHBoxLayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QLabel(f"CM{cm_name} Amplitude:"))
        hlayout.addWidget(gui_cryomodule.spinbox)
        hlayout.addWidget(QLabel("MV"))
        hlayout.addWidget(gui_cryomodule.readback_label)
        hlayout.addWidget(gui_cryomodule.setup_button)
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
            cav_widgets = gui_cryomodule.gui_cavities[cav_num]
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
        self.linac_widgets: List[Linac] = []
        for linac_idx in range(0, 4):
            self.linac_widgets.append(Linac(f"L{linac_idx}B", linac_idx,
                                            LINAC_TUPLES[linac_idx][1],
                                            sela_button=self.ui.sela_radio_button,
                                            selap_button=self.ui.selap_radio_button))
        
        self.linac_widgets.insert(2, Linac("L1BHL", 1, L1BHL,
                                           sela_button=self.ui.sela_radio_button,
                                           selap_button=self.ui.selap_radio_button))
        self.update_readback()
        
        self.update_amax()
        self.ui.machine_spinbox.setValue(40 * 37)
        
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
            camonitor(linac.aact_pv, callback=self.update_readback)
    
    def update_amax(self):
        amax = 0
        for linac in self.linac_widgets:
            amax += caget(linac.amax_pv)
            self.ui.machine_spinbox.setRange(0, amax)
    
    def update_readback(self, **kwargs):
        readback = 0
        for linac in self.linac_widgets:
            readback += caget(linac.aact_pv)
        self.ui.machine_readback_label.setText(str(readback))
