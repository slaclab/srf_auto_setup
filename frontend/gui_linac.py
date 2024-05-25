from typing import Optional, TYPE_CHECKING

from PyQt5.QtWidgets import (
    QPushButton,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QGridLayout,
)
from pydm.widgets import PyDMLabel

from backend.setup_linac import SetupLinac
from frontend.gui_cryomodule import GUICryomodule
from lcls_tools.common.controls.pyepics.utils import PV

if TYPE_CHECKING:
    from frontend.gui_machine import GUIMachine

from lcls_tools.common.frontend.display.util import ERROR_STYLESHEET


class GUILinac(SetupLinac):
    def __init__(
            self,
            linac_section,
            beamline_vacuum_infixes,
            insulating_vacuum_cryomodules,
            machine: "GUIMachine",
    ):
        super().__init__(
            linac_section,
            beamline_vacuum_infixes,
            insulating_vacuum_cryomodules,
            machine,
        )

        self.machine: "GUIMachine" = machine

        self._linac_object: Optional[SetupLinac] = None

        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.setup_button.clicked.connect(self.trigger_setup)

        self.abort_button: QPushButton = QPushButton(f"Abort Action for {self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.request_abort)

        self.acon_button: QPushButton = QPushButton(f"Capture all {self.name} ACON")
        self.acon_button.clicked.connect(self.capture_acon)

        self.aact_pv = f"ACCL:{self.name}:1:AACTMEANSUM"
        self._aact_pv_obj: Optional[PV] = None

        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True

        self.cm_tab_widget: QTabWidget = QTabWidget()

        for cm_name in self.cryomodules.keys():
            self._add_cm_tab(cm_name)

    @property
    def aact(self):
        if not self._aact_pv_obj:
            self._aact_pv_obj = PV(self.aact_pv)
        return self._aact_pv_obj.get()

    def trigger_setup(self):
        self.ssa_cal_requested = self.machine.settings.ssa_cal_checkbox.isChecked()
        self.auto_tune_requested = self.machine.settings.auto_tune_checkbox.isChecked()
        self.cav_char_requested = self.machine.settings.cav_char_checkbox.isChecked()
        self.rf_ramp_requested = self.machine.settings.rf_ramp_checkbox.isChecked()
        super().trigger_setup()

    def capture_acon(self):
        for gui_cm in self.cryomodules.values():
            gui_cm.capture_acon()

    def _add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")

        gui_cryomodule: GUICryomodule = self.cryomodules[cm_name]
        hlayout: QHBoxLayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QLabel(f"CM{cm_name} Amplitude:"))
        hlayout.addWidget(gui_cryomodule.readback_label)
        hlayout.addWidget(gui_cryomodule.setup_button)
        hlayout.addWidget(gui_cryomodule.turn_off_button)
        hlayout.addWidget(gui_cryomodule.abort_button)
        hlayout.addWidget(gui_cryomodule.acon_button)
        hlayout.addStretch()

        vlayout.addLayout(hlayout)

        groupbox: QGroupBox = QGroupBox()
        all_cav_layout: QGridLayout = QGridLayout()
        groupbox.setLayout(all_cav_layout)
        vlayout.addWidget(groupbox)
        for gui_cavity in gui_cryomodule.cavities.values():
            cav_groupbox: QGroupBox = QGroupBox(f"{gui_cavity}")
            cav_groupbox.setStyleSheet("QGroupBox { font-weight: bold; } ")

            cav_vlayout: QVBoxLayout = QVBoxLayout()
            cav_groupbox.setLayout(cav_vlayout)
            cav_amp_hlayout: QHBoxLayout = QHBoxLayout()
            cav_amp_hlayout.addStretch()
            cav_amp_hlayout.addWidget(QLabel("ACON: "))
            cav_amp_hlayout.addWidget(gui_cavity.acon_label)
            cav_amp_hlayout.addWidget(QLabel("AACT: "))
            cav_amp_hlayout.addWidget(gui_cavity.aact_readback_label)
            cav_amp_hlayout.addStretch()
            cav_button_hlayout: QHBoxLayout = QHBoxLayout()
            cav_button_hlayout.addStretch()
            cav_button_hlayout.addWidget(gui_cavity.setup_button)
            cav_button_hlayout.addWidget(gui_cavity.shutdown_button)
            cav_button_hlayout.addWidget(gui_cavity.abort_button)
            cav_button_hlayout.addWidget(gui_cavity.expert_screen_button)
            cav_button_hlayout.addStretch()

            cav_vlayout.addLayout(cav_amp_hlayout)
            cav_vlayout.addLayout(cav_button_hlayout)
            cav_vlayout.addWidget(gui_cavity.status_label)
            cav_vlayout.addWidget(gui_cavity.progress_bar)
            cav_vlayout.addWidget(gui_cavity.note_label)
            all_cav_layout.addWidget(
                cav_groupbox,
                0 if gui_cavity.number in range(1, 5) else 1,
                (gui_cavity.number - 1) % 4,
            )
