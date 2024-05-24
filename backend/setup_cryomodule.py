from backend.utils import AutoLinacObject
from lcls_tools.superconducting.sc_linac import Cryomodule


class SetupCryomodule(Cryomodule, AutoLinacObject):
    def __init__(
        self,
        cryo_name,
        linac_object,
    ):
        Cryomodule.__init__(
            self,
            cryo_name=cryo_name,
            linac_object=linac_object,
        )
        AutoLinacObject.__init__(self)

        self.aact_pv = self.pv_addr("AACTMEANSUM")

    def clear_abort(self):
        for cavity in self.cavities.values():
            cavity.clear_abort()
