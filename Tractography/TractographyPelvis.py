import os
import qt
import ctk
import vtk
import sys
import json
import shutil
import slicer
import tempfile
import unittest
import numpy as np
from subprocess import call
from joblib import cpu_count
from vtk.util import numpy_support as ns
from functions import *
from functions import filter as ft


__author__ = 'Alessandro Delmonte'
__email__ = 'delmonte.ale92@gmail.com'


def vtkmatrix_to_numpy(matrix):
    m = np.ones((4, 4))
    for i in range(4):
        for j in range(4):
            m[i, j] = matrix.GetElement(i, j)
    return m


def pipe(cmd, verbose=False, my_env=slicer.util.startupEnvironment()):
    if verbose:
        print('Processing command: ' + str(cmd))

    slicer.app.processEvents()

    with open(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'config.json')),
              'r') as handle:
        add_paths = json.load(handle)

    my_env['PATH'] = add_paths['MRTrix_path'] + os.pathsep + my_env['PATH']
    return call(cmd, shell=True, stdin=None, stdout=None, stderr=None,
                executable=os.path.abspath(slicer.util.startupEnvironment()['SHELL']),
                env=my_env)


class TractographyPelvis:
    def __init__(self, parent):
        parent.title = 'Tractography Processing'
        parent.categories = ['IMAG2', 'Diffusion Pelvis']
        parent.dependencies = []
        parent.contributors = ['Alessandro Delmonte (IMAG2)']
        parent.helpText = '''Tools for automatic pelvic tractography seeds extraction and DTI-based pelvic tractography 
        computation.\n Pickle the shell environment before using this module.'''
        parent.acknowledgementText = '''Module developped for 3DSlicer (<a>http://www.slicer.org</a>)\n
		Tractography based on MRTrix3 (<a>http://www.mrtrix.org</a>)'''

        self.parent = parent

        moduleDir = os.path.dirname(self.parent.path)
        iconPath = os.path.join(moduleDir, 'Resources', 'icon.png')
        if os.path.isfile(iconPath):
            parent.icon = qt.QIcon(iconPath)

        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['TractographyPelvis'] = self.runTest

    def __repr__(self):
        return 'TractographyPelvis(parent={})'.format(self.parent)

    def __str__(self):
        return 'TractographyPelvis module initialization class.'

    @staticmethod
    def runTest():
        tester = TractographyPelvisTest()
        tester.runTest()


class TractographyPelvisWidget:
    def __init__(self, parent=None):
        self.moduleName = self.__class__.__name__
        if self.moduleName.endswith('Widget'):
            self.moduleName = self.moduleName[:-6]
        settings = qt.QSettings()
        try:
            self.developerMode = settings.value('Developer/DeveloperMode').lower() == 'true'
        except AttributeError:
            self.developerMode = settings.value('Developer/DeveloperMode') is True

        self.logic = TractographyPelvisLogic()

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
        return 'TractographyPelvisWidget(parent={})'.format(self.parent)

    def __str__(self):
        return 'TractographyPelvis GUI class'

    def setup(self):
        tractoCollapsibleButton = ctk.ctkCollapsibleButton()
        tractoCollapsibleButton.text = 'Tractography'

        self.layout.addWidget(tractoCollapsibleButton)

        tractoFormLayout = qt.QFormLayout(tractoCollapsibleButton)

        self.dwiSelector = slicer.qMRMLNodeComboBox()
        self.dwiSelector.nodeTypes = ['vtkMRMLDiffusionWeightedVolumeNode']
        self.dwiSelector.selectNodeUponCreation = True
        self.dwiSelector.addEnabled = False
        self.dwiSelector.removeEnabled = False
        self.dwiSelector.noneEnabled = False
        self.dwiSelector.showHidden = False
        self.dwiSelector.renameEnabled = False
        self.dwiSelector.showChildNodeTypes = False
        self.dwiSelector.setMRMLScene(slicer.mrmlScene)

        self.dwiNode = self.dwiSelector.currentNode()

        self.dwiSelector.connect('nodeActivated(vtkMRMLNode*)', self.ondwiSelect)
        tractoFormLayout.addRow('Input DWI: ', self.dwiSelector)

        groupbox = qt.QGroupBox()
        groupbox.setTitle('Choose the seed map:')
        groupbox.setContentsMargins(11, 20, 11, 11)
        grid_layout = qt.QGridLayout(groupbox)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setColumnStretch(3, 1)
        grid_layout.setColumnStretch(4, 1)

        textwidget = qt.QLabel()
        textwidget.setText('Input LabelMap: ')

        self.seedsSelector = slicer.qMRMLNodeComboBox()
        self.seedsSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.seedsSelector.selectNodeUponCreation = True
        self.seedsSelector.addEnabled = False
        self.seedsSelector.removeEnabled = False
        self.seedsSelector.noneEnabled = False
        self.seedsSelector.showHidden = False
        self.seedsSelector.renameEnabled = False
        self.seedsSelector.showChildNodeTypes = False
        self.seedsSelector.setMRMLScene(slicer.mrmlScene)

        self.seedsNode = self.seedsSelector.currentNode()

        self.seedsSelector.connect('nodeActivated(vtkMRMLNode*)', self.onseedsSelect)
        # tractoFormLayout.addRow('Input Parcellation: ', self.seedsSelector)

        grid_layout.addWidget(textwidget, 0, 0, 0)
        grid_layout.addWidget(self.seedsSelector, 0, 1, 1, 4)

        self.radio_p = qt.QRadioButton('Standard LabelMap')
        self.radio_p.setChecked(True)
        self.radio_l = qt.QRadioButton('Binary Mask')
        grid_layout.addWidget(self.radio_p, 2, 2, 0)
        grid_layout.addWidget(self.radio_l, 2, 3, 0)

        groupbox.setLayout(grid_layout)

        tractoFormLayout.addRow(groupbox)

        self.tractoSelector = slicer.qMRMLNodeComboBox()
        self.tractoSelector.nodeTypes = ['vtkMRMLFiberBundleNode']
        self.tractoSelector.selectNodeUponCreation = True
        self.tractoSelector.addEnabled = True
        self.tractoSelector.removeEnabled = False
        self.tractoSelector.noneEnabled = False
        self.tractoSelector.showHidden = False
        self.tractoSelector.renameEnabled = True
        self.tractoSelector.showChildNodeTypes = False
        self.tractoSelector.setMRMLScene(slicer.mrmlScene)

        self.tractoNode = self.tractoSelector.currentNode()

        self.tractoSelector.connect('nodeActivated(vtkMRMLNode*)', self.ontractoSelect)
        tractoFormLayout.addRow('Output Fiber Bundle: ', self.tractoSelector)

        self.tractoButton = qt.QPushButton('Compute')
        self.tractoButton.toolTip = 'Run the tractography algorithm.'
        self.tractoButton.enabled = True

        self.tractoButton.connect('clicked(bool)', self.ontractoButton)
        tractoFormLayout.addRow(self.tractoButton)

        line = qt.QFrame()
        line.setFrameShape(qt.QFrame().HLine)
        line.setFrameShadow(qt.QFrame().Sunken)
        line.setStyleSheet("min-height: 24px")
        tractoFormLayout.addRow(line)

        self.maskSelector = slicer.qMRMLNodeComboBox()
        self.maskSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.maskSelector.selectNodeUponCreation = False
        self.maskSelector.addEnabled = False
        self.maskSelector.removeEnabled = False
        self.maskSelector.noneEnabled = True
        self.maskSelector.showHidden = False
        self.maskSelector.renameEnabled = False
        self.maskSelector.showChildNodeTypes = False
        self.maskSelector.setMRMLScene(slicer.mrmlScene)

        self.maskNode = self.maskSelector.currentNode()

        self.maskSelector.connect('nodeActivated(vtkMRMLNode*)', self.onmaskSelect)
        tractoFormLayout.addRow('Whole Pelvis Mask: ', self.maskSelector)

        self.exclusionSelector = slicer.qMRMLNodeComboBox()
        self.exclusionSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.exclusionSelector.selectNodeUponCreation = False
        self.exclusionSelector.addEnabled = False
        self.exclusionSelector.removeEnabled = False
        self.exclusionSelector.noneEnabled = True
        self.exclusionSelector.showHidden = False
        self.exclusionSelector.renameEnabled = False
        self.exclusionSelector.showChildNodeTypes = False
        self.exclusionSelector.setMRMLScene(slicer.mrmlScene)

        self.exclusionNode = self.exclusionSelector.currentNode()

        self.exclusionSelector.connect('nodeActivated(vtkMRMLNode*)', self.onexclusionSelect)
        tractoFormLayout.addRow('Exclusion Mask: ', self.exclusionSelector)

        self.sliderSeeds = ctk.ctkSliderWidget()
        self.sliderSeeds.decimals = 2
        self.sliderSeeds.minimum = 0.
        self.sliderSeeds.maximum = 1.
        self.sliderSeeds.singleStep = 0.01
        self.sliderSeeds.value = 0.15
        self.sliderSeeds.spinBoxVisible = True

        tractoFormLayout.addRow('Seeds Threshold (FA)', self.sliderSeeds)

        self.sliderCutoff = ctk.ctkSliderWidget()
        self.sliderCutoff.decimals = 2
        self.sliderCutoff.minimum = 0.
        self.sliderCutoff.maximum = 1.
        self.sliderCutoff.singleStep = 0.01
        self.sliderCutoff.value = 0.05
        self.sliderCutoff.spinBoxVisible = True

        tractoFormLayout.addRow('Cutoff (FA)', self.sliderCutoff)

        self.sliderMaxangle = ctk.ctkSliderWidget()
        self.sliderMaxangle.decimals = 1
        self.sliderMaxangle.minimum = 1.
        self.sliderMaxangle.maximum = 90.
        self.sliderMaxangle.singleStep = 0.5
        self.sliderMaxangle.value = 45.
        self.sliderMaxangle.spinBoxVisible = True

        tractoFormLayout.addRow('Admissible Angle (\xB0)', self.sliderMaxangle)

        self.sliderLength = ctk.ctkRangeWidget()
        self.sliderLength.setRange(1, 800)
        self.sliderLength.setValues(50, 800)
        tractoFormLayout.addRow('Length (mm)', self.sliderLength)

        self.combo_tract = qt.QComboBox()
        self.combo_tract.insertItem(0, 'DTI - Deterministic - FACT')
        self.combo_tract.insertItem(1, 'CSD - Deterministic - SD_STREAM')
        self.combo_tract.insertItem(2, 'CSD - Probabilistic - iFOD')
        tractoFormLayout.addRow('Algorithm', self.combo_tract)

        line2 = qt.QFrame()
        line2.setFrameShape(qt.QFrame().HLine)
        line2.setFrameShadow(qt.QFrame().Sunken)
        line2.setStyleSheet("min-height: 24px")
        tractoFormLayout.addRow(line2)

        groupbox2 = qt.QGroupBox()
        groupbox2.setTitle('Whole Pelvis Tractogram')
        grid_layout2 = qt.QGridLayout(groupbox2)
        grid_layout2.setColumnStretch(1, 1)
        grid_layout2.setColumnStretch(2, 1)
        grid_layout2.setColumnStretch(3, 1)

        textwidget_info = qt.QLabel()
        textwidget_info.setText(
            'Slicer can not manage large tractogram files. In the situation you desire to compute a whole-pelvis'
            ' tractography,\nplease check the following box and select a tck output file. The result will be saved directly'
            ' on the disk.\n')
        tractoFormLayout.addRow(textwidget_info)

        self.output_file_selector = ctk.ctkPathLineEdit()
        self.output_file_selector.filters = ctk.ctkPathLineEdit.Files | ctk.ctkPathLineEdit.Writable | \
                                            ctk.ctkPathLineEdit.Hidden
        self.output_file_selector.addCurrentPathToHistory()

        textwidget = qt.QLabel()
        textwidget.setText('Use Whole: ')
        grid_layout2.addWidget(textwidget, 0, 0, 0)
        self.radio_whole = qt.QCheckBox()
        self.radio_whole.setChecked(False)
        grid_layout2.addWidget(self.radio_whole, 0, 1, 0)

        textwidget2 = qt.QLabel()
        textwidget2.setText('File Path (.tck): ')
        grid_layout2.addWidget(textwidget2, 1, 0, 0)
        grid_layout2.addWidget(self.output_file_selector, 1, 1, 1, 3)

        groupbox2.setLayout(grid_layout2)
        tractoFormLayout.addRow(groupbox2)

        filtersCollapsibleButton = ctk.ctkCollapsibleButton()
        filtersCollapsibleButton.text = 'Filters'

        self.layout.addWidget(filtersCollapsibleButton)

        filtersFormLayout = qt.QFormLayout(filtersCollapsibleButton)

        self.tractofiltersSelector = slicer.qMRMLNodeComboBox()
        self.tractofiltersSelector.nodeTypes = ['vtkMRMLFiberBundleNode']
        self.tractofiltersSelector.selectNodeUponCreation = True
        self.tractofiltersSelector.addEnabled = False
        self.tractofiltersSelector.removeEnabled = False
        self.tractofiltersSelector.noneEnabled = False
        self.tractofiltersSelector.showHidden = False
        self.tractofiltersSelector.renameEnabled = False
        self.tractofiltersSelector.showChildNodeTypes = False
        self.tractofiltersSelector.setMRMLScene(slicer.mrmlScene)

        self.tractofiltersNode = self.tractofiltersSelector.currentNode()

        self.tractofiltersSelector.connect('nodeActivated(vtkMRMLNode*)', self.ontractofiltersSelect)
        filtersFormLayout.addRow('Input Fiber Bundle: ', self.tractofiltersSelector)

        self.outfiltersSelector = slicer.qMRMLNodeComboBox()
        self.outfiltersSelector.nodeTypes = ['vtkMRMLFiberBundleNode']
        self.outfiltersSelector.selectNodeUponCreation = True
        self.outfiltersSelector.addEnabled = True
        self.outfiltersSelector.removeEnabled = False
        self.outfiltersSelector.noneEnabled = False
        self.outfiltersSelector.showHidden = False
        self.outfiltersSelector.renameEnabled = True
        self.outfiltersSelector.showChildNodeTypes = False
        self.outfiltersSelector.setMRMLScene(slicer.mrmlScene)

        self.outfiltersNode = self.outfiltersSelector.currentNode()

        self.outfiltersSelector.connect('nodeActivated(vtkMRMLNode*)', self.onoutfiltersSelect)
        filtersFormLayout.addRow('Filtered Fiber Bundle: ', self.outfiltersSelector)

        groupbox3 = qt.QGroupBox()
        groupbox3.setStyleSheet("border:none")
        grid_layout3 = qt.QGridLayout(groupbox3)
        grid_layout3.setAlignment(4)
        grid_layout3.setColumnMinimumWidth(0, 150)
        grid_layout3.setColumnMinimumWidth(1, 150)

        self.radio_ap = qt.QRadioButton('Anterior-Posterior')
        self.radio_ap.setChecked(True)
        self.radio_si = qt.QRadioButton('Superior-Inferior')
        self.radio_ml = qt.QRadioButton('Medial-Lateral')
        grid_layout3.addWidget(self.radio_ap, 0, 0, 0)
        grid_layout3.addWidget(self.radio_si, 0, 1, 0)
        grid_layout3.addWidget(self.radio_ml, 0, 2, 0)
        filtersFormLayout.addRow('Principal Direction: ', groupbox3)

        self.compute_filter = qt.QPushButton('Filter')
        self.compute_filter.toolTip = 'Apply the PQL algorithm to the input tractogram.'
        self.compute_filter.enabled = True

        self.compute_filter.connect('clicked(bool)', self.on_compute_filter)
        filtersFormLayout.addRow(self.compute_filter)

        self.layout.addStretch(1)

        if self.developerMode:

            def createHLayout(elements):
                widget = qt.QWidget()
                rowLayout = qt.QHBoxLayout()
                widget.setLayout(rowLayout)
                for element in elements:
                    rowLayout.addWidget(element)
                return widget

            """Developer interface"""
            self.reloadCollapsibleButton = ctk.ctkCollapsibleButton()
            self.reloadCollapsibleButton.text = "Reload && Test"
            self.layout.addWidget(self.reloadCollapsibleButton)
            reloadFormLayout = qt.QFormLayout(self.reloadCollapsibleButton)

            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "ScriptedLoadableModuleTemplate Reload"
            self.reloadButton.connect('clicked()', self.onReload)

            self.reloadAndTestButton = qt.QPushButton("Reload and Test")
            self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
            self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

            self.editSourceButton = qt.QPushButton("Edit")
            self.editSourceButton.toolTip = "Edit the module's source code."
            self.editSourceButton.connect('clicked()', self.onEditSource)

            self.restartButton = qt.QPushButton("Restart Slicer")
            self.restartButton.toolTip = "Restart Slicer"
            self.restartButton.name = "ScriptedLoadableModuleTemplate Restart"
            self.restartButton.connect('clicked()', slicer.app.restart)

            reloadFormLayout.addWidget(
                createHLayout([self.reloadButton, self.reloadAndTestButton, self.editSourceButton, self.restartButton]))

    def ondwiSelect(self):
        self.dwiNode = self.dwiSelector.currentNode()

    def ontractoSelect(self):
        self.tractoNode = self.tractoSelector.currentNode()

    def onseedsSelect(self):
        self.seedsNode = self.seedsSelector.currentNode()

    def onmaskSelect(self):
        self.maskNode = self.maskSelector.currentNode()

    def onexclusionSelect(self):
        self.exclusionNode = self.exclusionSelector.currentNode()

    def ontractofiltersSelect(self):
        self.tractofiltersNode = self.tractofiltersSelector.currentNode()

    def onoutfiltersSelect(self):
        self.outfiltersNode = self.outfiltersSelector.currentNode()

    def ontractoButton(self):
        if self.dwiNode and self.sliderSeeds.value > self.sliderCutoff.value and (
                self.tractoNode or self.radio_whole.isChecked()) and self.seedsNode:
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
            if self.maskNode:
                mask_path = os.path.join(self.logic.tmp, 'mask.nii')
                properties = {}
                properties['useCompression'] = 0
                slicer.util.saveNode(self.maskNode, mask_path, properties)
            else:
                mask_path = None

            seeds_path = os.path.join(self.logic.tmp, 'seeds.nii')
            properties = {}
            properties['useCompression'] = 0
            if (not self.radio_whole.isChecked()) and self.radio_p.isChecked():
                label_list = [n for n in range(15, 28)] + [n for n in range(7, 10)]
                temp_seed_node = slicer.vtkSlicerVolumesLogic().CloneVolume(slicer.mrmlScene, self.seedsNode, 'out',
                                                                            True)
                parc = np.copy(slicer.util.arrayFromVolume(self.seedsNode))
                seed_mask = np.zeros(parc.shape)
                for label in label_list:
                    seed_mask[parc == label] = 1
                slicer.util.updateVolumeFromArray(temp_seed_node, seed_mask)
                slicer.util.saveNode(temp_seed_node, seeds_path, properties)
                slicer.mrmlScene.RemoveNode(temp_seed_node)
            else:
                self.radio_l.setChecked(True)
                slicer.util.saveNode(self.seedsNode, seeds_path, properties)

            if self.exclusionNode:
                excl_path = os.path.join(self.logic.tmp, 'exclusion.nii')
                properties = {}
                properties['useCompression'] = 0
                slicer.util.saveNode(self.exclusionNode, excl_path, properties)
            else:
                excl_path = None

            path = self.logic.tracts(self.sliderLength.minimumValue, self.sliderLength.maximumValue,
                                     self.sliderCutoff.value, self.sliderSeeds.value, self.sliderMaxangle.value,
                                     data_path, mask_path, seeds_path,
                                     excl_path, bvec_path, bval_path, self.combo_tract.currentIndex,
                                     self.radio_whole.isChecked())

            if not self.radio_whole.isChecked():
                tractoname = self.tractoNode.GetName()

                slicer.mrmlScene.RemoveNode(self.tractoNode)

                success, self.upNode = slicer.util.loadFiberBundle(path, True)
                self.upNode.SetName(tractoname)
                self.tractoSelector.setCurrentNode(self.upNode)

                fiber_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLFiberBundleNode')
                fiber_nodes.UnRegister(slicer.mrmlScene)
                fiber_nodes.InitTraversal()
                fiber_node = fiber_nodes.GetNextItemAsObject()
                while fiber_node:
                    if fiber_node is not self.upNode:
                        fiber_node.GetLineDisplayNode().SetVisibility(0)
                        fiber_node.GetTubeDisplayNode().SetVisibility(0)
                        fiber_node.GetGlyphDisplayNode().SetVisibility(0)
                    fiber_node = fiber_nodes.GetNextItemAsObject()
            else:
                self.output_file_selector.addCurrentPathToHistory()
                new_path = self.output_file_selector.currentPath.encode('utf-8')
                shutil.move(path, new_path)

            self.cleanup()

    def on_compute_filter(self):
        if self.tractofiltersNode and self.outfiltersNode:
            properties = {}
            properties['useCompression'] = 0
            tracto_path = os.path.join(self.logic.tmp, 'tracto.vtk')
            slicer.util.saveNode(self.tractofiltersNode, tracto_path, properties)

            outputname = self.outfiltersNode.GetName()

            if self.radio_ml.isChecked():
                dir = 0
            elif self.radio_ap.isChecked():
                dir = 1
            else:
                dir = 2

            path = self.logic.filter(tracto_path, dir)

            slicer.mrmlScene.RemoveNode(self.outfiltersNode)

            success, self.upNode = slicer.util.loadFiberBundle(path, True)
            self.upNode.SetName(outputname)
            self.outfiltersSelector.setCurrentNode(self.upNode)

            fiber_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLFiberBundleNode')
            fiber_nodes.UnRegister(slicer.mrmlScene)
            fiber_nodes.InitTraversal()
            fiber_node = fiber_nodes.GetNextItemAsObject()
            while fiber_node:
                if fiber_node is not self.upNode:
                    fiber_node.GetLineDisplayNode().SetVisibility(0)
                    fiber_node.GetTubeDisplayNode().SetVisibility(0)
                    fiber_node.GetGlyphDisplayNode().SetVisibility(0)
                fiber_node = fiber_nodes.GetNextItemAsObject()

            self.cleanup()

    def onReload(self):

        print('\n' * 2)
        print('-' * 30)
        print('Reloading module: ' + self.moduleName)
        print('-' * 30)
        print('\n' * 2)

        slicer.util.reloadScriptedModule(self.moduleName)

    def onReloadAndTest(self):
        try:
            self.onReload()
            test = slicer.selfTests[self.moduleName]
            test()
        except Exception:
            import traceback
            traceback.print_exc()
            errorMessage = "Reload and Test: Exception!\n\n" + str(e) + "\n\nSee Python Console for Stack Trace"
            slicer.util.errorDisplay(errorMessage)

    def onEditSource(self):
        filePath = slicer.util.modulePath(self.moduleName)
        qt.QDesktopServices.openUrl(qt.QUrl("file:///" + filePath, qt.QUrl.TolerantMode))

    def cleanup(self):
        for filename in os.listdir(self.logic.tmp):
            path = os.path.join(self.logic.tmp, filename)
            try:
                if os.path.isfile(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except:
                pass


class TractographyPelvisLogic:
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
        self.my_env = slicer.util.startupEnvironment()

    def __del__(self):
        shutil.rmtree(self.tmp)

    def __repr__(self):
        return 'TractographyPelvisLogic()'

    def __str__(self):
        return 'TractographyPelvis implementation class'

    def tracts(self, Minlength, Maxlength, Cutoff, Seeds_T, Angle, data_path, Mask, Seeds, ROE, fbvec, fbval, mode,
               is_whole):
        num_cores = str(cpu_count())
        if mode == 0:
            string = 'dwi2tensor -force -nthreads ' + num_cores + ' ' + data_path + ' ' + os.path.join(
                self.tmp, 'DTI.mif') + ' -fslgrad ' + fbvec + ' ' + fbval
            if Mask:
                string = string + ' -mask ' + Mask
            pipe(string, True, self.my_env)

            pipe('tensor2metric -force -nthreads ' + num_cores + ' ' + os.path.join(
                self.tmp, 'DTI.mif') + ' -vec ' + os.path.join(self.tmp, 'eigen.mif'), True, self.my_env)

            if not is_whole:
                string = 'tckgen -force -nthreads ' + num_cores + ' '  + os.path.join(
                    self.tmp, 'eigen.mif') + ' ' + os.path.join(
                    self.tmp, 'tracto.tck') + ' -algorithm FACT -cutoff ' + str(Cutoff) + ' -seed_cutoff ' + str(
                    Seeds_T) + ' -minlength ' + str(Minlength) + ' -maxlength ' + str(
                    Maxlength) + ' -seed_random_per_voxel ' + Seeds + ' 3 ' + ' -angle ' + str(Angle)
            else:
                string = 'tckgen -force -nthreads ' + num_cores + ' '  + os.path.join(
                    self.tmp, 'eigen.mif') + ' ' + os.path.join(
                    self.tmp, 'tracto.tck') + ' -algorithm FACT -cutoff ' + str(Cutoff) + ' -seed_cutoff ' + str(
                    Seeds_T) + ' -minlength ' + str(Minlength) + ' -maxlength ' + str(
                    Maxlength) + ' -seed_image ' + Seeds + ' -angle ' + str(Angle) + ' -select 1M -step 1'
            if Mask:
                string = string + ' -mask ' + Mask
            if ROE:
                string = string + ' -exclude ' + ROE

            pipe(string, True, self.my_env)
        else:
            string = 'dwi2response tournier -nthreads ' + num_cores + ' ' + data_path + ' ' + os.path.join(
                self.tmp, 'response.txt') + ' -fslgrad ' + fbvec + ' ' + fbval
            if Mask:
                string = string + ' -mask ' + Mask
            pipe(string, True, self.my_env)

            string = 'dwi2fod csd -nthreads ' + num_cores + ' ' + data_path + ' ' + os.path.join(
                self.tmp, 'response.txt') + ' ' + os.path.join(self.tmp, 'FOD.mif') + ' -fslgrad ' + fbvec + ' ' + fbval
            if Mask:
                string = string + ' -mask ' + Mask
            pipe(string, True, self.my_env)

            if mode == 1:
                algorithm = 'SD_STREAM'
            else:
                algorithm = 'iFOD2'

            if not is_whole:
                string = 'tckgen -force -nthreads ' + num_cores + ' '  + os.path.join(
                    self.tmp, 'FOD.mif') + ' ' + os.path.join(self.tmp,'tracto.tck') + ' -algorithm ' + algorithm + \
                         ' -cutoff ' + str(Cutoff) + ' -seed_cutoff ' + str(Seeds_T) + ' -minlength ' + str(
                    Minlength) + ' -maxlength ' + str(Maxlength) + ' -seed_random_per_voxel ' + \
                         Seeds + ' 3  -fslgrad ' + fbvec + ' ' + fbval
            else:
                string = 'tckgen -force -nthreads ' + num_cores + ' '  + os.path.join(
                    self.tmp, 'FOD.mif') + ' ' + os.path.join(self.tmp, 'tracto.tck') + ' -algorithm ' + algorithm + \
                         ' -cutoff ' + str(Cutoff) + ' -seed_cutoff ' + str(Seeds_T) + ' -minlength ' + str(
                    Minlength) + ' -maxlength ' + str(Maxlength) + ' -seed_image ' + Seeds +  \
                         '  -fslgrad ' + fbvec + ' ' + fbval + ' -select 1M -step 1'

            if Mask:
                string = string + ' -mask ' + Mask
            if ROE:
                string = string + ' -exclude ' + ROE

            pipe(string, True, self.my_env)

        if not is_whole:
            final_path = tck2vtk(os.path.join(self.tmp, 'tracto.tck'))
        else:
            final_path = os.path.join(self.tmp, 'tracto.tck')

        return final_path

    def filter(self, in_path, dir):
        out_path = os.path.join(self.tmp, 'filter.vtk')
        ft(in_path, out_path, dir)
        return out_path


class TractographyPelvisTest(unittest.TestCase):

    def __init__(self):
        pass

    def __repr__(self):
        return 'TractographyPelvis(). Derived from {}'.format(unittest.TestCase)

    def __str__(self):
        return 'TractographyPelvis test class'

    def runTest(self, scenario=None):
        pass
