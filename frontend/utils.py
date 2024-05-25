import dataclasses

from PyQt5.QtWidgets import QCheckBox


@dataclasses.dataclass
class Settings:
    ssa_cal_checkbox: QCheckBox
    auto_tune_checkbox: QCheckBox
    cav_char_checkbox: QCheckBox
    rf_ramp_checkbox: QCheckBox


def make_setting_checkbox(text: str) -> QCheckBox:
    checkbox = QCheckBox(text)
    checkbox.setChecked(True)
    checkbox.setToolTip("Leave all checked if unsure")
    return checkbox
