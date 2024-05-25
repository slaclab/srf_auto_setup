from backend.setup_cavity import SetupCavity
from backend.setup_cryomodule import SetupCryomodule
from backend.utils import AutoLinacObject
from lcls_tools.superconducting.sc_linac import (
    Linac,
    Machine,
)


class SetupLinac(Linac, AutoLinacObject):
    @property
    def pv_prefix(self):
        return f"ACCL:{self.name}:1:"

    def __init__(
        self,
        linac_section,
        beamline_vacuum_infixes,
        insulating_vacuum_cryomodules,
        machine,
    ):
        Linac.__init__(
            self,
            linac_section=linac_section,
            beamline_vacuum_infixes=beamline_vacuum_infixes,
            insulating_vacuum_cryomodules=insulating_vacuum_cryomodules,
            machine=machine,
        )
        AutoLinacObject.__init__(self)

    def clear_abort(self):
        for cm in self.cryomodules.values():
            cm.clear_abort()


class SetupMachine(Machine, AutoLinacObject):
    @property
    def pv_prefix(self):
        return "ACCL:SYS0:SC:"

    def __init__(self):
        Machine.__init__(
            self,
            cavity_class=SetupCavity,
            cryomodule_class=SetupCryomodule,
            linac_class=SetupLinac,
        )
        AutoLinacObject.__init__(self)

    def clear_abort(self):
        for cm in self.cryomodules.values():
            cm.clear_abort()


SETUP_MACHINE = SetupMachine()
