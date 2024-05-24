from PyQt5.QtWidgets import (
    QPushButton,
    QLabel,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from epics import camonitor

from backend.utils import AutoLinacObject
from frontend.gui_cavity import GUICavity
from frontend.gui_cryomodule import GUICryomodule
from frontend.gui_linac import GUILinac
from frontend.utils import Settings, make_setting_checkbox
from lcls_tools.common.frontend.display.util import ERROR_STYLESHEET
from lcls_tools.superconducting.sc_linac import Machine


class GUIMachine(Machine, AutoLinacObject):
    @property
    def pv_prefix(self):
        return "ACCL:SYS0:SC:AUTO:"

    def __init__(self):
        Machine.__init__(
            self,
            linac_class=GUILinac,
            cryomodule_class=GUICryomodule,
            cavity_class=GUICavity,
        )
        AutoLinacObject.__init__(self)

        self.machine_abort_button = QPushButton("Abort Machine")
        self.machine_setup_button = QPushButton("Set Up Machine")
        self.machine_shutdown_button = QPushButton("Shut Down Machine")

        self.machine_abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.machine_abort_button.clicked.connect(self.request_abort)
        self.machine_setup_button.clicked.connect(self.trigger_setup)
        self.machine_shutdown_button.clicked.connect(self.trigger_shutdown)

        self.ssa_cal_checkbox = make_setting_checkbox("SSA Calibration")
        self.autotune_checkbox = make_setting_checkbox("Auto Tune")
        self.cav_char_checkbox = make_setting_checkbox("Cavity Characterization")
        self.rf_ramp_checkbox = make_setting_checkbox("RF Ramp")

        self.settings = Settings(
            ssa_cal_checkbox=self.ssa_cal_checkbox,
            auto_tune_checkbox=self.autotune_checkbox,
            cav_char_checkbox=self.cav_char_checkbox,
            rf_ramp_checkbox=self.rf_ramp_checkbox,
        )

        self.machine_readback_label: QLabel = QLabel()

        self.linac_tab_widget: QTabWidget = QTabWidget()

        for linac in self.linacs:
            page: QWidget = QWidget()
            vlayout: QVBoxLayout = QVBoxLayout()
            page.setLayout(vlayout)
            self.linac_tab_widget.addTab(page, linac.name)

            hlayout: QHBoxLayout = QHBoxLayout()
            hlayout.addStretch()
            hlayout.addWidget(QLabel(f"{linac.name} Amplitude:"))
            hlayout.addWidget(linac.readback_label)
            hlayout.addWidget(linac.setup_button)
            hlayout.addWidget(linac.abort_button)
            hlayout.addWidget(linac.acon_button)
            hlayout.addStretch()

            vlayout.addLayout(hlayout)
            vlayout.addWidget(linac.cm_tab_widget)
            camonitor(linac.aact_pv, callback=self.update_readback)

    def update_readback(self, **kwargs):
        readback = 0
        for linac in self.linacs:
            readback += linac.aact
        self.machine_readback_label.setText(f"{readback:.2f} MV")

    def trigger_setup(self):
        self.ssa_cal_requested = self.settings.ssa_cal_checkbox.isChecked()
        self.auto_tune_requested = self.settings.auto_tune_checkbox.isChecked()
        self.cav_char_requested = self.settings.cav_char_checkbox.isChecked()
        self.rf_ramp_requested = self.settings.rf_ramp_checkbox.isChecked()
        super().trigger_setup()
