#! /usr/bin/env python

import os
import pickle
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from subprocess import (call)

import ctk
import dicom
import qt
import slicer
from joblib import cpu_count

__author__ = 'Alessandro Delmonte'
__email__ = 'delmonte.ale92@gmail.com'


def pipe(cmd, verbose=False, my_env=os.environ):
    if verbose:
        print 'Processing command: ' + str(cmd)

    slicer.app.processEvents()
    return call(cmd, shell=True, stdin=None, stdout=None, stderr=None, executable="/usr/bin/zsh", env=my_env)


def pickle_open(path):
    with open(path, 'rb') as handle:
        env = pickle.load(handle)
        return env


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


class DiffusionPelvis:
    def __init__(self, parent):
        parent.title = 'DWI Processing'
        parent.categories = ['Diffusion Pelvis']
        parent.dependencies = []
        parent.contributors = ['Alessandro Delmonte (IMAG2)']
        parent.helpText = '''Tools for pelvic diffusion data preprocessing and analysis, inter-modalities registration
		and diffusion tensor measures extraction.\n Pickle the shell environment before using this module.'''
        parent.acknowledgementText = '''Module developed for 3DSlicer (<a>http://www.slicer.org</a>)\n
		Preprocessing based on MRTrix3 (<a>http://www.mrtrix.org</a>)\n
		Registration based on ANTs (<a>http://stnava.github.io/ANTs/</a>)
		'''

        self.parent = parent

        moduleDir = os.path.dirname(self.parent.path)
        iconPath = os.path.join(moduleDir, 'Resources', 'icon.png')
        if os.path.isfile(iconPath):
            parent.icon = qt.QIcon(iconPath)

        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['DiffusionPelvis'] = self.runTest

    def __repr__(self):
        return 'DiffusionPelvis(parent={})'.format(self.parent)

    def __str__(self):
        return 'DiffusionPelvis module initialization class.'

    @staticmethod
    def runTest():
        tester = DiffusionPelvisTest()
        tester.runTest()


class DiffusionPelvisWidget:
    def __init__(self, parent=None):
        self.moduleName = self.__class__.__name__
        if self.moduleName.endswith('Widget'):
            self.moduleName = self.moduleName[:-6]
        settings = qt.QSettings()
        try:
            self.developerMode = settings.value('Developer/DeveloperMode').lower() == 'true'
        except AttributeError:
            self.developerMode = settings.value('Developer/DeveloperMode') is True

        self.logic = DiffusionPelvisLogic()

        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()

        if not parent:
            self.setup()
            self.parent.show()

    def __repr__(self):
        return 'DiffusionPelvisWidget(parent={})'.format(self.parent)

    def __str__(self):
        return 'DiffusionPelvis GUI class'

    def setup(self):

        preprocesssingCollapsibleButton = ctk.ctkCollapsibleButton()
        preprocesssingCollapsibleButton.text = 'Preprocessing'

        self.layout.addWidget(preprocesssingCollapsibleButton)

        preprocessingFormLayout = qt.QFormLayout(preprocesssingCollapsibleButton)

        self.dialogfolder = qt.QFileDialog()
        self.dialogfolder.FileMode(2)
        self.dialogfolder.setFileMode(4)
        self.dialogfolderbutton = qt.QPushButton('Select DICOM Directory')
        self.dialogfolderbutton.enabled = True

        self.dialogfolderbutton.connect('clicked(bool)', self.onApplydialogfolderbutton)
        preprocessingFormLayout.addRow('Input DICOM DWI: ', self.dialogfolderbutton)

        self.maskSelector = slicer.qMRMLNodeComboBox()
        self.maskSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.maskSelector.selectNodeUponCreation = True
        self.maskSelector.addEnabled = False
        self.maskSelector.removeEnabled = False
        self.maskSelector.noneEnabled = True
        self.maskSelector.showHidden = False
        self.maskSelector.renameEnabled = False
        self.maskSelector.showChildNodeTypes = False
        self.maskSelector.setMRMLScene(slicer.mrmlScene)

        self.maskNode = self.maskSelector.currentNode()

        self.maskSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onmaskSelect)
        preprocessingFormLayout.addRow('Whole Pelvis Mask: ', self.maskSelector)

        self.outputSelector = slicer.qMRMLNodeComboBox()
        self.outputSelector.nodeTypes = ['vtkMRMLDiffusionWeightedVolumeNode']
        self.outputSelector.selectNodeUponCreation = True
        self.outputSelector.addEnabled = True
        self.outputSelector.removeEnabled = False
        self.outputSelector.noneEnabled = False
        self.outputSelector.showHidden = False
        self.outputSelector.renameEnabled = True
        self.outputSelector.showChildNodeTypes = False
        self.outputSelector.setMRMLScene(slicer.mrmlScene)

        self.outputSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onoutputSelect)
        preprocessingFormLayout.addRow('Output DWI preprocessed: ', self.outputSelector)

        self.check_denoising = qt.QCheckBox('Denoising')
        self.check_denoising.setChecked(True)
        self.check_gibbs = qt.QCheckBox('Gibbs Artifact Removal')
        self.check_gibbs.setChecked(True)
        self.check_preproc = qt.QCheckBox('Motion && Eddy Currents Corrections')
        self.check_preproc.setChecked(False)

        preprocessingFormLayout.addRow('Options', self.check_denoising)
        preprocessingFormLayout.addRow('    ', self.check_gibbs)
        preprocessingFormLayout.addRow('    ', self.check_preproc)

        self.preprocButton = qt.QPushButton('Preprocess')
        self.preprocButton.toolTip = 'Apply the selected operations to the input DICOM directory.'
        self.preprocButton.enabled = True

        self.preprocButton.connect('clicked(bool)', self.onpreprocButton)
        preprocessingFormLayout.addRow(self.preprocButton)

        registrationCollapsibleButton = ctk.ctkCollapsibleButton()
        registrationCollapsibleButton.text = 'Registration'

        self.layout.addWidget(registrationCollapsibleButton)

        registrationFormLayout = qt.QFormLayout(registrationCollapsibleButton)

        self.DWISelector = slicer.qMRMLNodeComboBox()
        self.DWISelector.nodeTypes = ['vtkMRMLDiffusionWeightedVolumeNode']
        self.DWISelector.selectNodeUponCreation = True
        self.DWISelector.addEnabled = False
        self.DWISelector.removeEnabled = False
        self.DWISelector.noneEnabled = False
        self.DWISelector.showHidden = False
        self.DWISelector.renameEnabled = True
        self.DWISelector.showChildNodeTypes = False
        self.DWISelector.setMRMLScene(slicer.mrmlScene)

        self.dwiNode = self.DWISelector.currentNode()

        self.DWISelector.connect('currentNodeChanged(vtkMRMLNode*)', self.ondwiSelect)
        registrationFormLayout.addRow('Input DWI: ', self.DWISelector)

        self.t2Selector = slicer.qMRMLNodeComboBox()
        self.t2Selector.nodeTypes = ['vtkMRMLScalarVolumeNode']
        self.t2Selector.selectNodeUponCreation = True
        self.t2Selector.addEnabled = False
        self.t2Selector.removeEnabled = False
        self.t2Selector.noneEnabled = False
        self.t2Selector.showHidden = False
        self.t2Selector.renameEnabled = False
        self.t2Selector.showChildNodeTypes = False
        self.t2Selector.setMRMLScene(slicer.mrmlScene)

        self.t2Node = self.t2Selector.currentNode()

        self.t2Selector.connect('currentNodeChanged(vtkMRMLNode*)', self.ont2Select)
        registrationFormLayout.addRow('Input T2 Volume: ', self.t2Selector)

        self.b0maskSelector = slicer.qMRMLNodeComboBox()
        self.b0maskSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.b0maskSelector.selectNodeUponCreation = False
        self.b0maskSelector.addEnabled = False
        self.b0maskSelector.removeEnabled = False
        self.b0maskSelector.noneEnabled = True
        self.b0maskSelector.showHidden = False
        self.b0maskSelector.renameEnabled = False
        self.b0maskSelector.showChildNodeTypes = False
        self.b0maskSelector.setMRMLScene(slicer.mrmlScene)

        self.b0maskNode = self.b0maskSelector.currentNode()

        self.b0maskSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onb0maskSelect)
        registrationFormLayout.addRow('b0 Whole Pelvis Mask: ', self.b0maskSelector)

        self.t2maskSelector = slicer.qMRMLNodeComboBox()
        self.t2maskSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.t2maskSelector.selectNodeUponCreation = False
        self.t2maskSelector.addEnabled = False
        self.t2maskSelector.removeEnabled = False
        self.t2maskSelector.noneEnabled = True
        self.t2maskSelector.showHidden = False
        self.t2maskSelector.renameEnabled = False
        self.t2maskSelector.showChildNodeTypes = False
        self.t2maskSelector.setMRMLScene(slicer.mrmlScene)

        self.t2maskNode = self.b0maskSelector.currentNode()

        self.t2maskSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.ont2maskSelect)
        registrationFormLayout.addRow('T2 Whole Pelvis Mask: ', self.t2maskSelector)

        self.outDWISelector = slicer.qMRMLNodeComboBox()
        self.outDWISelector.nodeTypes = ['vtkMRMLDiffusionWeightedVolumeNode']
        self.outDWISelector.selectNodeUponCreation = True
        self.outDWISelector.addEnabled = True
        self.outDWISelector.removeEnabled = False
        self.outDWISelector.noneEnabled = False
        self.outDWISelector.showHidden = False
        self.outDWISelector.renameEnabled = True
        self.outDWISelector.showChildNodeTypes = False
        self.outDWISelector.setMRMLScene(slicer.mrmlScene)

        self.dwiNode = self.outDWISelector.currentNode()

        self.outDWISelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onoutdwiSelect)
        registrationFormLayout.addRow('Output DWI: ', self.outDWISelector)

        self.regButton = qt.QPushButton('Register')
        self.regButton.toolTip = 'Register the DWI on the T2 image'
        self.regButton.enabled = True

        self.regButton.connect('clicked(bool)', self.onregButton)
        registrationFormLayout.addRow(self.regButton)

        measuresCollapsibleButton = ctk.ctkCollapsibleButton()
        measuresCollapsibleButton.text = 'Measures'

        self.layout.addWidget(measuresCollapsibleButton)

        measuresFormLayout = qt.QFormLayout(measuresCollapsibleButton)

        self.mDWISelector = slicer.qMRMLNodeComboBox()
        self.mDWISelector.nodeTypes = ['vtkMRMLDiffusionWeightedVolumeNode']
        self.mDWISelector.selectNodeUponCreation = True
        self.mDWISelector.addEnabled = False
        self.mDWISelector.removeEnabled = False
        self.mDWISelector.noneEnabled = False
        self.mDWISelector.showHidden = False
        self.mDWISelector.renameEnabled = True
        self.mDWISelector.showChildNodeTypes = False
        self.mDWISelector.setMRMLScene(slicer.mrmlScene)

        self.mdwiNode = self.mDWISelector.currentNode()

        self.mDWISelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onmdwiSelect)
        measuresFormLayout.addRow('Input DWI: ', self.mDWISelector)

        self.measuremaskSelector = slicer.qMRMLNodeComboBox()
        self.measuremaskSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.measuremaskSelector.selectNodeUponCreation = True
        self.measuremaskSelector.addEnabled = False
        self.measuremaskSelector.removeEnabled = False
        self.measuremaskSelector.noneEnabled = True
        self.measuremaskSelector.showHidden = False
        self.measuremaskSelector.renameEnabled = False
        self.measuremaskSelector.showChildNodeTypes = False
        self.measuremaskSelector.setMRMLScene(slicer.mrmlScene)

        self.measuremaskNode = self.measuremaskSelector.currentNode()

        self.measuremaskSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onmeasuremaskSelect)
        measuresFormLayout.addRow('Whole Pelvis Mask: ', self.measuremaskSelector)

        self.mapSelector = slicer.qMRMLNodeComboBox()
        self.mapSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
        self.mapSelector.selectNodeUponCreation = True
        self.mapSelector.addEnabled = True
        self.mapSelector.removeEnabled = False
        self.mapSelector.noneEnabled = False
        self.mapSelector.showHidden = False
        self.mapSelector.renameEnabled = False
        self.mapSelector.showChildNodeTypes = False
        self.mapSelector.setMRMLScene(slicer.mrmlScene)

        self.mapNode = self.mapSelector.currentNode()

        self.mapSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onmapSelect)
        measuresFormLayout.addRow('Output Metric Volume: ', self.mapSelector)

        self.radio_b0 = qt.QRadioButton('b0')
        self.radio_b0.setChecked(True)
        self.radio_fa = qt.QRadioButton('Fractional Anisotropy')
        self.radio_md = qt.QRadioButton('Mean Diffusivity')

        measuresFormLayout.addRow('Measure', self.radio_b0)
        measuresFormLayout.addRow('    ', self.radio_fa)
        measuresFormLayout.addRow('    ', self.radio_md)

        self.measureButton = qt.QPushButton('Extract')
        self.measureButton.toolTip = 'Extract the selected metric.'
        self.measureButton.enabled = True

        self.measureButton.connect('clicked(bool)', self.onmeasureButton)
        measuresFormLayout.addRow(self.measureButton)

        if self.developerMode:
            """Developer interface"""
            reloadCollapsibleButton = ctk.ctkCollapsibleButton()
            reloadCollapsibleButton.text = 'Advanced - Reload && Test'
            reloadCollapsibleButton.collapsed = False
            self.layout.addWidget(reloadCollapsibleButton)
            reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

            self.reloadButton = qt.QPushButton('Reload')
            self.reloadButton.toolTip = 'Reload this module.'
            self.reloadButton.name = 'DiffusionPelvis Reload'
            reloadFormLayout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

            self.reloadAndTestButton = qt.QPushButton('Reload and Test')
            self.reloadAndTestButton.toolTip = 'Reload this module and then run the self tests.'
            reloadFormLayout.addWidget(self.reloadAndTestButton)
            self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

        self.layout.addStretch(1)

    def onApplydialogfolderbutton(self):
        self.dir = self.dialogfolder.getExistingDirectory()
        self.dialogfolderbutton.setText(self.dir)

    def onmaskSelect(self):
        self.maskNode = self.maskSelector.currentNode()

    def onoutputSelect(self):
        self.outputNode = self.outputSelector.currentNode()

    def onpreprocButton(self):

        loadingbar = qt.QProgressDialog(slicer.util.mainWindow())
        loadingbar.maximum = 8
        loadingbar.minimum = 0
        loadingbar.windowTitle = 'Preprocessing...'
        loadingbar.labelText = 'Saving Mask File...'
        slicer.app.processEvents()

        if self.dir and self.outputNode:

            if self.maskNode:
                mask_dir = os.path.join(self.logic.tmp, 'whole_pelvis_mask.nii')
                properties = {}
                properties['useCompression'] = 0
                slicer.util.saveNode(self.maskNode, mask_dir, properties)
                loadingbar.value = 1
                loadingbar.labelText = 'Denoising...'
                slicer.app.processEvents()
            else:
                mask_dir = None
            nii_path, bval_path, bvec_path = self.logic.preproc(self.dir, self.check_denoising.isChecked(),
                                                                self.check_gibbs.isChecked(),
                                                                self.check_preproc.isChecked(),
                                                                mask_dir, loadingbar)

            parameters = {}
            parameters['conversionMode'] = 'FSLToNrrd'
            parameters['outputVolume'] = self.outputNode.GetID()
            parameters['fslNIFTIFile'] = nii_path
            parameters['inputBValues'] = bval_path
            parameters['inputBVectors'] = bvec_path
            parameters['allowLossyConversion'] = True
            parameters['transpose'] = True
            converter = slicer.modules.dwiconvert
            slicer.cli.runSync(converter, None, parameters)

    def ondwiSelect(self):
        self.dwiNode = self.DWISelector.currentNode()

    def ont2Select(self):
        self.t2Node = self.t2Selector.currentNode()

    def onb0maskSelect(self):
        self.b0maskNode = self.b0maskSelector.currentNode()

    def ont2maskSelect(self):
        self.t2maskNode = self.t2maskSelector.currentNode()

    def onoutdwiSelect(self):
        self.outdwiNode = self.outDWISelector.currentNode()

    def onregButton(self):
        if self.dwiNode and self.t2Node:
            data_path = os.path.join(self.logic.tmp, 'data.nii')
            bval_path = os.path.join(self.logic.tmp, 'data.bval')
            bvec_path = os.path.join(self.logic.tmp, 'data.bvec')
            parameters = {}
            parameters['conversionMode'] = 'NrrdToFSL'
            parameters['inputVolume'] = self.dwiNode.GetID()
            parameters['outputNiftiFile'] = data_path
            parameters['outputBValues'] = bval_path
            parameters['outputBVectors'] = bvec_path
            converter = slicer.modules.dwiconvert
            slicer.cli.runSync(converter, None, parameters)

            t2_path = os.path.join(self.logic.tmp, 't2.nii')
            properties = {}
            properties['useCompression'] = 0
            slicer.util.saveNode(self.t2Node, t2_path, properties)

            properties = {}
            properties['useCompression'] = 0

            if self.b0maskNode:
                b0mask_path = os.path.join(self.logic.tmp, 'b0mask.nii')
                slicer.util.saveNode(self.b0maskNode, b0mask_path, properties)
            else:
                b0mask_path = None

            if self.t2maskNode:
                t2mask_path = os.path.join(self.logic.tmp, 't2mask.nii')
                slicer.util.saveNode(self.t2maskNode, t2mask_path, properties)
            else:
                t2mask_path = None

            warped_path = self.logic.register(data_path, bval_path, bvec_path, t2_path, t2mask_path, b0mask_path)

            parameters = {}
            parameters['conversionMode'] = 'FSLToNrrd'
            parameters['outputVolume'] = self.outdwiNode.GetID()
            parameters['fslNIFTIFile'] = warped_path
            parameters['inputBValues'] = bval_path
            parameters['inputBVectors'] = bvec_path
            parameters['allowLossyConversion'] = True
            parameters['transpose'] = True
            converter = slicer.modules.dwiconvert
            slicer.cli.runSync(converter, None, parameters)

    def onmdwiSelect(self):
        self.mdwiNode = self.mDWISelector.currentNode()

    def onmapSelect(self):
        self.mapNode = self.mapSelector.currentNode()

    def onmeasuremaskSelect(self):
        self.measuremaskNode = self.measuremaskSelector.currentNode()

    def onmeasureButton(self):
        switch = {'b0': self.radio_b0.isChecked(), 'fa': self.radio_fa.isChecked(), 'md': self.radio_md.isChecked()}

        data_path = os.path.join(self.logic.tmp, 'measure_data.nii')
        bval_path = os.path.join(self.logic.tmp, 'measure.bval')
        bvec_path = os.path.join(self.logic.tmp, 'measure.bvec')
        parameters = {}
        parameters['conversionMode'] = 'NrrdToFSL'
        parameters['inputVolume'] = self.mdwiNode.GetID()
        parameters['outputNiftiFile'] = data_path
        parameters['outputBValues'] = bval_path
        parameters['outputBVectors'] = bvec_path
        converter = slicer.modules.dwiconvert
        slicer.cli.runSync(converter, None, parameters)

        properties = {}
        properties['useCompression'] = 0

        if self.b0maskNode:
            measuremask_path = os.path.join(self.logic.tmp, 'measure_mask.nii')
            slicer.util.saveNode(self.b0maskNode, measuremask_path, properties)
        else:
            measuremask_path = None

        path = self.logic.extract(data_path, bval_path, bvec_path, measuremask_path, switch)

        _, upNode = slicer.util.loadVolume(path, returnNode=True)
        # _, self.mapNode = slicer.util.loadVolume(path,
        #                                          properties={'name': self.mapNode.GetID(), 'show': True,
        #                                                      'autoWindowLevel': True},
        #                                          returnNode=True)

        # upNode.CopyWithScene(self.mapNode)
        self.mapNode.CopyWithScene(upNode)
        # self.mapNode = slicer.vtkSlicerVolumesLogic().CloneVolume(slicer.mrmlScene, upNode)
        # upNode.SetName(self.mapNode.GetName())

    def onReload(self):
        slicer.util.reloadScriptedModule(self.moduleName)

    def onReloadAndTest(self):
        try:
            self.onReload()
            test = slicer.selfTests[self.moduleName]
            test()
        except Exception, e:
            import traceback
            traceback.print_exc()
            errorMessage = 'Reload and Test: Exception!\n\n" + str(e) + "\n\nSee Python Console for Stack Trace'
            slicer.util.errorDisplay(errorMessage)

    def cleanup(self):
        pass


class DiffusionPelvisLogic:
    def __init__(self):
        try:
            if os.name == 'nt':
                import win32api, win32process, win32con
                pid = win32api.GetCurrentProcessId()
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
                win32process.SetPriorityClass(handle, win32process.NORMAL_PRIORITY_CLASS)
            elif 'linux' in sys.platform.lower():
                os.nice(0)
        except:
            pass

        self.tmp = tempfile.mkdtemp()
        self.my_env = pickle_open('/opt/Slicer-4.8.1-linux-amd64/environ.pickle')

    @property
    def tmp(self):
        return self._tmp

    @tmp.setter
    def tmp(self, value):
        self._tmp = value

    def __del__(self):
        shutil.rmtree(self.tmp)

    def __repr__(self):
        return 'DiffusionPelvisLogic()'

    def __str__(self):
        return 'DiffusionPelvis implementation class'

    def preproc(self, dir, check_denoising, check_gibbs, check_preproc, mask, loadingbar):
        loadingbar.value = 2
        loadingbar.labelText = 'Reading DICOM header...'
        slicer.app.processEvents()
        lstFilesDCM = []
        for dirName, subdirList, fileList in os.walk(dir):
            for filename in fileList:
                lstFilesDCM.append(os.path.join(dirName, filename))
        RefDs = dicom.read_file(lstFilesDCM[0])
        if RefDs.InPlanePhaseEncodingDirection == 'COL':
            phase_encoding_direction = 'AP '
        elif RefDs.InPlanePhaseEncodingDirection == 'ROW':
            phase_encoding_direction = 'LR '
        else:
            phase_encoding_direction = 'AP '

        try:
            diff_dir = RefDs[0x0019, 0x10e0].value
            diff_dir = int(diff_dir)
        except:
            diff_dir = 25

        win_size = 2
        while win_size ** 3 < diff_dir:
            win_size += 1
        win_size = str(win_size)

        loadingbar.value = 3
        loadingbar.labelText = 'Noise Estimation...'
        slicer.app.processEvents()
        if check_denoising:
            if mask:
                pipe('dwidenoise -force ' + dir + ' ' + os.path.join(self.tmp,
                                                                     'd.mif' + ' -extent ' + win_size + ' -mask ' + mask),
                     True, self.my_env)
            else:
                pipe('dwidenoise -force ' + dir + ' ' + os.path.join(self.tmp, 'd.mif' + ' -extent ' + win_size), True,
                     self.my_env)
        loadingbar.value = 4
        loadingbar.labelText = 'Gibbs Artifact Removal...'
        slicer.app.processEvents()
        if check_gibbs:
            if check_denoising:
                pipe('mrdegibbs  -force ' + os.path.join(self.tmp, 'd.mif') + ' ' + os.path.join(self.tmp, 'g.mif'),
                     True,
                     self.my_env)
            else:
                pipe('mrdegibbs -force ' + dir + ' ' + os.path.join(self.tmp, 'g.mif'), True, self.my_env)
        loadingbar.value = 5
        loadingbar.labelText = 'Motion and Eddy Currents Correction...'
        slicer.app.processEvents()
        if check_preproc:
            num_cores = str(cpu_count())
            if check_gibbs:
                pipe(
                    'dwipreproc -force -nthreads ' + num_cores + ' -tempdir ' + self.tmp + ' -rpe_none -pe_dir ' + phase_encoding_direction + \
                    os.path.join(self.tmp, 'g.mif') + ' ' + os.path.join(self.tmp, 'p.mif'), True, self.my_env)
            elif check_denoising:
                pipe(
                    'dwipreproc -force -nthreads ' + num_cores + ' -tempdir ' + self.tmp + ' -rpe_none -pe_dir ' + phase_encoding_direction + \
                    os.path.join(self.tmp, 'd.mif') + ' ' + os.path.join(self.tmp, 'p.mif'), True, self.my_env)
            else:
                pipe(
                    'dwipreproc -force -nthreads ' + num_cores + ' -tempdir ' + self.tmp + ' -rpe_none -pe_dir ' + phase_encoding_direction + \
                    dir + ' ' + os.path.join(self.tmp, 'p.mif'), True, self.my_env)

        loadingbar.value = 6
        loadingbar.labelText = 'Bias Field Correction...'
        slicer.app.processEvents()
        if check_preproc:
            pipe(
                'dwibiascorrect -force -ants ' + os.path.join(self.tmp, 'p.mif') + ' ' + os.path.join(self.tmp,
                                                                                                      'r.mif'),
                True, self.my_env)
        elif check_gibbs:
            pipe(
                'dwibiascorrect -force -ants ' + os.path.join(self.tmp, 'g.mif') + ' ' + os.path.join(self.tmp,
                                                                                                      'r.mif'),
                True, self.my_env)
        elif check_denoising:
            pipe(
                'dwibiascorrect -force -ants ' + os.path.join(self.tmp, 'd.mif') + ' ' + os.path.join(self.tmp,
                                                                                                      'r.mif'),
                True, self.my_env)
        else:
            pipe(
                'dwibiascorrect -force -ants ' + dir + ' ' + os.path.join(self.tmp, 'r.mif'),
                True, self.my_env)

        loadingbar.value = 7
        loadingbar.labelText = 'Loading Corrected DWI...'
        slicer.app.processEvents()
        nii_path = os.path.join(self.tmp, 'r.nii')
        bval_path = os.path.join(self.tmp, 'r.bval')
        bvec_path = os.path.join(self.tmp, 'r.bvec')
        pipe('mrconvert -force  -stride -1,2,3,4 ' + os.path.join(self.tmp,
                                                                  'r.mif') + ' ' + nii_path + ' -export_grad_fsl ' + bvec_path + ' ' + bval_path,
             True, self.my_env)

        loadingbar.value = 8
        loadingbar.labelText = ''
        slicer.app.processEvents()

        return nii_path, bval_path, bvec_path

    def register(self, data_path, bvals, bvecs, t2_path, mask_t2, mask_b0):
        b0_path = os.path.join(self.tmp, 'b0.nii')

        with cd(self.tmp):
            pipe('dwiextract -force ' + data_path + ' -bzero ' + b0_path + '  -fslgrad ' + bvecs + ' ' + bvals, True,
                 self.my_env)
            cmd = 'antsRegistration --verbose 1 --dimensionality 3 --float 0 --output \[out,b0Warped.nii,coroT2Warped.nii\] --interpolation Linear --use-histogram-matching 1 --winsorize-image-intensities \[0.005,0.995\] --initial-moving-transform \[' + t2_path + ',' + b0_path + ',1\] --transform Rigid\[0.1\] --metric MI\[' + t2_path + ',' + b0_path + ',1,32,Regular,0.25\] --convergence \[1000x500x250x100,1e-6,10\] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox --transform Affine\[0.1\] --metric MI\[' + t2_path + ',' + b0_path + ',1,32,Regular,0.25\] --convergence \[1000x500x250x100,1e-6,10\] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox --transform SyN\[0.1,3,0\] --metric CC\[' + t2_path + ',' + b0_path + ',1,4\] --convergence \[100x70x50x20,1e-6,10\] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox'
            if mask_t2 and mask_b0:
                cmd += '--masks\[' + mask_t2 + ', ' + mask_b0 + '\]'
            pipe(cmd, True)

            pipe('warpinit -force ' + data_path + ' identity_warp\[\].nii', True, self.my_env)

            pipe(
                'for i in {0..2}; do; WarpImageMultiTransform 3 identity_warp${i}.nii mrtrix_warp${i}.nii -R ' + b0_path + ' out1Warp.nii out0GenericAffine.mat; done;',
                True, self.my_env)

            pipe('warpcorrect -force mrtrix_warp\[\].nii mrtrix_warp_corrected.mif', True, self.my_env)

            pipe('mrtransform -force -stride -1,2,3,4 ' + data_path + ' -warp mrtrix_warp_corrected.mif DWIWarped.nii',
                 True,
                 self.my_env)

        return os.path.join(self.tmp, 'DWIWarped.nii')

    def extract(self, data_path, bvals, bvecs, mask, switch):
        if switch['b0'] is True:
            metric_path = os.path.join(self.tmp, 'b0.nii')
            pipe('dwiextract -force ' + data_path + ' -bzero ' + metric_path + '  -fslgrad ' + bvecs + ' ' + bvals,
                 True, self.my_env)
        if switch['fa'] is True:
            metric_path = os.path.join(self.tmp, 'fa.nii')
            cmd = 'dwi2tensor -force ' + data_path + ' ' + os.path.join(self.tmp,
                                                                        'DTI.mif') + ' -fslgrad ' + bvecs + ' ' + bvals
            if mask:
                cmd += ' -mask ' + mask
            pipe(cmd, True, self.my_env)

            pipe('tensor2metric -force ' + os.path.join(self.tmp, 'DTI.mif') + ' -fa ' + metric_path, True, self.my_env)

        if switch['md'] is True:
            metric_path = os.path.join(self.tmp, 'md.nii')
            cmd = 'dwi2tensor -force ' + data_path + ' ' + os.path.join(self.tmp,
                                                                        'DTI.mif') + ' -fslgrad ' + bvecs + ' ' + bvals
            if mask:
                cmd += ' -mask ' + mask

            pipe(cmd, True, self.my_env)

            pipe('tensor2metric -force ' + os.path.join(self.tmp, 'DTI.mif') + ' -adc ' + metric_path, True,
                 self.my_env)

        return metric_path


class DiffusionPelvisTest(unittest.TestCase):

    def __init__(self):
        pass

    def __repr__(self):
        return 'DiffusionPelvis(). Derived from {}'.format(unittest.TestCase)

    def __str__(self):
        return 'DiffusionPelvis test class'

    def runTest(self, scenario=None):
        pass
