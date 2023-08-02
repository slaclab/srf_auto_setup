import argparse

from lcls_tools.superconducting.scLinac import CRYOMODULE_OBJECTS, Cavity
from lcls_tools.superconducting.sc_linac_utils import ALL_CRYOMODULES, RF_MODE_SELAP


def setup(cavity: Cavity, ssa_cal=True, auto_tune=True, cav_char=True,
          rf_ramp=True):
    print(f"Turning on {cavity} SSA if not on already")
    cavity.ssa.turn_on()
    
    print(f"Resetting {cavity} interlocks")
    cavity.reset_interlocks()
    
    if ssa_cal:
        print(f"Running {cavity} SSA Calibration")
        cavity.turnOff()
        cavity.ssa.calibrate(cavity.ssa.drive_max)
        print(f"{cavity} SSA Calibrated")
    
    cavity.check_abort()
    
    if auto_tune:
        print(f"Tuning {cavity} to Resonance")
        cavity.move_to_resonance(use_sela=False)
        print(f"{cavity} Tuned to Resonance")
    
    cavity.check_abort()
    
    if cav_char:
        print(f"Running {cavity} Cavity Characterization")
        cavity.characterize()
        cavity.calc_probe_q_pv_obj.put(1)
        print(f"{cavity} Characterized")
    
    cavity.check_abort()
    
    if rf_ramp:
        des_amp = cavity.ades
        print(f"Ramping {cavity} to {des_amp}")
        cavity.piezo.enable_feedback()
        
        if (not cavity.is_on
                or (cavity.is_on and cavity.rf_mode != RF_MODE_SELAP)):
            cavity.ades = min(5, des_amp)
        
        cavity.turn_on()
        
        cavity.check_abort()
        
        cavity.set_sela_mode()
        cavity.walk_amp(des_amp, 0.1)
        
        print(f"Centering {cavity} piezo")
        cavity.move_to_resonance(use_sela=True)
        
        cavity.set_selap_mode()
        
        print(f"{cavity} Ramped Up to {des_amp} MV")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cryomodule', '-cm', choices=ALL_CRYOMODULES, required=True,
                        help=f'Cryomodule name as a string')
    parser.add_argument('--cavity', '-cav', required=True, choices=range(1, 9),
                        type=int, help=f'Cavity number as an int')
    parser.add_argument('--ssa_cal', '-ssa', action="store_true",
                        help='Run SSA calibration')
    parser.add_argument('--auto_tune', '-tune', action="store_true",
                        help='Tune cavity to resonance')
    parser.add_argument('--cavity_characterization', '-cav_char', action="store_true",
                        help='Run cavity characterization')
    parser.add_argument('--rf_ramp', '-ramp', action="store_true",
                        help='Ramp cavity to ADES in SELAP')
    
    args = parser.parse_args()
    print(args)
    cm_name = args.cryomodule
    cav_num = args.cavity
    
    cavity_object: Cavity = CRYOMODULE_OBJECTS[cm_name].cavities[cav_num]
    setup(cavity_object, ssa_cal=args.ssa_cal, auto_tune=args.auto_tune,
          cav_char=args.cavity_characterization, rf_ramp=args.rf_ramp)
