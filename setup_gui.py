import dataclasses
from typing import Dict

from PyQt5.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QPushButton,
                             QTabWidget, QWidget)
from lcls_tools.superconducting.scLinac import LINAC_TUPLES
from pydm import Display
from pydm.widgets import PyDMLabel


@dataclasses.dataclass
class Cavity:
    number: int
    aact_pv: str
    
    def __post_init__(self):
        self.setup_button = QPushButton(f"Set Up Cavity {self.number}")
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.spinbox: QDoubleSpinBox = QDoubleSpinBox()


@dataclasses.dataclass
class Cryomodule:
    linac_idx: int
    name: str
    spinbox: QDoubleSpinBox = QDoubleSpinBox()
    readback_label: QLabel = QLabel()
    
    def __post_init__(self):
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        self.cavity_widgets: Dict[int, Cavity] = {}
        for cav_num in range(1, 9):
            self.cavity_widgets[cav_num] = Cavity(cav_num,
                                                  f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:AACT")


class SetupGUI(Display):
    def ui_filename(self):
        return 'setup.ui'
    
    def add_cm_tab(self, cm_name: str, linac_idx: int, linac_tab_widget: QTabWidget):
        page: QWidget = QWidget()
        layout: QGridLayout = QGridLayout()
        page.setLayout(layout)
        linac_tab_widget.addTab(page, f"CM{cm_name}")
        
        widgets = Cryomodule(linac_idx=linac_idx, name=cm_name)
        self.cm_widgets[cm_name] = widgets
        layout.addWidget(widgets.spinbox, 0, 0)
        layout.addWidget(QLabel("MV"), 0, 1)
        layout.addWidget(QLabel("READBACK"), 0, 2)
        layout.addWidget(widgets.setup_button, 0, 3)
        
        groupbox: QGroupBox = QGroupBox()
        all_cav_layout: QGridLayout = QGridLayout()
        groupbox.setLayout(all_cav_layout)
        layout.addWidget(groupbox, 1, 0)
        for cav_num in range(1, 9):
            cav_groupbox: QGroupBox = QGroupBox()
            cav_layout: QGridLayout = QGridLayout()
            cav_groupbox.setLayout(cav_layout)
            cav_widgets = widgets.cavity_widgets[cav_num]
            cav_layout.addWidget(cav_widgets.spinbox, 0, 0)
            cav_layout.addWidget(QLabel("MV"), 0, 1)
            cav_layout.addWidget(cav_widgets.readback_label, 0, 2)
            cav_layout.addWidget(cav_widgets.setup_button, 1, 0)
            all_cav_layout.addWidget(cav_groupbox,
                                     0 if cav_num in range(1, 5) else 1,
                                     (cav_num - 1) % 4)
    
    def __init__(self, parent=None, args=None):
        super(SetupGUI, self).__init__(parent=parent, args=args)
        self.cm_widgets = {}
        l0b_tab_widget: QTabWidget = self.ui.tabWidget_l0b
        for cm_name in LINAC_TUPLES[0][1]:
            self.add_cm_tab(cm_name, 0, l0b_tab_widget)
