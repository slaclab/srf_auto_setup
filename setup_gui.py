import dataclasses
from typing import Dict, List

from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)
from lcls_tools.superconducting.scLinac import L1BHL, LINAC_TUPLES
from pydm import Display
from pydm.widgets import PyDMLabel


@dataclasses.dataclass
class Cavity:
    number: int
    prefix: str
    
    def __post_init__(self):
        self.setup_button = QPushButton(f"Set Up Cavity {self.number}")
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.prefix + "AACT")
        self.readback_label.showUnits = True
        
        # Putting this here because it otherwise gets garbage collected (?!)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setValue(5)


@dataclasses.dataclass
class Cryomodule:
    linac_idx: int
    name: str
    
    def __post_init__(self):
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setValue(40)
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.linac_idx}B:{self.name}00:AACTMEANSUM")
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        self.cavity_widgets: Dict[int, Cavity] = {}
        for cav_num in range(1, 9):
            self.cavity_widgets[cav_num] = Cavity(cav_num,
                                                  f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:")


@dataclasses.dataclass
class Linac:
    name: str
    idx: int
    cryomodule_names: List[str]
    
    def __post_init__(self):
        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()
        self.spinbox.setRange(0, 16.6 * 8 * len(self.cryomodule_names))
        self.spinbox.setValue(40 * len(self.cryomodule_names))
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.idx}B:1:AACTMEANSUM")
        self.cryomodules: List[Cryomodule] = []
        self.cm_tab_widget: QTabWidget = QTabWidget()
        self.cm_widgets: Dict[str, Cryomodule] = {}
        
        for cm_name in self.cryomodule_names:
            self.add_cm_tab(cm_name)
    
    def add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")
        
        widgets = Cryomodule(linac_idx=self.idx, name=cm_name)
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
            cav_widgets = widgets.cavity_widgets[cav_num]
            cav_hlayout: QHBoxLayout = QHBoxLayout()
            cav_hlayout.addWidget(cav_widgets.spinbox)
            cav_hlayout.addWidget(QLabel("MV"))
            cav_hlayout.addWidget(cav_widgets.readback_label)
            cav_layout.addLayout(cav_hlayout)
            cav_layout.addWidget(cav_widgets.setup_button)
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
