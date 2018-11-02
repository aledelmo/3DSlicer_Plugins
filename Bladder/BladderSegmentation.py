import ctk
import os
import qt
import slicer
import string
import unittest
import vtk
from builtins import range
from slicer.ScriptedLoadableModule import *


class BladderSegmentation:

    def __init__(self, parent):
        parent.title = "Bladder"
        parent.categories = ['IMAG2', "Pelvic Segmentation"]
        parent.dependencies = []
        parent.contributors = ["Alessandro Delmonte (IMAG2)"]
        parent.helpText = string.Template(
            'Fast bladder segmentation for T2w image. It requires one initialization point inside of '
            'bladder.').substitute(
            {'a': parent.slicerWikiUrl, 'b': slicer.app.majorVersion, 'c': slicer.app.minorVersion})
        parent.acknowledgementText = ''

        self.parent = parent

        module_dir = os.path.dirname(self.parent.path)
        icon = os.path.join(module_dir, 'Resources', 'icon.png')
        if os.path.isfile(icon):
            parent.icon = qt.QIcon(icon)


class BladderSegmentationWidget:

    def __init__(self, parent=None):
        self.module_name = self.__class__.__name__
        if self.module_name.endswith('Widget'):
            self.module_name = self.module_name[:-6]
        settings = qt.QSettings()
        try:
            self.developerMode = settings.value('Developer/DeveloperMode').lower() == 'true'
        except AttributeError:
            self.developerMode = settings.value('Developer/DeveloperMode') is True
        self.logic = BladderSegmentationLogic()
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

        self.logic = BladderSegmentationLogic()

    def setup(self):

        parameters_collapsible_button = ctk.ctkCollapsibleButton()
        parameters_collapsible_button.text = "Bladder Segmentation"

        self.layout.addWidget(parameters_collapsible_button)

        parameters_form_layout = qt.QFormLayout(parameters_collapsible_button)

        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = False
        self.inputSelector.showHidden = False
        self.inputSelector.showChildNodeTypes = False
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.setToolTip("Pick the input to the algorithm.")
        self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.on_volume_select)
        self.volume_node = self.inputSelector.currentNode()
        parameters_form_layout.addRow("Input MRI Volume: ", self.inputSelector)

        self.markups_selector = slicer.qSlicerSimpleMarkupsWidget()
        self.markups_selector.objectName = 'bladderFiducialsNodeSelector'
        self.markups_selector.setNodeBaseName("OriginSeedsBladder")
        self.markups_selector.defaultNodeColor = qt.QColor(255, 192, 103)
        self.markups_selector.maximumHeight = 150
        self.markups_selector.markupsSelectorComboBox().noneEnabled = False
        parameters_form_layout.addRow("Seeed points:", self.markups_selector)
        self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                            self.markups_selector, 'setMRMLScene(vtkMRMLScene*)')

        self.outputSelector = slicer.qMRMLNodeComboBox()
        self.outputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.outputSelector.selectNodeUponCreation = True
        self.outputSelector.addEnabled = True
        self.outputSelector.removeEnabled = True
        self.outputSelector.noneEnabled = False
        self.outputSelector.showHidden = False
        self.outputSelector.renameEnabled = True
        self.outputSelector.showChildNodeTypes = False
        self.outputSelector.setMRMLScene(slicer.mrmlScene)
        self.outputSelector.setToolTip("Pick the output to the algorithm.")
        self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.on_output_select)
        self.output_node = self.outputSelector.currentNode()
        parameters_form_layout.addRow("Output Segmentation: ", self.outputSelector)

        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Run the algorithm."
        self.applyButton.enabled = True
        self.applyButton.connect('clicked(bool)', self.on_apply_button)
        parameters_form_layout.addRow(self.applyButton)

        self.layout.addStretch(1)

        if self.developerMode:

            def create_hor_layout(elements):
                widget = qt.QWidget()
                row_layout = qt.QHBoxLayout()
                widget.setLayout(row_layout)
                for element in elements:
                    row_layout.addWidget(element)
                return widget

            """Developer interface"""
            reload_collapsible_button = ctk.ctkCollapsibleButton()
            reload_collapsible_button.text = "Reload && Test"
            self.layout.addWidget(reload_collapsible_button)
            reload_form_layout = qt.QFormLayout(reload_collapsible_button)

            reload_button = qt.QPushButton("Reload")
            reload_button.toolTip = "Reload this module."
            reload_button.name = "ScriptedLoadableModuleTemplate Reload"
            reload_button.connect('clicked()', self.on_reload)

            reload_and_test_button = qt.QPushButton("Reload and Test")
            reload_and_test_button.toolTip = "Reload this module and then run the self tests."
            reload_and_test_button.connect('clicked()', self.on_reload_and_test)

            edit_source_button = qt.QPushButton("Edit")
            edit_source_button.toolTip = "Edit the module's source code."
            edit_source_button.connect('clicked()', self.on_edit_source)

            restart_button = qt.QPushButton("Restart Slicer")
            restart_button.toolTip = "Restart Slicer"
            restart_button.name = "ScriptedLoadableModuleTemplate Restart"
            restart_button.connect('clicked()', slicer.app.restart)

            reload_form_layout.addWidget(
                create_hor_layout([reload_button, reload_and_test_button, edit_source_button, restart_button]))

    def on_volume_select(self):
        self.volume_node = self.inputSelector.currentNode()

    def on_output_select(self):
        self.output_node = self.outputSelector.currentNode()

    def on_apply_button(self):
        if self.volume_node and self.output_node and self.markups_selector.currentNode():
            self.logic.run(self.volume_node, self.markups_selector.currentNode(),
                           self.output_node)

    def on_reload(self):
        print('\n' * 2)
        print('-' * 30)
        print('Reloading module: ' + self.module_name)
        print('-' * 30)
        print('\n' * 2)

        slicer.util.reloadScriptedModule(self.module_name)

    def on_reload_and_test(self):
        try:
            self.on_reload()
            test = slicer.selfTests[self.module_name]
            test()
        except Exception:
            import traceback
            traceback.print_exc()
            error_message = "Reload and Test: Exception!\n\n" + str(e) + "\n\nSee Python Console for Stack Trace"
            slicer.util.errorDisplay(error_message)

    def on_edit_source(self):
        fpath = slicer.util.modulePath(self.module_name)
        qt.QDesktopServices.openUrl(qt.QUrl("file:///" + fpath, qt.QUrl.TolerantMode))

    def cleanup(self):
        pass


class BladderSegmentationLogic:
    def __init__(self):
        pass

    @staticmethod
    def run(input_volume, input_point, output_volume):

        blad_params = dict()
        blad_params['inputvolume'] = input_volume.GetID()
        blad_params['point'] = input_point.GetID()
        blad_params["outputMap"] = output_volume.GetID()

        slicer.cli.run(slicer.modules.bladderseg, None, blad_params, wait_for_completion=True)

        display_node = output_volume.GetDisplayNode()
        display_node.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')

        model_params = dict()
        model_params['Name'] = input_volume.GetName() + '_Bladder'
        model_params["InputVolume"] = output_volume.GetID()
        model_params['FilterType'] = "Sinc"

        model_params['Labels'] = 226
        model_params["StartLabel"] = -1
        model_params["EndLabel"] = -1

        model_params['GenerateAll'] = False
        model_params["JointSmoothing"] = False
        model_params["SplitNormals"] = True
        model_params["PointNormals"] = True
        model_params["SkipUnNamed"] = True
        model_params["Decimate"] = 0.25
        model_params["Smooth"] = 10

        n_nodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelHierarchyNode")
        out_hierarchy = None
        for n in range(n_nodes):
            node = slicer.mrmlScene.GetNthNodeByClass(n, "vtkMRMLModelHierarchyNode")
            if node.GetName() == "Bladder Models":
                out_hierarchy = node

        if not out_hierarchy:
            out_hierarchy = slicer.vtkMRMLModelHierarchyNode()
            out_hierarchy.SetScene(slicer.mrmlScene)
            out_hierarchy.SetName("Bladder Models")
            slicer.mrmlScene.AddNode(out_hierarchy)

        model_params["ModelSceneFile"] = out_hierarchy

        slicer.cli.run(slicer.modules.modelmaker, None, model_params)

        slicer.util.showStatusMessage("Model Making Started...", 2000)


class BladderSegmentationTest(unittest.TestCase):

    def __init__(self):
        pass

    def __repr__(self):
        return 'BladderSegmentationTest(). Derived from {}'.format(unittest.TestCase)

    def __str__(self):
        return 'BladderSegmentation test class'

    def run_test(self, scenario=None):
        pass
