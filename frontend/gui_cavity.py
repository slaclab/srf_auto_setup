from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QSizePolicy
from edmbutton import PyDMEDMDisplayButton
from pydm.widgets import PyDMLabel
from pydm.widgets.analog_indicator import PyDMAnalogIndicator
from pydm.widgets.display_format import DisplayFormat

from backend.setup_cavity import SetupCavity
from lcls_tools.common.frontend.display.util import ERROR_STYLESHEET


class GUICavity(SetupCavity):
    def __init__(self, cavity_num, rack_object):
        super().__init__(cavity_num, rack_object)

        self.setup_button = QPushButton(f"Set Up")

        self.abort_button: QPushButton = QPushButton("Abort")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.request_abort)
        self.shutdown_button: QPushButton = QPushButton(f"Turn Off")
        self.shutdown_button.clicked.connect(self.trigger_shutdown)

        self.setup_button.clicked.connect(self.trigger_setup)
        self.aact_readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.aact_readback_label.alarmSensitiveBorder = True
        self.aact_readback_label.alarmSensitiveContent = True
        self.aact_readback_label.showUnits = True
        self.aact_readback_label.precisionFromPV = False
        self.aact_readback_label.precision = 2

        # Putting this here because it otherwise gets garbage collected (?!)
        self.acon_label: PyDMLabel = PyDMLabel(init_channel=self.acon_pv)
        self.acon_label.alarmSensitiveContent = True
        self.acon_label.alarmSensitiveBorder = True
        self.acon_label.showUnits = True
        self.acon_label.precisionFromPV = False
        self.acon_label.precision = 2

        self.status_label: PyDMLabel = PyDMLabel(init_channel=self.status_msg_pv)

        # status_msg_pv is an ndarray of char codes and seeing the display format
        # makes is display correctly (i.e. not as [ 1 2 3 4]
        self.status_label.displayFormat = DisplayFormat.String

        self.status_label.setAlignment(Qt.AlignHCenter)
        self.status_label.setWordWrap(True)
        self.status_label.alarmSensitiveBorder = True
        self.status_label.alarmSensitiveContent = True

        self.progress_bar: PyDMAnalogIndicator = PyDMAnalogIndicator(
            init_channel=self.progress_pv
        )
        self.progress_bar.backgroundSizeRate = 0.2
        self.progress_bar.sizePolicy().setVerticalPolicy(QSizePolicy.Maximum)

        self.expert_screen_button: PyDMEDMDisplayButton = PyDMEDMDisplayButton()
        self.expert_screen_button.filenames = ["$EDM/llrf/rf_srf_cavity_main.edl"]
        self.expert_screen_button.macros = self.edm_macro_string + (
                "," + "SELTAB=0,SELCHAR=3"
        )
        self.expert_screen_button.setToolTip("EDM expert screens")

        self.note_label: PyDMLabel = PyDMLabel(init_channel=self.note_pv)
        self.note_label.displayFormat = DisplayFormat.String
        self.note_label.setWordWrap(True)
        self.note_label.alarmSensitiveBorder = True
        self.note_label.alarmSensitiveContent = True

    def trigger_shutdown(self):
        if self.script_is_running:
            self.status_message = f"{self} script already running"
            return
        super().trigger_shutdown()

    def trigger_setup(self):
        if self.script_is_running:
            self.status_message = f"{self} script already running"
            return
        elif not self.is_online:
            self.status_message = f"{self} not online, skipping"
            return
        else:
            settings = self.cryomodule.linac.machine.settings
            self.ssa_cal_requested = settings.ssa_cal_checkbox.isChecked()
            self.auto_tune_requested = settings.auto_tune_checkbox.isChecked()
            self.cav_char_requested = settings.cav_char_checkbox.isChecked()
            self.rf_ramp_requested = settings.rf_ramp_checkbox.isChecked()

            super().trigger_setup()
