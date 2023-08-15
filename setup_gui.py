import dataclasses
from functools import partial
from typing import Dict, List

from PyQt5.QtCore import QThreadPool, Qt
from PyQt5.QtWidgets import (QCheckBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)
from edmbutton import PyDMEDMDisplayButton
from epics import camonitor
from lcls_tools.common.pydm_tools.displayUtils import (ERROR_STYLESHEET,
                                                       STATUS_STYLESHEET)
from lcls_tools.common.pyepics_tools.pyepics_utils import PV
from lcls_tools.superconducting import sc_linac_utils
from pydm import Display
from pydm.widgets import PyDMLabel, PyDMSpinbox

from setup_linac import SETUP_CRYOMODULES, SetupCavity


@dataclasses.dataclass
class Settings:
    ssa_cal_checkbox: QCheckBox
    auto_tune_checkbox: QCheckBox
    cav_char_checkbox: QCheckBox
    rf_ramp_checkbox: QCheckBox


@dataclasses.dataclass
class GUICavity:
    number: int
    prefix: str
    cm: str
    settings: Settings
    parent: Display

    def __post_init__(self):
        self._cavity: SetupCavity = None
        self.setup_button = QPushButton(f"Set Up")

        self.abort_button: QPushButton = QPushButton("Abort")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.cavity.trigger_abort)

        self.turn_off_button: QPushButton = QPushButton(f"Turn Off")
        self.turn_off_button.clicked.connect(self.cavity.trigger_shut_down)

        self.setup_button.clicked.connect(self.cavity.trigger_setup)
        self.aact_readback_label: PyDMLabel = PyDMLabel(init_channel=self.prefix + "AACTMEAN")
        self.aact_readback_label.alarmSensitiveBorder = True
        self.aact_readback_label.alarmSensitiveContent = True
        self.aact_readback_label.showUnits = True
        self.aact_readback_label.precisionFromPV = False
        self.aact_readback_label.precision = 2

        # Putting this here because it otherwise gets garbage collected (?!)
        self.ades_spinbox: PyDMSpinbox = PyDMSpinbox(init_channel=self.prefix + "ADES")
        self.ades_spinbox.ctrl_limit_changed = lambda *args: None
        self.ades_spinbox.alarmSensitiveContent = True
        self.ades_spinbox.alarmSensitiveBorder = True
        self.ades_spinbox.showUnits = True
        self.ades_spinbox.showStepExponent = False
        self.ades_spinbox.precisionFromPV = False
        self.ades_spinbox.precision = 2
        self.ades_spinbox.setRange(0, 21)
        self.ades_spinbox.update_format_string = partial(self.ades_spinbox.lineEdit().setToolTip,
                                                         "Press enter to execute ADES change")

        self.status_label: PyDMLabel = PyDMLabel(init_channel=self.cavity.status_msg_pv)
        self.status_label.setAlignment(Qt.AlignHCenter)
        self.status_label.setWordWrap(True)
        self.status_label.alarmSensitiveBorder = True
        self.status_label.alarmSensitiveContent = True

        self.expert_screen_button: PyDMEDMDisplayButton = PyDMEDMDisplayButton()
        self.expert_screen_button.filenames = ["$EDM/llrf/rf_srf_cavity_main.edl"]
        self.expert_screen_button.macros = self.cavity.edm_macro_string + (',' + "SELTAB=0,SELCHAR=3")
        self.expert_screen_button.setToolTip("EDM expert screens")

    def kill_workers(self):
        self.status_label.setText(f"Sending abort request for CM{self.cm} cavity {self.number}")
        self.status_label.setStyleSheet(STATUS_STYLESHEET)
        self.cavity.abort_flag = True
        self.cavity.steppertuner.abort_flag = True

    @property
    def cavity(self) -> SetupCavity:
        if not self._cavity:
            self._cavity = SETUP_CRYOMODULES[self.cm].cavities[self.number]
        return self._cavity

    def launch_off_worker(self):
        self.cavity.trigger_shut_down()

    def launch_ramp_worker(self):
        self.cavity.trigger_setup()


@dataclasses.dataclass
class GUICryomodule:
    linac_idx: int
    name: str
    settings: Settings
    parent: Display

    def __post_init__(self):

        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.linac_idx}B:{self.name}00:AACTMEANSUM")
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")

        self.abort_button: QPushButton = QPushButton(f"Abort Action for CM{self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.trigger_cavity_aborts)

        self.turn_off_button: QPushButton = QPushButton(f"Turn off CM{self.name}")
        self.turn_off_button.clicked.connect(self.trigger_cavity_turnoffs)

        self.setup_button.clicked.connect(self.trigger_cavity_setups)
        self.gui_cavities: Dict[int, GUICavity] = {}

        for cav_num in range(1, 9):
            gui_cavity = GUICavity(cav_num,
                                   f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:",
                                   self.name,
                                   settings=self.settings,
                                   parent=self.parent)
            self.gui_cavities[cav_num] = gui_cavity

    def trigger_cavity_turnoffs(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.cavity.trigger_shut_down()

    def trigger_cavity_aborts(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.cavity.trigger_abort()

    def trigger_cavity_setups(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.cavity.trigger_setup()


@dataclasses.dataclass
class Linac:
    name: str
    idx: int
    cryomodule_names: List[str]
    settings: Settings
    parent: Display

    def __post_init__(self):
        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.setup_button.clicked.connect(self.launch_cm_workers)

        self.abort_button: QPushButton = QPushButton(f"Abort Action for {self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.kill_cm_workers)
        self.aact_pv = (f"ACCL:L{self.idx}B:1:AACTMEANSUM"
                        if self.name != "L1BHL"
                        else "ACCL:L1B:1:HL_AACTMEANSUM")
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True
        self.cryomodules: List[GUICryomodule] = []
        self.cm_tab_widget: QTabWidget = QTabWidget()
        self.gui_cryomodules: Dict[str, GUICryomodule] = {}

        for cm_name in self.cryomodule_names:
            self.add_cm_tab(cm_name)

    def kill_cm_workers(self):
        for gui_cm in self.gui_cryomodules.values():
            gui_cm.trigger_cavity_aborts()

    def launch_cm_workers(self):
        for gui_cm in self.gui_cryomodules.values():
            gui_cm.trigger_cavity_setups()

    def add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")

        gui_cryomodule = GUICryomodule(linac_idx=self.idx, name=cm_name,
                                       settings=self.settings,
                                       parent=self.parent)
        self.gui_cryomodules[cm_name] = gui_cryomodule
        hlayout: QHBoxLayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QLabel(f"CM{cm_name} Amplitude:"))
        hlayout.addWidget(gui_cryomodule.readback_label)
        hlayout.addWidget(gui_cryomodule.setup_button)
        hlayout.addWidget(gui_cryomodule.turn_off_button)
        hlayout.addWidget(gui_cryomodule.abort_button)
        hlayout.addStretch()

        vlayout.addLayout(hlayout)

        groupbox: QGroupBox = QGroupBox()
        all_cav_layout: QGridLayout = QGridLayout()
        groupbox.setLayout(all_cav_layout)
        vlayout.addWidget(groupbox)
        for cav_num in range(1, 9):
            cav_groupbox: QGroupBox = QGroupBox(f"CM{cm_name} Cavity {cav_num}")
            cav_groupbox.setStyleSheet("QGroupBox { font-weight: bold; } ")

            cav_vlayout: QVBoxLayout = QVBoxLayout()
            cav_groupbox.setLayout(cav_vlayout)
            cav_widgets = gui_cryomodule.gui_cavities[cav_num]
            cav_desamp_hlayout: QHBoxLayout = QHBoxLayout()
            cav_desamp_hlayout.addStretch()
            cav_desamp_hlayout.addWidget(QLabel("Amplitude: "))
            cav_desamp_hlayout.addWidget(cav_widgets.ades_spinbox)
            cav_desamp_hlayout.addWidget(cav_widgets.aact_readback_label)
            cav_desamp_hlayout.addStretch()

            cav_button_hlayout: QHBoxLayout = QHBoxLayout()
            cav_button_hlayout.addStretch()
            cav_button_hlayout.addWidget(cav_widgets.setup_button)
            cav_button_hlayout.addWidget(cav_widgets.turn_off_button)
            cav_button_hlayout.addWidget(cav_widgets.abort_button)
            cav_button_hlayout.addWidget(cav_widgets.expert_screen_button)
            cav_button_hlayout.addStretch()

            cav_vlayout.addLayout(cav_desamp_hlayout)
            cav_vlayout.addLayout(cav_button_hlayout)
            cav_vlayout.addWidget(cav_widgets.status_label)
            all_cav_layout.addWidget(cav_groupbox,
                                     0 if cav_num in range(1, 5) else 1,
                                     (cav_num - 1) % 4)


class SetupGUI(Display):
    def ui_filename(self):
        return 'setup_gui.ui'

    def __init__(self, parent=None, args=None):
        super(SetupGUI, self).__init__(parent=parent, args=args)
        self.threadpool = QThreadPool()
        print(f"Max thread count: {self.threadpool.maxThreadCount()}")

        self.settings = Settings(ssa_cal_checkbox=self.ui.ssa_cal_checkbox,
                                 auto_tune_checkbox=self.ui.autotune_checkbox,
                                 cav_char_checkbox=self.ui.cav_char_checkbox,
                                 rf_ramp_checkbox=self.ui.rf_ramp_checkbox)

        self.linac_widgets: List[Linac] = []
        for linac_idx in range(0, 4):
            self.linac_widgets.append(Linac(f"L{linac_idx}B", linac_idx,
                                            sc_linac_utils.LINAC_TUPLES[linac_idx][1],
                                            settings=self.settings,
                                            parent=self))

        self.linac_widgets.insert(2, Linac("L1BHL", 1, sc_linac_utils.L1BHL,
                                           settings=self.settings, parent=self))

        self.linac_aact_pvs: List[PV] = [PV(f"ACCL:L{i}B:1:AACTMEANSUM") for i in range(4)]

        self.update_readback()

        linac_tab_widget: QTabWidget = self.ui.tabWidget_linac

        for linac in self.linac_widgets:
            page: QWidget = QWidget()
            vlayout: QVBoxLayout = QVBoxLayout()
            page.setLayout(vlayout)
            linac_tab_widget.addTab(page, linac.name)

            hlayout: QHBoxLayout = QHBoxLayout()
            hlayout.addStretch()
            hlayout.addWidget(QLabel(f"{linac.name} Amplitude:"))
            hlayout.addWidget(linac.readback_label)
            hlayout.addWidget(linac.setup_button)
            hlayout.addWidget(linac.abort_button)
            hlayout.addStretch()

            vlayout.addLayout(hlayout)
            vlayout.addWidget(linac.cm_tab_widget)
            camonitor(linac.aact_pv, callback=self.update_readback)

    def update_readback(self, **kwargs):
        readback = 0
        for linac_aact_pv in self.linac_aact_pvs:
            readback += linac_aact_pv.get()
        self.ui.machine_readback_label.setText(f"{readback:.2f} MV")
