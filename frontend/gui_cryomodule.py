from PyQt5.QtWidgets import QPushButton
from pydm.widgets import PyDMLabel

from backend.setup_cryomodule import SetupCryomodule
from lcls_tools.common.frontend.display.util import ERROR_STYLESHEET


class GUICryomodule(SetupCryomodule):
    def __init__(self, cryo_name, linac_object):
        super().__init__(cryo_name, linac_object)

        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True

        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        self.setup_button.clicked.connect(self.trigger_setup)

        self.abort_button: QPushButton = QPushButton(f"Abort Action for CM{self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.request_abort)
        self.turn_off_button: QPushButton = QPushButton(f"Turn off CM{self.name}")
        self.turn_off_button.clicked.connect(self.trigger_shutdown)

        self.acon_button: QPushButton = QPushButton(
            f"Push all CM{self.name} ADES to ACON"
        )
        self.acon_button.clicked.connect(self.capture_acon)

    def capture_acon(self):
        for cavity in self.cavities.values():
            cavity.capture_acon()

    def trigger_setup(self):
        self.ssa_cal_requested = self.settings.ssa_cal_checkbox.isChecked()
        self.auto_tune_requested = self.settings.auto_tune_checkbox.isChecked()
        self.cav_char_requested = self.settings.cav_char_checkbox.isChecked()
        self.rf_ramp_requested = self.settings.rf_ramp_checkbox.isChecked()

        super().trigger_setup()
