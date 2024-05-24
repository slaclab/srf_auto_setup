from backend.utils import STATUS_READY_VALUE
from frontend.gui_cavity import GUICavity
from tests.test_gui_machine import TestGUI
from tests.utils import make_mock_pv, test_setup


class TestGUICavity(TestGUI):
    def test_trigger_shutdown(self):
        gui_cavity: GUICavity = self.gui_machine.cryomodules["01"].cavities[1]
        gui_cavity._status_pv_obj = make_mock_pv(get_val=STATUS_READY_VALUE)
        gui_cavity._shutoff_pv_obj = make_mock_pv()
        gui_cavity.trigger_shutdown()
        gui_cavity._status_pv_obj.get.assert_called()
        gui_cavity._shutoff_pv_obj.put.assert_called_with(1)

    def test_trigger_setup(self):
        gui_cavity: GUICavity = self.gui_machine.cryomodules["01"].cavities[2]
        test_setup(gui_cavity)
