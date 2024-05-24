from unittest.mock import MagicMock

from frontend.gui_cryomodule import GUICryomodule
from tests.test_gui_machine import TestGUI
from tests.utils import test_setup


class TestGUICryomodule(TestGUI):
    def test_capture_acon(self):
        gui_cm: GUICryomodule = self.gui_machine.cryomodules["01"]
        print(gui_cm.name)
        for gui_cavity in gui_cm.cavities.values():
            gui_cavity.capture_acon = MagicMock()
        gui_cm.capture_acon()
        for gui_cavity in gui_cm.cavities.values():
            gui_cavity.capture_acon.assert_called()

    def test_trigger_setup(self):
        gui_cm: GUICryomodule = self.gui_machine.cryomodules["02"]
        test_setup(gui_cm)
