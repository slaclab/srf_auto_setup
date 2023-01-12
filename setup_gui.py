import dataclasses
from time import sleep
from typing import Dict, List

from PyQt5.QtCore import QRunnable, QThreadPool
from PyQt5.QtWidgets import (QCheckBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QMessageBox, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)
from epics import PV, caget, camonitor, caput
from lcls_tools.common.pydm_tools.displayUtils import ERROR_STYLESHEET, WorkerSignals
from lcls_tools.common.pyepics_tools.pyepicsUtils import PVInvalidError
from lcls_tools.superconducting import scLinacUtils
from lcls_tools.superconducting.scLinac import (CRYOMODULE_OBJECTS, Cavity,
                                                L1BHL, LINAC_TUPLES)
from lcls_tools.superconducting.scLinacUtils import (CavityHWModeError,
                                                     PIEZO_FEEDBACK_VALUE,
                                                     RF_MODE_SEL, RF_MODE_SELA,
                                                     RF_MODE_SELAP)
from pydm import Display
from pydm.widgets import PyDMLabel, PyDMSpinbox
from qtpy.QtCore import Slot


class OffWorker(QRunnable):
    def __init__(self, cavity: Cavity, status_label: QLabel):
        super().__init__()
        self.signals = WorkerSignals(status_label)
        self.cavity = cavity
    
    def run(self):
        self.signals.status.emit("Turning RF off")
        self.cavity.turnOff()
        self.signals.status.emit("Turning SSA off")
        self.cavity.ssa.turnOff()
        self.signals.finished.emit("RF and SSA off")


class SetupWorker(QRunnable):
    def __init__(self, cavity: Cavity, status_label: QLabel,
                 desAmp: float = 5,
                 ssa_cal=True, auto_tune=True, cav_char=True, rf_ramp=True):
        super().__init__()
        self.signals = WorkerSignals(status_label)
        self.cavity: Cavity = cavity
        self.desAmp = desAmp
        
        self.ssa_cal = ssa_cal
        self.auto_tune = auto_tune
        self.cav_char = cav_char
        self.rf_ramp = rf_ramp
    
    def run(self):
        try:
            if not self.desAmp:
                self.signals.status.emit(f"Turning off {self.cavity}")
                self.cavity.turnOff()
                self.cavity.ssa.turnOff()
                self.signals.status.emit(f"RF and SSA off for {self.cavity}")
            
            else:
                self.signals.status.emit(f"Resetting and turning on {self.cavity} SSA if not on already")
                self.cavity.ssa.reset()
                self.cavity.ssa.turnOn()
                
                self.signals.status.emit(f"Resetting {self.cavity} interlocks")
                self.cavity.reset_interlocks()
                
                if self.ssa_cal:
                    self.signals.status.emit(f"Running {self.cavity} SSA Calibration")
                    self.cavity.turnOff()
                    self.cavity.ssa.calibrate(self.cavity.ssa.drivemax)
                    self.signals.finished.emit(f"{self.cavity} SSA Calibrated")
                
                self.cavity.check_abort()
                
                if self.auto_tune:
                    self.signals.status.emit(f"Tuning {self.cavity} to Resonance")
                    self.cavity.move_to_resonance()
                    self.signals.finished.emit(f"{self.cavity} Tuned to Resonance")
                
                self.cavity.check_abort()
                
                if self.cav_char:
                    self.signals.status.emit(f"Running {self.cavity} Cavity Characterization")
                    self.cavity.characterize()
                    self.cavity.calc_probe_q_pv.put(1)
                    self.signals.finished.emit(f"{self.cavity} Characterized")
                
                self.cavity.check_abort()
                
                if self.rf_ramp:
                    self.signals.status.emit(f"Ramping {self.cavity} to {self.desAmp}")
                    caput(self.cavity.selAmplitudeDesPV.pvname, min(5, self.desAmp),
                          wait=True)
                    caput(self.cavity.rfModeCtrlPV.pvname, RF_MODE_SEL, wait=True)
                    caput(self.cavity.piezo.feedback_mode_PV.pvname,
                          PIEZO_FEEDBACK_VALUE, wait=True)
                    caput(self.cavity.rfModeCtrlPV.pvname, RF_MODE_SELA, wait=True)
                    self.cavity.turnOn()
                    
                    self.cavity.check_abort()
                    
                    if self.desAmp <= 10:
                        self.cavity.walk_amp(self.desAmp, 0.5)
                    
                    else:
                        self.cavity.walk_amp(10, 0.5)
                        self.cavity.walk_amp(self.desAmp, 0.1)
                    
                    caput(self.cavity.rfModeCtrlPV.pvname, RF_MODE_SELAP, wait=True)
                    
                    self.signals.finished.emit(f"{self.cavity} Ramped Up to {self.desAmp}MV")
        
        except (scLinacUtils.StepperError, scLinacUtils.DetuneError,
                scLinacUtils.SSACalibrationError, PVInvalidError,
                scLinacUtils.QuenchError,
                scLinacUtils.CavityQLoadedCalibrationError,
                scLinacUtils.CavityScaleFactorCalibrationError,
                scLinacUtils.SSAFaultError, scLinacUtils.CavityAbortError,
                scLinacUtils.StepperAbortError, CavityHWModeError) as e:
            self.cavity.abort_flag = False
            self.cavity.steppertuner.abort_flag = False
            self.signals.error.emit(str(e))


@Slot(str)
def handle_error(message: str):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error")
    msg.setInformativeText(message)
    msg.setWindowTitle("Error")
    msg.exec_()


@dataclasses.dataclass
class Settings:
    ssa_cal_checkbox: QCheckBox
    auto_tune_checkbox: QCheckBox
    cav_char_checkbox: QCheckBox
    rf_ramp_checkbox: QCheckBox


@dataclasses.dataclass
class GUICavity:
    number: int
    prefix: str
    cm: str
    settings: Settings
    parent: Display
    
    def __post_init__(self):
        self._cavity = None
        
        self._ades_pv: PV = None
        self.setup_button = QPushButton(f"Set Up Cavity {self.number}")
        
        self.abort_button: QPushButton = QPushButton("Abort")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.kill_workers)
        
        self.turn_off_button: QPushButton = QPushButton(f"Turn off Cavity {self.number}")
        self.turn_off_button.clicked.connect(self.launch_off_worker)
        
        self.setup_button.clicked.connect(self.launch_ramp_worker)
        self.aact_readback_label: PyDMLabel = PyDMLabel(init_channel=self.prefix + "AACTMEAN")
        self.aact_readback_label.alarmSensitiveBorder = True
        self.aact_readback_label.alarmSensitiveContent = True
        self.aact_readback_label.showUnits = True
        
        # Putting this here because it otherwise gets garbage collected (?!)
        self.spinbox: PyDMSpinbox = PyDMSpinbox(init_channel=self.prefix + "ADES")
        self.spinbox.alarmSensitiveContent = True
        self.spinbox.alarmSensitiveBorder = True
        self.spinbox.showUnits = True
        
        self.status_label: QLabel = QLabel("Ready for Setup")
    
    @property
    def ades_pv(self):
        if not self._ades_pv:
            self._ades_pv = PV(self.prefix + "ADES")
        return self._ades_pv
    
    def kill_workers(self):
        self.status_label.setText(f"Sending abort request for CM{self.cm} cavity {self.number}")
        self.cavity.abort_flag = True
        self.cavity.steppertuner.abort_flag = True
    
    @property
    def cavity(self):
        if not self._cavity:
            self._cavity = CRYOMODULE_OBJECTS[self.cm].cavities[self.number]
        return self._cavity
    
    def launch_off_worker(self):
        off_worker = OffWorker(cavity=self.cavity,
                               status_label=self.status_label)
        self.parent.threadpool.start(off_worker)
        print(f"Active thread count: {self.parent.threadpool.activeThreadCount()}")
    
    def launch_ramp_worker(self):
        setup_worker = SetupWorker(cavity=self.cavity,
                                   desAmp=self.spinbox.value(),
                                   status_label=self.status_label,
                                   ssa_cal=self.settings.ssa_cal_checkbox.isChecked(),
                                   auto_tune=self.settings.auto_tune_checkbox.isChecked(),
                                   cav_char=self.settings.cav_char_checkbox.isChecked(),
                                   rf_ramp=self.settings.rf_ramp_checkbox.isChecked())
        self.parent.threadpool.start(setup_worker)
        print(f"Active thread count: {self.parent.threadpool.activeThreadCount()}")


@dataclasses.dataclass
class GUICryomodule:
    linac_idx: int
    name: str
    settings: Settings
    parent: Display
    
    def __post_init__(self):
        
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=f"ACCL:L{self.linac_idx}B:{self.name}00:AACTMEANSUM")
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True
        self.setup_button: QPushButton = QPushButton(f"Set Up CM{self.name}")
        
        self.abort_button: QPushButton = QPushButton(f"Abort Action for CM{self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.kill_cavity_workers)
        
        self.turn_off_button: QPushButton = QPushButton(f"Turn off CM{self.name}")
        self.turn_off_button.clicked.connect(self.launch_turnoff_workers)
        
        self.setup_button.clicked.connect(self.launch_cavity_workers)
        self.gui_cavities: Dict[int, GUICavity] = {}
        
        for cav_num in range(1, 9):
            gui_cavity = GUICavity(cav_num,
                                   f"ACCL:L{self.linac_idx}B:{self.name}{cav_num}0:",
                                   self.name,
                                   settings=self.settings,
                                   parent=self.parent)
            self.gui_cavities[cav_num] = gui_cavity
    
    def launch_turnoff_workers(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.launch_off_worker()
            sleep(0.5)
    
    def kill_cavity_workers(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.kill_workers()
            sleep(0.5)
    
    def launch_cavity_workers(self):
        for cavity_widget in self.gui_cavities.values():
            cavity_widget.launch_ramp_worker()
            sleep(0.5)


@dataclasses.dataclass
class Linac:
    name: str
    idx: int
    cryomodule_names: List[str]
    settings: Settings
    parent: Display
    
    def __post_init__(self):
        self.setup_button: QPushButton = QPushButton(f"Set Up {self.name}")
        self.setup_button.clicked.connect(self.launch_cm_workers)
        
        self.abort_button: QPushButton = QPushButton(f"Abort Action for {self.name}")
        self.abort_button.setStyleSheet(ERROR_STYLESHEET)
        self.abort_button.clicked.connect(self.kill_cm_workers)
        
        self.aact_pv = f"ACCL:L{self.idx}B:1:AACTMEANSUM"
        self.readback_label: PyDMLabel = PyDMLabel(init_channel=self.aact_pv)
        self.readback_label.alarmSensitiveBorder = True
        self.readback_label.alarmSensitiveContent = True
        self.readback_label.showUnits = True
        self.cryomodules: List[GUICryomodule] = []
        self.cm_tab_widget: QTabWidget = QTabWidget()
        self.gui_cryomodules: Dict[str, GUICryomodule] = {}
        
        for cm_name in self.cryomodule_names:
            self.add_cm_tab(cm_name)
    
    def kill_cm_workers(self):
        for gui_cm in self.gui_cryomodules.values():
            gui_cm.kill_cavity_workers()
            sleep(0.5)
    
    def launch_cm_workers(self):
        for gui_cm in self.gui_cryomodules.values():
            gui_cm.launch_cavity_workers()
            sleep(0.5)
    
    def add_cm_tab(self, cm_name: str):
        page: QWidget = QWidget()
        vlayout: QVBoxLayout = QVBoxLayout()
        page.setLayout(vlayout)
        self.cm_tab_widget.addTab(page, f"CM{cm_name}")
        
        gui_cryomodule = GUICryomodule(linac_idx=self.idx, name=cm_name,
                                       settings=self.settings,
                                       parent=self.parent)
        self.gui_cryomodules[cm_name] = gui_cryomodule
        hlayout: QHBoxLayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(QLabel(f"CM{cm_name} Amplitude:"))
        hlayout.addWidget(gui_cryomodule.readback_label)
        hlayout.addWidget(gui_cryomodule.setup_button)
        hlayout.addWidget(gui_cryomodule.turn_off_button)
        hlayout.addWidget(gui_cryomodule.abort_button)
        hlayout.addStretch()
        
        vlayout.addLayout(hlayout)
        
        groupbox: QGroupBox = QGroupBox()
        all_cav_layout: QGridLayout = QGridLayout()
        groupbox.setLayout(all_cav_layout)
        vlayout.addWidget(groupbox)
        for cav_num in range(1, 9):
            cav_groupbox: QGroupBox = QGroupBox(f"CM{cm_name} Cavity {cav_num}")
            cav_vlayout: QVBoxLayout = QVBoxLayout()
            cav_groupbox.setLayout(cav_vlayout)
            cav_widgets = gui_cryomodule.gui_cavities[cav_num]
            cav_desamp_hlayout: QHBoxLayout = QHBoxLayout()
            cav_desamp_hlayout.addStretch()
            cav_desamp_hlayout.addWidget(QLabel("Amplitude: "))
            cav_desamp_hlayout.addWidget(cav_widgets.spinbox)
            cav_desamp_hlayout.addWidget(cav_widgets.aact_readback_label)
            cav_desamp_hlayout.addStretch()
            
            cav_vlayout.addLayout(cav_desamp_hlayout)
            cav_vlayout.addWidget(cav_widgets.setup_button)
            cav_vlayout.addWidget(cav_widgets.turn_off_button)
            cav_vlayout.addWidget(cav_widgets.status_label)
            cav_vlayout.addWidget(cav_widgets.abort_button)
            all_cav_layout.addWidget(cav_groupbox,
                                     0 if cav_num in range(1, 5) else 1,
                                     (cav_num - 1) % 4)


class SetupGUI(Display):
    def ui_filename(self):
        return 'setup.ui'
    
    def __init__(self, parent=None, args=None):
        super(SetupGUI, self).__init__(parent=parent, args=args)
        self.threadpool = QThreadPool()
        print(f"Max thread count: {self.threadpool.maxThreadCount()}")
        
        self.settings = Settings(ssa_cal_checkbox=self.ui.ssa_cal_checkbox,
                                 auto_tune_checkbox=self.ui.autotune_checkbox,
                                 cav_char_checkbox=self.ui.cav_char_checkbox,
                                 rf_ramp_checkbox=self.ui.rf_ramp_checkbox)
        
        self.linac_widgets: List[Linac] = []
        for linac_idx in range(0, 4):
            self.linac_widgets.append(Linac(f"L{linac_idx}B", linac_idx,
                                            LINAC_TUPLES[linac_idx][1],
                                            settings=self.settings,
                                            parent=self))
        
        self.linac_widgets.insert(2, Linac("L1BHL", 1, L1BHL,
                                           settings=self.settings, parent=self))
        self.update_readback()
        
        linac_tab_widget: QTabWidget = self.ui.tabWidget_linac
        
        for linac in self.linac_widgets:
            page: QWidget = QWidget()
            vlayout: QVBoxLayout = QVBoxLayout()
            page.setLayout(vlayout)
            linac_tab_widget.addTab(page, linac.name)
            
            hlayout: QHBoxLayout = QHBoxLayout()
            hlayout.addStretch()
            hlayout.addWidget(QLabel(f"{linac.name} Amplitude:"))
            hlayout.addWidget(linac.readback_label)
            hlayout.addWidget(linac.setup_button)
            hlayout.addWidget(linac.abort_button)
            hlayout.addStretch()
            
            vlayout.addLayout(hlayout)
            vlayout.addWidget(linac.cm_tab_widget)
            camonitor(linac.aact_pv, callback=self.update_readback)
    
    def update_readback(self, **kwargs):
        readback = 0
        for linac_idx in range(4):
            aact_pv = f"ACCL:L{linac_idx}B:1:AACTMEANSUM"
            readback += caget(aact_pv)
        self.ui.machine_readback_label.setText(f"{readback:.2f} MV")
