from lcls_tools.common.pyepics_tools.pyepics_utils import PV
from lcls_tools.superconducting.scLinac import (Cavity, CryoDict, Piezo, SSA,
                                                StepperTuner)
from lcls_tools.superconducting.sc_linac_utils import (RF_MODE_SELAP)


class SetupCavity(Cavity):
    
    def auto_pv_addr(self, suffix: str):
        return super().pv_addr("AUTO:" + suffix)
    
    def __init__(self, cavityNum, rackObject, ssaClass=SSA,
                 stepperClass=StepperTuner, piezoClass=Piezo):
        super().__init__(cavityNum, rackObject, ssaClass,
                         stepperClass, piezoClass)
        
        # TODO populate these when they exist
        self.progress_pv: str = self.auto_pv_addr("")
        self.status_severity_pv: str = self.auto_pv_addr("")
        
        # TODO implement
        self.running_pv: str = self.auto_pv_addr("")
        self._running_pv_obj: PV = None
        
        # TODO implement
        self.status_pv: str = self.auto_pv_addr("")
        self._status_pv_obj: PV = None
        
        # TODO implement
        self.abort_pv: str = self.auto_pv_addr("")
        self._abort_pv_obj: PV = None
        
        # TODO implement
        self.shutoff_pv: str = self.auto_pv_addr("")
        self._shutoff_pv_obj: PV = None
        
        self.start_pv: str = self.auto_pv_addr("SETUPSTRT")
        self._start_pv_obj: PV = None
        
        self.ssa_cal_requested_pv: str = self.auto_pv_addr("TURNON_SSASEL")
        self._ssa_cal_requested_pv_obj: PV = None
        
        self.auto_tune_requested_pv: str = self.auto_pv_addr("TURNON_TUNESEL")
        self._auto_tune_requested_pv_obj: PV = None
        
        self.cav_char_requested_pv: str = self.auto_pv_addr("TURNON_CHARSEL")
        self._cav_char_requested_pv_obj: PV = None
        
        self.rf_ramp_requested_pv: str = self.auto_pv_addr("TURNON_RAMPSEL")
        self._rf_ramp_requested_pv_obj: PV = None
    
    @property
    def running_pv_obj(self):
        if not self._running_pv_obj:
            self._running_pv_obj = PV(self.running_pv)
        return self._running_pv_obj
    
    @property
    def script_is_running(self) -> bool:
        return False
        # TODO put in when implemented
        # return self.running_pv_obj.get()
    
    @property
    def status_pv_obj(self) -> PV:
        if not self._status_pv_obj:
            self._status_pv_obj = PV(self.status_pv)
        return self._status_pv_obj
    
    @property
    def status_message(self):
        return self.status_pv_obj.get()
    
    @status_message.setter
    def status_message(self, message):
        print(message)
        # TODO add in when available
        # self.status_pv_obj.put(message)
    
    @property
    def start_pv_obj(self) -> PV:
        if not self._start_pv_obj:
            self._start_pv_obj = PV(self.start_pv)
        return self._start_pv_obj
    
    @property
    def shutoff_pv_obj(self) -> PV:
        if not self._shutoff_pv_obj:
            self._shutoff_pv_obj = PV(self.shutoff_pv)
        return self._shutoff_pv_obj
    
    @property
    def abort_pv_obj(self):
        if not self._abort_pv_obj:
            self._abort_pv_obj = PV(self.abort_pv)
        return self._abort_pv_obj
    
    @property
    def abort_requested(self):
        return self.abort_pv_obj.get()
    
    def clear_abort(self):
        self.abort_pv_obj.put(False)
    
    def check_abort(self):
        return super().check_abort()
        # TODO implement when available
        # if self.abort_requested:
        #     self.clear_abort()
        #     raise CavityAbortError(f"Abort requested for {self}")
    
    def trigger_setup(self):
        self.start_pv_obj.put(1)
    
    def trigger_abort(self):
        self.abort_pv_obj.put(1)
    
    def shut_down(self):
        self.turnOff()
        self.ssa.turn_off()
    
    def trigger_shut_down(self):
        self.shutoff_pv_obj.put(1)
    
    @property
    def ssa_cal_requested(self) -> bool:
        if not self._ssa_cal_requested_pv_obj:
            self._ssa_cal_requested_pv_obj = PV(self.ssa_cal_requested_pv)
        return bool(self._ssa_cal_requested_pv_obj.get())
    
    @property
    def auto_tune_requested(self) -> bool:
        if not self._auto_tune_requested_pv_obj:
            self._auto_tune_requested_pv_obj = PV(self.auto_tune_requested_pv)
        return bool(self._auto_tune_requested_pv_obj.get())
    
    @property
    def cav_char_requested(self) -> bool:
        if not self._cav_char_requested_pv_obj:
            self._cav_char_requested_pv_obj = PV(self.cav_char_requested_pv)
        return bool(self._cav_char_requested_pv_obj.get())
    
    @property
    def rf_ramp_requested(self) -> bool:
        if not self._rf_ramp_requested_pv_obj:
            self._rf_ramp_requested_pv_obj = PV(self.rf_ramp_requested_pv)
        return bool(self._rf_ramp_requested_pv_obj.get())
    
    def setup(self):
        self.status_message = f"Turning on {self} SSA if not on already"
        self.ssa.turn_on()
        
        self.status_message = f"Resetting {self} interlocks"
        self.reset_interlocks()
        
        if self.ssa_cal_requested:
            self.status_message = f"Running {self} SSA Calibration"
            self.turnOff()
            self.ssa.calibrate(self.ssa.drive_max)
            self.status_message = f"{self} SSA Calibrated"
        
        self.check_abort()
        
        if self.auto_tune_requested:
            self.status_message = f"Tuning {self} to Resonance"
            self.move_to_resonance(use_sela=False)
            self.status_message = f"{self} Tuned to Resonance"
        
        self.check_abort()
        
        if self.cav_char_requested:
            self.status_message = f"Running {self} Cavity Characterization"
            self.characterize()
            self.calc_probe_q_pv_obj.put(1)
            self.status_message = f"{self} Characterized"
        
        self.check_abort()
        
        if self.rf_ramp_requested:
            des_amp = self.ades
            self.status_message = f"Ramping {self} to {des_amp}"
            self.piezo.enable_feedback()
            
            if (not self.is_on
                    or (self.is_on and self.rf_mode != RF_MODE_SELAP)):
                self.ades = min(5, des_amp)
            
            self.turn_on()
            
            self.check_abort()
            
            self.set_sela_mode()
            self.walk_amp(des_amp, 0.1)
            
            self.status_message = f"Centering {self} piezo"
            self.move_to_resonance(use_sela=True)
            
            self.set_selap_mode()
            
            self.status_message = f"{self} Ramped Up to {des_amp} MV"


SETUP_CRYOMODULES: CryoDict = CryoDict(cavityClass=SetupCavity)
