from unittest.mock import MagicMock

from lcls_tools.common.controls.pyepics.utils import EPICS_NO_ALARM_VAL


def mock_func(*args, **kwargs):
    args_str = ",".join(map(str, args))
    kwargs_str = ",".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"mocking  with {','.join([args_str, kwargs_str])}")


def make_mock_pv(
    pv_name: str = None, get_val=None, severity=EPICS_NO_ALARM_VAL
) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
        severity=severity,
    )


def test_setup(obj):
    obj._ssa_cal_requested_pv_obj = make_mock_pv()
    obj._auto_tune_requested_pv_obj = make_mock_pv()
    obj._cav_char_requested_pv_obj = make_mock_pv()
    obj._rf_ramp_requested_pv_obj = make_mock_pv()
    obj._start_pv_obj = make_mock_pv()
    obj.trigger_setup()

    obj._ssa_cal_requested_pv_obj.put.assert_called_with(1)
    obj._auto_tune_requested_pv_obj.put.assert_called_with(1)
    obj._cav_char_requested_pv_obj.put.assert_called_with(1)
    obj._rf_ramp_requested_pv_obj.put.assert_called_with(1)
    obj._start_pv_obj.put.assert_called_with(1)
