from time import sleep
from typing import Optional

from epics.ca import CASeverityException

from backend.utils import (
    STATUS_READY_VALUE,
    STATUS_RUNNING_VALUE,
    STATUS_ERROR_VALUE,
    AutoLinacObject,
)
from lcls_tools.common.controls.pyepics.utils import PV, PVInvalidError
from lcls_tools.superconducting import sc_linac_utils
from lcls_tools.superconducting.sc_linac import Cavity
from lcls_tools.superconducting.sc_linac_utils import RF_MODE_SELA


class SetupCavity(Cavity, AutoLinacObject):
    def __init__(
        self,
        cavity_num,
        rack_object,
    ):
        Cavity.__init__(self, cavity_num=cavity_num, rack_object=rack_object)
        AutoLinacObject.__init__(self)

        self.progress_pv: str = self.auto_pv_addr("PROG")
        self._progress_pv_obj: Optional[PV] = None

        self.status_pv: str = self.auto_pv_addr("STATUS")
        self._status_pv_obj: Optional[PV] = None

        self.status_msg_pv: str = self.auto_pv_addr("MSG")
        self._status_msg_pv_obj: Optional[PV] = None

        self.note_pv: str = self.auto_pv_addr("NOTE")
        self._note_pv_obj: Optional[PV] = None

    def capture_acon(self):
        self.acon = self.ades

    @property
    def note_pv_obj(self) -> PV:
        if not self._note_pv_obj:
            self._note_pv_obj = PV(self.note_pv)
        return self._note_pv_obj

    @property
    def status_pv_obj(self):
        if not self._status_pv_obj:
            self._status_pv_obj = PV(self.status_pv)
        return self._status_pv_obj

    @property
    def status(self):
        return self.status_pv_obj.get()

    @status.setter
    def status(self, value: int):
        self.status_pv_obj.put(value)

    @property
    def script_is_running(self) -> bool:
        return self.status == STATUS_RUNNING_VALUE

    @property
    def progress_pv_obj(self):
        if not self._progress_pv_obj:
            self._progress_pv_obj = PV(self.progress_pv)
        return self._progress_pv_obj

    @property
    def progress(self) -> float:
        return self.progress_pv_obj.get()

    @progress.setter
    def progress(self, value: float):
        self.progress_pv_obj.put(value)

    @property
    def status_msg_pv_obj(self) -> PV:
        if not self._status_msg_pv_obj:
            self._status_msg_pv_obj = PV(self.status_msg_pv)
        return self._status_msg_pv_obj

    @property
    def status_message(self):
        return self.status_msg_pv_obj.get()

    @status_message.setter
    def status_message(self, message):
        print(message)
        self.status_msg_pv_obj.put(message)

    def clear_abort(self):
        self.abort_pv_obj.put(0)

    def request_abort(self):
        if self.script_is_running:
            self.status_message = f"Requesting stop for {self}"
            self.abort_pv_obj.put(1)
        else:
            self.status_message = f"{self} script not running, no abort needed"

    def check_abort(self):
        if self.abort_requested:
            self.clear_abort()
            raise sc_linac_utils.CavityAbortError(f"Abort requested for {self}")

    def shut_down(self):
        if self.script_is_running:
            self.status_message = f"{self} script already running"
            return

        self.clear_abort()

        try:
            self.status = STATUS_RUNNING_VALUE
            self.progress = 0
            self.status_message = f"Turning {self} RF off"
            self.turn_off()
            self.progress = 50
            self.status_message = f"Turning {self} SSA off"
            self.ssa.turn_off()
            self.progress = 100
            self.status = STATUS_READY_VALUE
            self.status_message = f"{self} RF and SSA off"
        except (CASeverityException, sc_linac_utils.CavityAbortError) as e:
            self.status = STATUS_ERROR_VALUE
            self.clear_abort()
            self.status_message = str(e)

    def setup(self):
        try:
            if self.script_is_running:
                self.status_message = f"{self} script already running"
                return

            if not self.is_online:
                self.status_message = f"{self} not online, not setting up"
                self.status = STATUS_ERROR_VALUE
                return

            self.clear_abort()

            self.status = STATUS_RUNNING_VALUE
            self.progress = 0

            # Not turning it off can cause problems if an interlock is tripped
            # but the requested RF state is on
            self.status_message = f"Turning {self} off before starting setup"
            self.turn_off()
            self.progress = 5

            self.status_message = f"Turning on {self} SSA if not on already"
            self.ssa.turn_on()
            self.progress = 10

            self.status_message = f"Resetting {self} interlocks"
            self.reset_interlocks()
            self.progress = 15

            if self.ssa_cal_requested:
                self.status_message = f"Running {self} SSA Calibration"
                self.turn_off()
                self.progress = 20
                self.ssa.calibrate(self.ssa.drive_max)
                self.status_message = f"{self} SSA Calibrated"

            self.progress = 25
            self.check_abort()

            if self.auto_tune_requested:
                self.status_message = f"Tuning {self} to Resonance"
                self.move_to_resonance(use_sela=False)
                self.status_message = f"{self} Tuned to Resonance"

            self.progress = 50
            self.check_abort()

            if self.cav_char_requested:
                self.status_message = f"Running {self} Cavity Characterization"
                self.characterize()
                self.progress = 60
                self.calc_probe_q_pv_obj.put(1)
                self.progress = 70
                self.status_message = f"{self} Characterized"

            self.progress = 75
            self.check_abort()

            if self.rf_ramp_requested:
                self.status_message = f"Ramping {self} to {self.acon}"
                self.piezo.enable_feedback()
                self.progress = 80

                if not self.is_on or (
                    self.is_on and self.rf_mode != sc_linac_utils.RF_MODE_SELAP
                ):
                    self.ades = min(5, self.acon)

                self.turn_on()
                self.progress = 85

                self.check_abort()

                self.set_sela_mode()

                while self.rf_mode != RF_MODE_SELA:
                    self.check_abort()
                    self.status_message = "Waiting for cavity to be in SELA"
                    sleep(0.5)

                self.walk_amp(self.acon, 0.1)
                self.progress = 90

                self.status_message = f"Centering {self} piezo"
                self.move_to_resonance(use_sela=True)
                self.progress = 95

                self.set_selap_mode()

                self.status_message = f"{self} Ramped Up to {self.acon} MV"

            self.progress = 100
            self.status = STATUS_READY_VALUE
        except (
            sc_linac_utils.StepperError,
            sc_linac_utils.DetuneError,
            sc_linac_utils.SSACalibrationError,
            PVInvalidError,
            sc_linac_utils.QuenchError,
            sc_linac_utils.CavityQLoadedCalibrationError,
            sc_linac_utils.CavityScaleFactorCalibrationError,
            sc_linac_utils.SSAFaultError,
            sc_linac_utils.StepperAbortError,
            sc_linac_utils.CavityHWModeError,
            sc_linac_utils.CavityFaultError,
            sc_linac_utils.CavityAbortError,
            CASeverityException,
        ) as e:
            self.status = STATUS_ERROR_VALUE
            self.clear_abort()
            self.status_message = str(e)
