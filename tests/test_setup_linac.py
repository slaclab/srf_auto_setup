from unittest import TestCase, mock
from lcls_tools.superconducting.sc_linac import MACHINE
from lcls_tools.superconducting.sc_linac_utils import CavityAbortError
from setup_linac import (
    SETUP_MACHINE,
    SetupCavity,
    STATUS_RUNNING_VALUE,
    STATUS_READY_VALUE,
)


class TestAutoLinacObject(TestCase):
    def test_kill_setup(self):
        self.fail()

    def test_ssa_cal_requested_pv_obj(self):
        self.fail()

    def test_ssa_cal_requested(self):
        self.fail()

    def test_auto_tune_requested_pv_obj(self):
        self.fail()

    def test_auto_tune_requested(self):
        self.fail()

    def test_cav_char_requested_pv_obj(self):
        self.fail()

    def test_cav_char_requested(self):
        self.fail()

    def test_rf_ramp_requested_pv_obj(self):
        self.fail()

    def test_rf_ramp_requested(self):
        self.fail()


class TestSetupCavity(TestCase):
    def setUp(self):
        self.base_cavity = MACHINE.cryomodules["01"].cavities[1]
        self.setup_cavity: SetupCavity = SETUP_MACHINE.cryomodules["01"].cavities[1]

        self.mock_abort_pv_obj = mock.Mock(pvname=self.setup_cavity.abort_pv)
        self.mock_abort_pv_obj.put = mock.MagicMock(return_value=1)
        self.setup_cavity._abort_pv_obj = self.mock_abort_pv_obj

        self.mock_start_pv_obj = mock.Mock(pvname=self.setup_cavity.start_pv)
        self.mock_start_pv_obj.put = mock.MagicMock(return_value=1)
        self.setup_cavity._start_pv_obj = self.mock_start_pv_obj

        self.mock_shutdown_pv_obj = mock.Mock(pvname=self.setup_cavity.shutoff_pv)
        self.mock_shutdown_pv_obj.put = mock.MagicMock(return_value=1)
        self.setup_cavity._shutoff_pv_obj = self.mock_shutdown_pv_obj

        self.mock_status_pv_obj = mock.Mock(pvname=self.setup_cavity.status_pv)
        self.setup_cavity._status_pv_obj = self.mock_status_pv_obj

        self.mock_status_msg_pv_obj = mock.MagicMock(
            pvname=self.setup_cavity.status_msg_pv
        )
        self.setup_cavity._status_msg_pv_obj = self.mock_status_msg_pv_obj
        self.mock_status_msg_pv_obj.put = mock.MagicMock(return_value=1)

        self.mock_acon_pv_obj = mock.MagicMock(pvname=self.setup_cavity.acon_pv)
        self.setup_cavity._acon_pv_obj = self.mock_acon_pv_obj
        self.mock_acon_pv_obj.put = mock.MagicMock(return_value=1)

        self.mock_ades_pv_obj = mock.MagicMock(pvname=self.setup_cavity.ades_pv)
        self.setup_cavity._ades_pv_obj = self.mock_ades_pv_obj
        self.mock_ades_pv_obj.put = mock.MagicMock(return_value=1)
        self.mock_ades_pv_obj.get = mock.MagicMock(return_value=16.6)

        self.mock_progress_pv_obj = mock.MagicMock(pvname=self.setup_cavity.progress_pv)
        self.setup_cavity._progress_pv_obj = self.mock_progress_pv_obj
        self.mock_progress_pv_obj.put = mock.MagicMock(return_value=1)

    def test_auto_pv_addr(self):
        suffix = "suffix"
        self.assertEquals(
            self.base_cavity.pv_prefix + f"AUTO:{suffix}",
            self.setup_cavity.auto_pv_addr(suffix),
        )

    def test_abort_requested(self):
        """
        Assert that abort_requested returns the boolean value of the abort PV
        :return: None
        """
        attrs = {"get.return_value": True}
        self.mock_abort_pv_obj.configure_mock(**attrs)
        self.assertTrue(self.setup_cavity.abort_requested)

        attrs = {"get.return_value": False}
        self.mock_abort_pv_obj.configure_mock(**attrs)
        self.assertFalse(self.setup_cavity.abort_requested)

    def test_clear_abort(self):
        """
        Assert that clearing the abort means writing 0 to the abort PV
        :return:
        """
        self.setup_cavity.clear_abort()
        self.mock_abort_pv_obj.put.assert_called_with(0)

    def test_trigger_setup(self):
        """
        Assert that triggering the setup means writing 1 to the start PV
        :return:
        """
        self.setup_cavity.trigger_setup()
        self.mock_start_pv_obj.put.assert_called_with(1)

    def test_trigger_shutdown(self):
        """
        Assert that triggering the shutdown means writing 1 to the shutdown PV
        :return:
        """
        self.setup_cavity.trigger_shutdown()
        self.mock_shutdown_pv_obj.put.assert_called_with(1)

    def test_request_abort(self):
        attrs = {"get.return_value": STATUS_RUNNING_VALUE}
        self.mock_status_pv_obj.configure_mock(**attrs)

        self.setup_cavity.request_abort()
        self.mock_status_msg_pv_obj.put.assert_called_with(
            f"Requesting stop for {self.setup_cavity}"
        )
        self.mock_abort_pv_obj.put.assert_called_with(1)

        attrs = {"get.return_value": STATUS_READY_VALUE}
        self.mock_status_pv_obj.configure_mock(**attrs)
        self.setup_cavity.request_abort()
        self.mock_status_msg_pv_obj.put.assert_called_with(
            f"{self.setup_cavity} script not running, no abort needed"
        )

    def test_capture_acon(self):
        self.setup_cavity.capture_acon()
        self.mock_ades_pv_obj.get.assert_called()
        self.mock_acon_pv_obj.put.assert_called_with(16.6)

    def test_status(self):
        self.mock_status_pv_obj.get = mock.MagicMock(return_value=STATUS_READY_VALUE)
        self.assertEquals(self.setup_cavity.status, STATUS_READY_VALUE)

    def test_script_is_running(self):
        attrs = {"get.return_value": STATUS_RUNNING_VALUE}
        mock_status_pv_obj = mock.Mock(pvname=self.setup_cavity.status_pv, **attrs)
        self.setup_cavity._status_pv_obj = mock_status_pv_obj
        self.assertTrue(self.setup_cavity.script_is_running)

        attrs = {"get.return_value": STATUS_READY_VALUE}
        mock_status_pv_obj.configure_mock(**attrs)
        self.assertFalse(self.setup_cavity.script_is_running)

    def test_progress(self):
        self.mock_progress_pv_obj.get = mock.MagicMock(return_value=0)
        self.assertEquals(self.setup_cavity.progress, 0)

    def test_status_message(self):
        test_message = "test"
        self.mock_status_msg_pv_obj.get = mock.MagicMock(return_value=test_message)
        self.assertEquals(self.setup_cavity.status_message, test_message)

    def test_check_abort(self):
        self.mock_abort_pv_obj.get = mock.MagicMock(return_value=1)
        self.assertRaises(CavityAbortError, self.setup_cavity.check_abort)
        self.mock_abort_pv_obj.put.assert_called_with(0)

        self.mock_abort_pv_obj.get = mock.MagicMock(return_value=0)
        try:
            self.setup_cavity.check_abort()
        except CavityAbortError:
            self.fail(f"{self.setup_cavity} threw exception when abort not requested")

    def test_shut_down(self):
        self.setup_cavity.shut_down()

    def test_setup(self):
        self.setup_cavity.setup()


class TestSetupCryomodule(TestCase):
    def test_clear_abort(self):
        self.fail()


class TestSetupLinac(TestCase):
    def test_pv_prefix(self):
        self.fail()

    def test_clear_abort(self):
        self.fail()


class TestSetupMachine(TestCase):
    def test_pv_prefix(self):
        self.fail()

    def test_clear_abort(self):
        self.fail()
