from functools import partial

from PyQt5.QtWidgets import QLabel, QPushButton
from lcls_tools.common.frontend.display.util import WorkerSignals


class SetupSignals(WorkerSignals):
    def __init__(
        self, status_label: QLabel, setup_button: QPushButton, off_button: QPushButton
    ):
        super().__init__(status_label)
        self.status.connect(partial(setup_button.setEnabled, False))
        self.finished.connect(partial(setup_button.setEnabled, True))
        self.error.connect(partial(setup_button.setEnabled, True))

        self.status.connect(partial(off_button.setEnabled, False))
        self.finished.connect(partial(off_button.setEnabled, True))
        self.error.connect(partial(off_button.setEnabled, True))
