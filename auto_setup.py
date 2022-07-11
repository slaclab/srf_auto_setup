from time import sleep

from epics import caget, caput
from lcls_tools.common.pyepics_tools.pyepicsUtils import PV
from lcls_tools.superconducting import scLinacUtils
from lcls_tools.superconducting.scLinac import (Cavity, CryoDict, Piezo, SSA, StepperTuner)

PIEZO_WITH_RF_GRAD = 6.5


class SSACalError(Exception):
    pass


class DetuneError(Exception):
    pass


class QuenchError(Exception):
    pass


class SetupSSA(SSA):
    def __init__(self, cavity):
        super().__init__(cavity)
        
        self.maxdrive_pv: str = self.pvPrefix + "DRV_MAX_REQ"
        self.reactive_power_fraction_PV: PV = PV(self.pvPrefix + "REACTIVE")
    
    def calibrate(self, drivemax):
        print(f"Trying SSA calibration with drivemax {drivemax}")
        if drivemax < 0.6:
            raise SSACalError("Requested drive max too low")
        
        while caput(self.maxdrive_pv, drivemax, wait=True) != 1:
            print("Setting max drive")
        
        try:
            self.runCalibration()
        
        except scLinacUtils.SSACalibrationError as e:
            print("SSA Calibration failed, retrying")
            self.calibrate(drivemax - 0.05)
    
    @property
    def drivemax(self):
        if self.cavity.cryomodule.isHarmonicLinearizer:
            return 1
        else:
            return 0.8


class SetupCavity(Cavity):
    
    def __init__(self, cavityNum, rackObject, ssaClass=SetupSSA,
                 stepperClass=StepperTuner, piezoClass=Piezo):
        super().__init__(cavityNum, rackObject, ssaClass=SetupSSA)
        self.quench_bypass_pv: str = self.pvPrefix + "QUENCH_BYP"
        self.quench_latch_pv: str = self.pvPrefix + "QUENCH_LTCH"
        self.ades_max_PV: PV = PV(self.pvPrefix + "ADES_MAX")
    
    def auto_tune(self):
        amp = PIEZO_WITH_RF_GRAD * self.length
        cm_name = self.cryomodule.name
        cav_num = self.number
        print(f"setting CM{cm_name} cavity {cav_num} to {amp}MV")
        caput(self.selAmplitudeDesPV.pvname,
              min(caget(self.ades_max_PV.pvname), amp), wait=True)
        print(f"setting CM{cm_name} cavity {cav_num} to SEL")
        caput(self.rfModeCtrlPV.pvname, scLinacUtils.RF_MODE_SEL, wait=True)
        self.turnOn()
        
        piezo = self.piezo
        sleep(2)
        print(f"Enabling piezo for CM{cm_name} cavity {cav_num}")
        caput(piezo.enable_PV.pvname, scLinacUtils.PIEZO_ENABLE_VALUE, wait=True)
        print(f"Setting piezo for CM{cm_name} cavity {cav_num} to manual")
        caput(piezo.feedback_mode_PV.pvname, scLinacUtils.PIEZO_MANUAL_VALUE,
              wait=True)
        print(f"Setting piezo DC setpoint for CM{cm_name} cavity {cav_num} to 0")
        caput(piezo.dc_setpoint_PV.pvname, 0, wait=True)
        print(f"Setting piezo bias voltage for CM{cm_name} cavity {cav_num} to 25")
        caput(piezo.bias_voltage_PV.pvname, 25, wait=True)
        
        sleep(2)
        
        if (self.detune_best_PV.severity == 3
                or abs(caget(self.detune_best_PV.pvname)) > 10000):
            raise DetuneError(f"Tuning for CM{cm_name} cavity"
                              f" {cav_num} needs to be checked"
                              " (either invalid or above 10k)")
        
        while caget(self.detune_best_PV.pvname) > 50:
            if caget(self.quench_latch_pv) == 1:
                raise QuenchError(f"CM{cm_name} cavity"
                                  f" {cav_num} quenched, aborting autotune")
            est_steps = int(0.9 * caget(self.detune_best_PV.pvname)
                            * (scLinacUtils.ESTIMATED_MICROSTEPS_PER_HZ_HL
                               if self.cryomodule.isHarmonicLinearizer
                               else scLinacUtils.ESTIMATED_MICROSTEPS_PER_HZ))
            print(f"Moving stepper for CM{cm_name} cavity {cav_num} {est_steps} steps")
            self.steppertuner.move(est_steps,
                                   maxSteps=scLinacUtils.DEFAULT_STEPPER_MAX_STEPS,
                                   speed=scLinacUtils.MAX_STEPPER_SPEED)
    
    def setup(self, desAmp: float = 5):
        print(f"setting up cm{self.cryomodule.name} cavity {self.number}")
        self.turnOff()
        self.ssa.calibrate(self.ssa.drivemax)
        
        caput(self.quench_bypass_pv, 1, wait=True)
        self.runCalibration(3e7, 5e7)
        caput(self.quench_bypass_pv, 0, wait=True)
        
        self.auto_tune()
        
        caput(self.selAmplitudeDesPV.pvname, min(5, desAmp), wait=True)
        caput(self.rfModeCtrlPV.pvname, scLinacUtils.RF_MODE_SEL, wait=True)
        caput(self.piezo.feedback_mode_PV.pvname, scLinacUtils.PIEZO_FEEDBACK_VALUE, wait=True)
        caput(self.rfModeCtrlPV.pvname, scLinacUtils.RF_MODE_SELA, wait=True)
        
        if desAmp <= 10:
            self.walk_amp(desAmp, 0.5)
        
        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(desAmp, 0.1)
        
        caput(self.rfModeCtrlPV.pvname, scLinacUtils.RF_MODE_SELAP, wait=True)
        print(f"CM{self.cryomodule.name} Cavity{self.number} set up")
    
    def walk_amp(self, des_amp, step_size):
        print(f"walking CM{self.cryomodule.name} cavity {self.number} to {des_amp}")
        while caget(self.selAmplitudeDesPV.pvname) <= (des_amp - step_size):
            if caget(self.quench_latch_pv) == 1:
                raise QuenchError(f"Quench detected on CM{self.cryomodule.name}"
                                  f" cavity {self.number}, aborting rampup")
            caput(self.selAmplitudeDesPV.pvname, self.selAmplitudeDesPV.value + step_size, wait=True)
        if caget(self.selAmplitudeDesPV.pvname) != des_amp:
            caput(self.selAmplitudeDesPV.pvname, des_amp)
        
        print(f"CM{self.cryomodule.name} cavity {self.number} at {des_amp}")


SETUP_CRYOMODULES = CryoDict(cavityClass=SetupCavity, ssaClass=SetupSSA)
