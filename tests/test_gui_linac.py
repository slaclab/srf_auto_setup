from random import randint
from unittest.mock import MagicMock

from frontend.gui_linac import GUILinac
from tests.test_gui_machine import TestGUI
from tests.utils import make_mock_pv, test_setup


class TestGUILinac(TestGUI):

    def test_aact(self):
        gui_linac: GUILinac = self.gui_machine.linacs[0]
        amp = randint(0, 160)
        gui_linac._aact_pv_obj = make_mock_pv(get_val=amp)
        self.assertEqual(gui_linac.aact, amp)

    def test_trigger_setup(self):
        gui_linac: GUILinac = self.gui_machine.linacs[1]
        test_setup(gui_linac)

    def test_capture_acon(self):
        gui_linac: GUILinac = self.gui_machine.linacs[2]
        for gui_cm in gui_linac.cryomodules.values():
            gui_cm.capture_acon = MagicMock()
        gui_linac.capture_acon()
        for gui_cm in gui_linac.cryomodules.values():
            gui_cm.capture_acon.assert_called()
