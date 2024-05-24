from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout
from pydm import Display

from frontend.gui_machine import GUIMachine


class SetupGUI(Display):
    def __init__(self, parent=None, args=None):
        super(SetupGUI, self).__init__(parent=parent, args=args)
        self.gui_machine = GUIMachine(parent=self)

        self.setWindowTitle("SRF Auto Setup")
        self.vlayout: QVBoxLayout = QVBoxLayout()
        self.color_bar = QLabel()
        self.color_bar.setStyleSheet("background-color: rgb(175, 217, 248);")
        self.vlayout.addWidget(self.color_bar)
        self.setLayout(self.vlayout)

        self.machine_buttons = QHBoxLayout()
        self.machine_buttons.addStretch()
        self.machine_buttons.addWidget(self.gui_machine.machine_setup_button)
        self.machine_buttons.addWidget(self.gui_machine.machine_shutdown_button)
        self.machine_buttons.addWidget(self.gui_machine.machine_abort_button)
        self.machine_buttons.addStretch()
        self.vlayout.addLayout(self.machine_buttons)

        self.header: QHBoxLayout = QHBoxLayout()
        self.header.addStretch()
        self.header.addWidget(QLabel("Machine Amplitude:"))
        self.header.addWidget(self.gui_machine.machine_readback_label)
        self.header.addStretch()
        self.vlayout.addLayout(self.header)

        self.expert_options: QHBoxLayout = QHBoxLayout()
        self.expert_options.addStretch()
        self.expert_options.addWidget(QLabel("Expert Options:"))
        self.expert_options.addWidget(self.gui_machine.ssa_cal_checkbox)
        self.expert_options.addWidget(self.gui_machine.autotune_checkbox)
        self.expert_options.addWidget(self.gui_machine.cav_char_checkbox)
        self.expert_options.addWidget(self.gui_machine.rf_ramp_checkbox)
        self.expert_options.addStretch()
        self.vlayout.addLayout(self.expert_options)

        self.vlayout.addWidget(self.gui_machine.linac_tab_widget)
