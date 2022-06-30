from time import sleep

from lcls_tools.superconducting import scLinacUtils
from lcls_tools.superconducting.scLinac import Cavity, SSA, StepperTuner


class SetupCavity(Cavity):
    
    def __init__(self, cavityNum, rackObject, ssaClass=SSA,
                 stepperClass=StepperTuner):
        super().__init__(cavityNum, rackObject)
    
    def setup(self):
        self.turnOff()
        
        self.ssa.turnOn()
        
        self.selAmplitudeDesPV.put(5)
        
        self.rfModeCtrlPV.put(scLinacUtils.RF_MODE_SEL)
        
        self.turnOn()
        
        print("waiting 5s for detune to catch up")
        sleep(5)
        
        print("checking detune")
        if (self.detune_best_PV.severity == 3
                or abs(self.detune_best_PV.value) > 100):
            raise utils.DetuneError('Detune is invalid or larger than 100Hz')
        
        print("checking piezo with rf calibration")
        if not self.results.piezo_withrf_checked:
            raise utils.PiezoError('Piezo checks have not been completed')
        
        print("setting piezo to feedback")
        self.piezo.feedback_mode_PV.put(scLinacUtils.PIEZO_FEEDBACK_VALUE)
        
        self.rfModeCtrlPV.put(scLinacUtils.RF_MODE_SELA)
