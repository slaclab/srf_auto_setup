import argparse

from lcls_tools.common.pyepics_tools.pyepics_utils import PVInvalidError
from lcls_tools.superconducting import sc_linac_utils
from lcls_tools.superconducting.sc_linac_utils import ALL_CRYOMODULES

from setup_linac import SETUP_CRYOMODULES, SetupCavity


def main():
    global cavity_object
    
    if cavity_object.script_is_running:
        cavity_object.status_message = f"{cavity_object} script already running"
        return
    
    if args.shutdown:
        cavity_object.shut_down()
    
    else:
        try:
            cavity_object.setup()
        except sc_linac_utils.CavityAbortError:
            cavity_object.status_message = f"{cavity_object} successfully aborted"
        
        except (sc_linac_utils.StepperError, sc_linac_utils.DetuneError,
                sc_linac_utils.SSACalibrationError, PVInvalidError,
                sc_linac_utils.QuenchError,
                sc_linac_utils.CavityQLoadedCalibrationError,
                sc_linac_utils.CavityScaleFactorCalibrationError,
                sc_linac_utils.SSAFaultError, sc_linac_utils.CavityAbortError,
                sc_linac_utils.StepperAbortError, sc_linac_utils.CavityHWModeError,
                sc_linac_utils.CavityFaultError) as e:
            cavity_object.abort_flag = False
            cavity_object.steppertuner.abort_flag = False
            cavity_object.status_message = (str(e))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cryomodule', '-cm',
                        choices=ALL_CRYOMODULES, required=True,
                        help=f'Cryomodule name as a string')
    parser.add_argument('--cavity', '-cav', required=True,
                        choices=range(1, 9), type=int,
                        help=f'Cavity number as an int')
    parser.add_argument('--shutdown', '-off', action="store_true",
                        help='Turn off cavity and SSA')
    
    args = parser.parse_args()
    print(args)
    cm_name = args.cryomodule
    cav_num = args.cavity
    
    cavity_object: SetupCavity = SETUP_CRYOMODULES[cm_name].cavities[cav_num]
    
    main()
