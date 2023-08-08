from lcls_tools.common.pyepics_tools.pyepics_utils import PV
from lcls_tools.superconducting.scLinac import Cavity, CryoDict
from lcls_tools.superconducting.sc_linac_utils import RF_MODE_SELAP


class SetupCavity(Cavity):
    
    def pv_addr(self, suffix: str):
        return super().pv_addr("AUTO:" + suffix)
    
    def __init__(self, cavityNum, rackObject):
        super().__init__(cavityNum, rackObject)
        
        # TODO populate these when they exist
        self.status_pv: str = self.pv_addr("")
        self.progress_pv: str = self.pv_addr("")
        
        # TODO implement
        self.abort_pv: str = self.pv_addr("")
        self._abort_pv_obj: PV = None
        
        # TODO need to implement
        self.off_pv: str = self.pv_addr("")
        self._off_pv_obj: PV = None
        
        self.start_pv: str = self.pv_addr("SETUPSTRT")
        self._start_pv_obj: PV = None
        
        self.ssa_cal_checkbox_pv: str = self.pv_addr("TURNON_SSASEL")
        self._ssa_cal_checkbox_pv_obj: PV = None
        
        self.auto_tune_checkbox_pv: str = self.pv_addr("TURNON_TUNESEL")
        self._auto_tune_checkbox_pv_obj: PV = None
        
        self.cav_char_checkbox_pv: str = self.pv_addr("TURNON_CHARSEL")
        self._cav_char_checkbox_pv_obj: PV = None
        
        self.rf_ramp_checkbox_pv: str = self.pv_addr("TURNON_RAMPSEL")
        self._rf_ramp_checkbox_pv_obj: PV = None
    
    @property
    def start_pv_obj(self) -> PV:
        if not self._start_pv_obj:
            self._start_pv_obj = PV(self.start_pv)
        return self._start_pv_obj
    
    @property
    def off_pv_obj(self) -> PV:
        if not self._off_pv_obj:
            self._off_pv_obj = PV(self.off_pv)
        return self._off_pv_obj
    
    @property
    def abort_pv_obj(self):
        if not self._abort_pv_obj:
            self._abort_pv_obj = PV(self.abort_pv)
        return self._abort_pv_obj
    
    def trigger_setup(self):
        self.start_pv_obj.put(1)
    
    def trigger_abort(self):
        self.abort_pv_obj.put(1)
    
    def shut_down(self):
        self.turnOff()
        self.ssa.turn_off()
    
    def trigger_shut_down(self):
        self.off_pv_obj.put(1)
    
    @property
    def ssa_cal_checkbox_option(self) -> bool:
        if not self._ssa_cal_checkbox_pv_obj:
            self._ssa_cal_checkbox_pv_obj = PV(self.ssa_cal_checkbox_pv)
        return bool(self._ssa_cal_checkbox_pv_obj.get())
    
    @property
    def auto_tune_checkbox_option(self) -> bool:
        if not self._auto_tune_checkbox_pv_obj:
            self._auto_tune_checkbox_pv_obj = PV(self.auto_tune_checkbox_pv)
        return bool(self._auto_tune_checkbox_pv_obj.get())
    
    @property
    def cav_char_checkbox_option(self) -> bool:
        if not self._cav_char_checkbox_pv_obj:
            self._cav_char_checkbox_pv_obj = PV(self.cav_char_checkbox_pv)
        return bool(self._cav_char_checkbox_pv_obj.get())
    
    @property
    def rf_ramp_checkbox_option(self) -> bool:
        if not self._rf_ramp_checkbox_pv_obj:
            self._rf_ramp_checkbox_pv_obj = PV(self.rf_ramp_checkbox_pv)
        return bool(self._rf_ramp_checkbox_pv_obj.get())
    
    def setup(self):
        print(f"Turning on {self} SSA if not on already")
        self.ssa.turn_on()
        
        print(f"Resetting {self} interlocks")
        self.reset_interlocks()
        
        if self.ssa_cal_checkbox_option:
            print(f"Running {self} SSA Calibration")
            self.turnOff()
            self.ssa.calibrate(self.ssa.drive_max)
            print(f"{self} SSA Calibrated")
        
        self.check_abort()
        
        if self.auto_tune_checkbox_option:
            print(f"Tuning {self} to Resonance")
            self.move_to_resonance(use_sela=False)
            print(f"{self} Tuned to Resonance")
        
        self.check_abort()
        
        if self.cav_char_checkbox_option:
            print(f"Running {self} Cavity Characterization")
            self.characterize()
            self.calc_probe_q_pv_obj.put(1)
            print(f"{self} Characterized")
        
        self.check_abort()
        
        if self.rf_ramp_checkbox_option:
            des_amp = self.ades
            print(f"Ramping {self} to {des_amp}")
            self.piezo.enable_feedback()
            
            if (not self.is_on
                    or (self.is_on and self.rf_mode != RF_MODE_SELAP)):
                self.ades = min(5, des_amp)
            
            self.turn_on()
            
            self.check_abort()
            
            self.set_sela_mode()
            self.walk_amp(des_amp, 0.1)
            
            print(f"Centering {self} piezo")
            self.move_to_resonance(use_sela=True)
            
            self.set_selap_mode()
            
            print(f"{self} Ramped Up to {des_amp} MV")


SETUP_CRYOMODULES: CryoDict = CryoDict(cavityClass=SetupCavity)
