import sys
from random import randint
from unittest import mock, TestCase

from PyQt5.QtWidgets import QApplication

from tests.utils import mock_func, make_mock_pv, test_setup

with mock.patch("epics.camonitor", mock_func):
    with mock.patch("pydm.PyDMChannel", mock.MagicMock()):
        from frontend.gui_machine import GUIMachine


class TestGUI(TestCase):
    def setUp(self) -> None:
        self.app = QApplication(sys.argv)
        self.gui_machine = GUIMachine()

    def tearDown(self) -> None:
        self.app.closeAllWindows()


class TestGUIMachine(TestGUI):

    def test_pv_prefix(self):
        self.assertEqual(self.gui_machine.pv_prefix, "ACCL:SYS0:SC:AUTO:")

    def test_update_readback(self):
        amp = randint(0, 160)
        for gui_linac in self.gui_machine.linacs:
            gui_linac._aact_pv_obj = make_mock_pv(get_val=amp)
        self.gui_machine.update_readback()
        self.assertEqual(
            self.gui_machine.machine_readback_label.text(),
            f"{amp * len(self.gui_machine.linacs):.2f} MV",
        )

    def test_trigger_setup(self):
        test_setup(self.gui_machine)
