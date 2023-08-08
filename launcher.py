import argparse

from lcls_tools.superconducting.sc_linac_utils import ALL_CRYOMODULES

from setup_linac import SETUP_CRYOMODULES, SetupCavity

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
    parser.add_argument('--abort', '-abort', action="store_true",
                        help='Abort cavity setup')
    
    args = parser.parse_args()
    print(args)
    cm_name = args.cryomodule
    cav_num = args.cavity
    
    cavity_object: SetupCavity = SETUP_CRYOMODULES[cm_name].cavities[cav_num]
    
    if args.abort:
        # TODO rewrite lcls tools for this
        cavity_object.abort_flag = True
    
    elif args.shutdown:
        cavity_object.shut_down()
    
    else:
        cavity_object.setup()
