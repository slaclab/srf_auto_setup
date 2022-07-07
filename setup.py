from time import sleep

from lcls_tools.common.pyepics_tools.pyepicsUtils import PV
from lcls_tools.superconducting import scLinacUtils
from lcls_tools.superconducting.scLinac import (Cavity, CryoDict, Piezo, SSA, StepperTuner)


class SSACalError(Exception):
    pass


class DetuneError(Exception):
    pass


class SetupSSA(SSA):
    def __init__(self, cavity):
        super().__init__(cavity)
        
        self.maxdrive_PV: PV = PV(self.pvPrefix + "DRV_MAX_REQ")
        self.reactive_power_fraction_PV: PV = PV(self.pvPrefix + "REACTIVE")
    
    def calibrate(self, drivemax):
        print(f"Trying SSA calibration with drivemax {drivemax}")
        if drivemax < 0.6:
            raise SSACalError("Requested drive max too low")
        
        self.maxdrive_PV.put(drivemax)
        
        try:
            self.runCalibration()
        except scLinacUtils.SSACalibrationError as e:
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
        self.quench_bypass_pv: PV = PV(self.pvPrefix + "QUENCH_BYP")
    
    def auto_tune(self):
        self.selAmplitudeDesPV.put(7)
        self.rfModeCtrlPV.put(scLinacUtils.RF_MODE_SEL)
        self.turnOn()
        piezo = self.piezo
        sleep(2)
        piezo.enable_PV.put(scLinacUtils.PIEZO_ENABLE_VALUE)
        piezo.feedback_mode_PV.put(scLinacUtils.PIEZO_MANUAL_VALUE)
        
        if (self.detune_rfs_PV.severity == 3
                or abs(self.detune_rfs_PV.value) > 10000):
            raise DetuneError("Cavity tuning needs to be checked")
        
        while self.detune_rfs_PV.value > 50:
            est_steps = int(0.9 * self.detune_best_PV.value
                            * (scLinacUtils.ESTIMATED_MICROSTEPS_PER_HZ_HL
                               if self.cryomodule.isHarmonicLinearizer
                               else scLinacUtils.ESTIMATED_MICROSTEPS_PER_HZ))
            self.steppertuner.move(est_steps,
                                   maxSteps=scLinacUtils.DEFAULT_STEPPER_MAX_STEPS,
                                   speed=scLinacUtils.MAX_STEPPER_SPEED)
    
    def setup(self, desAmp: float = 5):
        print(f"setting up cm{self.cryomodule.name} cavity {self.number}")
        self.ssa.calibrate(self.ssa.drivemax)
        self.auto_tune()
        self.quench_bypass_pv.put(1)
        self.runCalibration(3e7, 5e7)
        self.quench_bypass_pv.put(0)
        
        self.selAmplitudeDesPV.put(desAmp)
        self.rfModeCtrlPV.put(scLinacUtils.RF_MODE_SEL)
        self.piezo.feedback_mode_PV.put(scLinacUtils.PIEZO_FEEDBACK_VALUE)
        self.rfModeCtrlPV.put(scLinacUtils.RF_MODE_SELA)
        print(f"CM{self.cryomodule.name} Cavity{self.number} set up")


SETUP_CRYOMODULES = CryoDict(cavityClass=SetupCavity, ssaClass=SetupSSA)
