import os
import string
import time
import unittest
from builtins import range

try:
    from itertools import izip as zip
except ImportError:
    pass

import RegistrationLib
from __main__ import vtk, qt, ctk, slicer

import MyRegistrationLib


class BonesSegmentation:
    def __init__(self, parent):
        parent.title = "Bones"
        parent.categories = ['IMAG2', "Pelvic Segmentation"]
        parent.dependencies = []
        parent.contributors = ["Alessandro Delmonte, Alessio Virzi' (IMAG2)"]
        parent.helpText = string.Template("""
    This module performs the semiautomatic segmentation of the pelvic bones on T2w MRI.
    """).substitute({'a': parent.slicerWikiUrl, 'b': slicer.app.majorVersion, 'c': slicer.app.minorVersion})
        parent.acknowledgementText = """
    .....
    """  # replace with organization, grant and thanks.

        self.parent = parent

        # IMAG2: Add the corresponding icon to the module
        self.moduleName = self.__class__.__name__
        moduleDir = os.path.dirname(self.parent.path)
        iconPath = os.path.join(moduleDir, 'Resources', 'icon.jpg')
        if os.path.isfile(iconPath):
            parent.icon = qt.QIcon(iconPath)

        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['BonesSegmentation'] = self.runTest

    def runTest(self):
        tester = BonesSegmentationTest()
        tester.runTest()


class BonesSegmentationWidget:
    """The module GUI widget"""

    def __init__(self, parent=None):
        settings = qt.QSettings()
        try:
            self.developerMode = settings.value('Developer/DeveloperMode').lower() == 'true'
        except AttributeError:
            self.developerMode = settings.value('Developer/DeveloperMode') is True
        self.logic = BonesSegmentationLogic()
        self.logic.registationState = self.registationState
        self.sliceNodesByViewName = {}
        self.sliceNodesByVolumeID = {}
        self.observerTags = []
        self.viewNames = ("Fixed", "Moving", "Transformed")
        self.volumeSelectDialog = None
        self.currentRegistrationInterface = None
        self.currentLocalRefinementInterface = None

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

    def setup(self):
        """Instantiate and connect widgets ..."""

        self.selectVolumesButton = qt.QPushButton("Show Pop-Up Selector")
        self.selectVolumesButton.connect('clicked(bool)', self.enter)
        self.layout.addWidget(self.selectVolumesButton)

        #
        # IMAG2: Apply Button (harden transform + image resampling)
        #
        self.applyButton = qt.QPushButton("Segment")
        self.applyButton.toolTip = "Segment!"
        self.applyButton.enabled = True
        self.layout.addWidget(self.applyButton)
        self.applyButton.connect('clicked(bool)', self.onApplyButton)

        self.interfaceFrame = qt.QWidget(self.parent)
        self.interfaceFrame.setLayout(qt.QVBoxLayout())
        self.layout.addWidget(self.interfaceFrame)

        #
        # Parameters Area
        #
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Hips Segmentation"
        self.interfaceFrame.layout().addWidget(parametersCollapsibleButton)
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self.volumeSelectors = {}
        for viewName in self.viewNames:
            self.volumeSelectors[viewName] = slicer.qMRMLNodeComboBox()
            self.volumeSelectors[viewName].nodeTypes = (("vtkMRMLScalarVolumeNode"), "")
            self.volumeSelectors[viewName].selectNodeUponCreation = False
            self.volumeSelectors[viewName].addEnabled = False
            self.volumeSelectors[viewName].removeEnabled = True
            self.volumeSelectors[viewName].noneEnabled = True
            self.volumeSelectors[viewName].showHidden = False
            self.volumeSelectors[viewName].showChildNodeTypes = True
            self.volumeSelectors[viewName].setMRMLScene(slicer.mrmlScene)
            self.volumeSelectors[viewName].setToolTip("Pick the %s volume." % viewName.lower())
            self.volumeSelectors[viewName].enabled = False
            # parametersFormLayout.addRow("%s Volume " % viewName, self.volumeSelectors[viewName])

        self.volumeSelectors["Transformed"].addEnabled = True
        self.volumeSelectors["Transformed"].selectNodeUponCreation = True
        self.volumeSelectors["Transformed"].setToolTip(
            "Pick the transformed volume, which is the target for the registration.")

        self.transformSelector = slicer.qMRMLNodeComboBox()
        self.transformSelector.nodeTypes = (("vtkMRMLTransformNode"), "")
        self.transformSelector.selectNodeUponCreation = True
        self.transformSelector.addEnabled = True
        self.transformSelector.removeEnabled = True
        self.transformSelector.noneEnabled = True
        self.transformSelector.showHidden = False
        self.transformSelector.showChildNodeTypes = False
        self.transformSelector.setMRMLScene(slicer.mrmlScene)
        self.transformSelector.setToolTip("The transform for linear registration")
        self.transformSelector.enabled = False
        # parametersFormLayout.addRow("Target Transform ", self.transformSelector)

        self.visualizationWidget = RegistrationLib.VisualizationWidget(self.logic)
        self.visualizationWidget.connect("layoutRequested(mode,volumesToShow)", self.onLayout)
        parametersFormLayout.addRow(self.visualizationWidget.widget)

        #
        # IMAG2: Landmarks Widget - just the add button changing the RegistrationLib into MyRegistrationLib
        # - manages landmarks
        #
        # self.landmarksWidget = MyRegistrationLib.myLandmarksWidget(self.logic)
        # self.landmarksWidget.connect("landmarkPicked(landmarkName)", self.onLandmarkPicked)
        # self.landmarksWidget.connect("landmarkMoved(landmarkName)", self.onLandmarkMoved)
        # self.landmarksWidget.connect("landmarkEndMoving(landmarkName)", self.onLandmarkEndMoving)
        # parametersFormLayout.addRow(self.landmarksWidget.widget)

        self.landmarksWidget = RegistrationLib.LandmarksWidget(self.logic)
        self.landmarksWidget.connect("landmarkPicked(landmarkName)", self.onLandmarkPicked)
        self.landmarksWidget.connect("landmarkMoved(landmarkName)", self.onLandmarkMoved)
        self.landmarksWidget.connect("landmarkEndMoving(landmarkName)", self.onLandmarkEndMoving)
        parametersFormLayout.addRow(self.landmarksWidget.widget)

        #
        # Registration Options
        #
        self.registrationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.registrationCollapsibleButton.text = "Registration"
        # self.interfaceFrame.layout().addWidget(self.registrationCollapsibleButton)
        registrationFormLayout = qt.QFormLayout(self.registrationCollapsibleButton)

        #
        # registration type selection
        # - allows selection of the active registration type to display
        #
        try:
            slicer.modules.registrationPlugins
        except AttributeError:
            slicer.modules.registrationPlugins = {}

        self.registrationTypeBox = qt.QGroupBox("Registration Type")
        self.registrationTypeBox.setLayout(qt.QFormLayout())
        self.registrationTypeButtons = {}
        self.registrationTypes = slicer.modules.registrationPlugins.keys()
        self.registrationTypes.sort()
        for registrationType in self.registrationTypes:
            plugin = slicer.modules.registrationPlugins[registrationType]
            if plugin.name == "ThinPlate Registration":
                self.onRegistrationType(registrationType)

        # connections
        for selector in self.volumeSelectors.values():
            selector.connect("currentNodeChanged(vtkMRMLNode*)", self.onVolumeNodeSelect)

        # listen to the scene
        self.addObservers()

        # Add vertical spacer
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
            reload_button.connect('clicked()', self.onReload)

            reload_and_test_button = qt.QPushButton("Reload and Test")
            reload_and_test_button.toolTip = "Reload this module and then run the self tests."
            reload_and_test_button.connect('clicked()', self.onReloadAndTest)

            edit_source_button = qt.QPushButton("Edit")
            edit_source_button.toolTip = "Edit the module's source code."
            edit_source_button.connect('clicked()', self.on_edit_source)

            restart_button = qt.QPushButton("Restart Slicer")
            restart_button.toolTip = "Restart Slicer"
            restart_button.name = "ScriptedLoadableModuleTemplate Restart"
            restart_button.connect('clicked()', slicer.app.restart)

            reload_form_layout.addWidget(
                create_hor_layout([reload_button, reload_and_test_button, edit_source_button, restart_button]))

    def onApplyButton(self):
        fix = self.volumeSelectors['Fixed'].currentNode()  # fixed image
        mov = self.volumeSelectors['Moving'].currentNode()  # moving image
        trans = self.volumeSelectors['Transformed'].currentNode()  # transformed image
        transName = "%s-transformed" % mov.GetName()
        try:
            transNode = slicer.util.getNode(transName)
        except slicer.util.MRMLNodeNotFoundException:
            transNode = None
        fixName = fix.GetName()
        fixNode = slicer.util.getNode(fixName)

        slicer.util.showStatusMessage("Processing...", 2000)
        # IMAG2: harden transform
        transLogic = slicer.modules.transforms.logic()
        transLogic.hardenTransform(transNode)

        # IMAG2: resample image
        resample = slicer.modules.brainsresample
        parametersRes = {}
        parametersRes['inputVolume'] = trans.GetID()
        parametersRes['referenceVolume'] = fix.GetID()
        parametersRes['outputVolume'] = trans.GetID()
        parametersRes['pixelType'] = 'uint'
        parametersRes['interpolationMode'] = 'NearestNeighbor'
        slicer.cli.run(resample, None, parametersRes, wait_for_completion=True)

        # IMAG2: reset the correct origins of the images (they were previously changed during the registration procedure)
        fix.SetOrigin(self.FixOrigin)
        trans.SetOrigin(self.FixOrigin)

        # IMAG2: segmentation step (partial - just thresholding)
        SlicerModule = slicer.modules.thresholdscalarvolume
        ModelLogic = SlicerModule.cliModuleLogic()
        CreateLogic = ModelLogic.CreateNode()
        # inputNode=slicer.util.getNode('scanner15ansM')
        inputNode = transNode
        inputNodeMRI = fixNode
        outputNode = slicer.vtkMRMLLabelMapVolumeNode()
        # outputNode.SetName("%s-Bones-label" % inputNode.GetName())
        outputNode.SetName("%s-Bones-label" % fix.GetName())
        outputNode.SetScene(slicer.mrmlScene)
        slicer.mrmlScene.AddNode(outputNode)

        parametersTh = {}
        parametersTh['InputVolume'] = inputNode.GetID()
        parametersTh['OutputVolume'] = outputNode.GetID()
        parametersTh['ThresholdType'] = 'Above'
        parametersTh['ThresholdValue'] = 0.9
        parametersTh['Lower'] = -200
        parametersTh['Upper'] = 200
        parametersTh['OutsideValue'] = 2
        CLINode = None
        CLINode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, parametersTh, wait_for_completion=True)

        bonesParams = {}
        bonesParams['inputvolumeMR'] = inputNodeMRI.GetID()
        bonesParams['inputvolumePRE'] = inputNode.GetID()
        bonesParams['outputvolume'] = outputNode.GetID()
        CLINode_b = None
        CLINode_b = slicer.cli.run(slicer.modules.bonesseg, None, bonesParams, wait_for_completion=True)

        display = outputNode.GetDisplayNode()
        try:
            labelColorTable = slicer.util.getNode('GenericAnatomyColors')
        except slicer.util.MRMLNodeNotFoundException:
            labelColorTable = None
        display.SetAndObserveColorNodeID(labelColorTable.GetID())

        # IMAG2: model maker

        modelParams = {}
        modelParams['Name'] = fix.GetName() + '-Bones'
        modelParams["InputVolume"] = outputNode.GetID()
        modelParams['FilterType'] = "Sinc"
        modelParams['Labels'] = 2
        modelParams["StartLabel"] = -1
        modelParams["EndLabel"] = -1
        modelParams['GenerateAll'] = False
        modelParams["JointSmoothing"] = False
        modelParams["SplitNormals"] = True
        modelParams["PointNormals"] = True
        modelParams["SkipUnNamed"] = True
        modelParams["Decimate"] = 0.25
        modelParams["Smooth"] = 30

        # - make a new hierarchy node if needed
        #
        numNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelHierarchyNode")
        outHierarchy = None
        for n in range(numNodes):
            node = slicer.mrmlScene.GetNthNodeByClass(n, "vtkMRMLModelHierarchyNode")
            if node.GetName() == "Bones Models":
                outHierarchy = node
                break

        if not outHierarchy:
            outHierarchy = slicer.vtkMRMLModelHierarchyNode()
            outHierarchy.SetScene(slicer.mrmlScene)
            outHierarchy.SetName("Bones Models")
            slicer.mrmlScene.AddNode(outHierarchy)

        modelParams["ModelSceneFile"] = outHierarchy
        modelMaker = slicer.modules.modelmaker
        slicer.cli.run(modelMaker, None, modelParams)
        slicer.util.showStatusMessage("3D Model Making Started...", 2000)

        # IMAG2: switch to the four up view
        LayoutWidget = slicer.qMRMLLayoutWidget()
        LayoutWidget.setMRMLScene(slicer.mrmlScene)
        LayoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        # IMAG2: center 3D View
        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()
        # IMAG2: assign background and label volumes
        red_logic = layoutManager.sliceWidget("Red").sliceLogic()
        red_cn = red_logic.GetSliceCompositeNode()
        red_cn.SetBackgroundVolumeID(fix.GetID())
        red_cn.SetLabelVolumeID(outputNode.GetID())
        red_cn.SetLabelOpacity(0.8)

        green_logic = layoutManager.sliceWidget("Green").sliceLogic()
        green_cn = green_logic.GetSliceCompositeNode()
        green_cn.SetBackgroundVolumeID(fix.GetID())
        green_cn.SetLabelVolumeID(outputNode.GetID())
        green_cn.SetLabelOpacity(0.8)

        yellow_logic = layoutManager.sliceWidget("Yellow").sliceLogic()
        yellow_cn = yellow_logic.GetSliceCompositeNode()
        yellow_cn.SetBackgroundVolumeID(fix.GetID())
        yellow_cn.SetLabelVolumeID(outputNode.GetID())
        yellow_cn.SetLabelOpacity(0.8)

        # IMAG2: center slice views
        red_logic.FitSliceToAll()
        green_logic.FitSliceToAll()
        yellow_logic.FitSliceToAll()

        mark_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLMarkupsFiducialNode')
        mark_nodes.UnRegister(slicer.mrmlScene)
        mark_nodes.InitTraversal()
        mark_node = mark_nodes.GetNextItemAsObject()
        while mark_node:
            if mov.GetName() in mark_node.GetName() or fix.GetName() in mark_node.GetName() or mark_node == 'F':
                slicer.mrmlScene.RemoveNode(mark_node)
            mark_node = mark_nodes.GetNextItemAsObject()

        vol_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
        vol_nodes.UnRegister(slicer.mrmlScene)
        vol_nodes.InitTraversal()
        vol_node = vol_nodes.GetNextItemAsObject()
        while vol_node:
            if mov.GetName() in vol_node.GetName():
                slicer.mrmlScene.RemoveNode(vol_node)
            vol_node = vol_nodes.GetNextItemAsObject()

    def enter(self):
        self.interfaceFrame.enabled = False
        self.setupDialog()

    def setupDialog(self):
        """setup dialog"""

        if not self.volumeSelectDialog:
            self.volumeSelectDialog = qt.QDialog(slicer.util.mainWindow())
            self.volumeSelectDialog.objectName = 'BonesSegmentationVolumeSelect'
            self.volumeSelectDialog.setLayout(qt.QVBoxLayout())

            self.volumeSelectLabel = qt.QLabel()
            self.volumeSelectDialog.layout().addWidget(self.volumeSelectLabel)

            self.volumeSelectorFrame = qt.QFrame()
            self.volumeSelectorFrame.objectName = 'VolumeSelectorFrame'
            self.volumeSelectorFrame.setLayout(qt.QFormLayout())
            self.volumeSelectDialog.layout().addWidget(self.volumeSelectorFrame)

            self.volumeDialogSelectors = {}

            #      #IMAG2:
            self.volumeDialogSelectors['Fixed'] = slicer.qMRMLNodeComboBox()
            self.volumeDialogSelectors['Fixed'].nodeTypes = (("vtkMRMLScalarVolumeNode"), "")
            self.volumeDialogSelectors['Fixed'].selectNodeUponCreation = False
            self.volumeDialogSelectors['Fixed'].addEnabled = False
            self.volumeDialogSelectors['Fixed'].removeEnabled = True
            self.volumeDialogSelectors['Fixed'].noneEnabled = True
            self.volumeDialogSelectors['Fixed'].showHidden = False
            self.volumeDialogSelectors['Fixed'].showChildNodeTypes = True
            self.volumeDialogSelectors['Fixed'].setMRMLScene(slicer.mrmlScene)
            self.volumeDialogSelectors['Fixed'].setToolTip("Pick the MRI volume of the patient.")
            self.volumeSelectorFrame.layout().addRow("Patient MRI", self.volumeDialogSelectors['Fixed'])

            self.volumeButtonFrame = qt.QFrame()
            self.volumeButtonFrame.objectName = 'VolumeButtonFrame'
            self.volumeButtonFrame.setLayout(qt.QHBoxLayout())
            self.volumeSelectDialog.layout().addWidget(self.volumeButtonFrame)

            # IMAG2: buttons for the age and the sex selection
            # Define the sex button
            self.SexButton = qt.QComboBox()
            self.SexButton.addItem('Male')
            self.SexButton.addItem('Female')
            self.volumeSelectorFrame.layout().addRow("Sex", self.SexButton)
            # Define the age button
            self.AgeButton = qt.QSpinBox()
            self.AgeButton.setRange(0, 20)
            self.volumeSelectorFrame.layout().addRow("Age", self.AgeButton)

            self.volumeDialogApply = qt.QPushButton("Apply", self.volumeButtonFrame)
            self.volumeDialogApply.objectName = 'VolumeDialogApply'
            self.volumeDialogApply.setToolTip("Use currently selected volume nodes.")
            self.volumeButtonFrame.layout().addWidget(self.volumeDialogApply)

            self.volumeDialogCancel = qt.QPushButton("Cancel", self.volumeButtonFrame)
            self.volumeDialogCancel.objectName = 'VolumeDialogCancel'
            self.volumeDialogCancel.setToolTip("Cancel current operation.")
            self.volumeButtonFrame.layout().addWidget(self.volumeDialogCancel)

            self.volumeDialogApply.connect("clicked()", self.onVolumeDialogApply)
            self.volumeDialogCancel.connect("clicked()", self.volumeSelectDialog.hide)

        self.volumeSelectLabel.setText("Insert the patient information")
        self.volumeSelectDialog.show()

    def onVolumeDialogApply(self):
        self.volumeSelectDialog.hide()
        sexLabel = self.SexButton.currentIndex
        #    ageLabel=self.AgeButton.currentIndex
        ageLabel = self.AgeButton.value
        moduleName = 'BonesSegmentation'
        filePath = eval('slicer.modules.%s.path' % moduleName.lower())
        ModuleDir = os.path.dirname(filePath)
        # Loading of the correct Template Volume
        if sexLabel == 0:  # Male patient
            if 0 <= ageLabel <= 1:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'M_M7.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'M_M7' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 1 < ageLabel <= 3:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'M_Y2.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'M_Y2' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 3 < ageLabel <= 8:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'M_Y4.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'M_Y4' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 8 < ageLabel <= 15:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'M_Y9.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'M_Y9' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            else:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'M_Y15.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'M_Y15' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
        else:  # Female patient
            if 0 <= ageLabel <= 1:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'F_M7.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'F_M7' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 1 < ageLabel <= 3:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'F_Y2.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'F_Y2' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 3 < ageLabel <= 8:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'F_Y4.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'F_Y4' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            elif 8 < ageLabel <= 13:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'F_Y9.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'F_Y9' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
            else:
                VolumePath = os.path.join(ModuleDir, 'Templates', 'F_Y15.nrrd')
                slicer.util.loadVolume(VolumePath)
                volume_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')
                volume_nodes.UnRegister(slicer.mrmlScene)
                volume_nodes.InitTraversal()
                volume_node = volume_nodes.GetNextItemAsObject()
                while volume_node:
                    if 'F_Y15' in volume_node.GetName():
                        VolumeNode = volume_node
                        break
                    volume_node = volume_nodes.GetNextItemAsObject()
                #
        #
        #
        fixedID = self.volumeDialogSelectors['Fixed'].currentNodeID
        # movingID = self.volumeDialogSelectors['Moving'].currentNodeID
        movingID = VolumeNode.GetID()
        if fixedID and movingID:
            self.volumeSelectors['Fixed'].setCurrentNodeID(fixedID)
            self.volumeSelectors['Moving'].setCurrentNodeID(movingID)
            fix = self.volumeSelectors['Fixed'].currentNode()
            self.FixOrigin = fix.GetOrigin()  # extraction of the origin of the original MRI
            mov = self.volumeSelectors['Moving'].currentNode()

            # IMAG2: center fixed and moving volumes
            VolumesLogic = slicer.modules.volumes.logic()
            try:
                temp = slicer.util.getNode(fix.GetName())
            except slicer.util.MRMLNodeNotFoundException:
                temp = None
            VolumesLogic.CenterVolume(temp)
            try:
                temp = slicer.util.getNode(mov.GetName())
            except slicer.util.MRMLNodeNotFoundException:
                temp = None
            VolumesLogic.CenterVolume(temp)
            # create transform and transformed if needed
            transform = self.transformSelector.currentNode()
            if not transform:
                self.transformSelector.addNode()
                transform = self.transformSelector.currentNode()
            transformed = self.volumeSelectors['Transformed'].currentNode()
            if not transformed:
                volumesLogic = slicer.modules.volumes.logic()
                moving = self.volumeSelectors['Moving'].currentNode()
                transformedName = "%s-transformed" % moving.GetName()
                try:
                    transformed = slicer.util.getNode(transformedName)
                except slicer.util.MRMLNodeNotFoundException:
                    transformed = None
                if not transformed:
                    transformed = volumesLogic.CloneVolume(slicer.mrmlScene, moving, transformedName)
                transformed.SetAndObserveTransformNodeID(transform.GetID())
            self.volumeSelectors['Transformed'].setCurrentNode(transformed)
            self.onLayout()
            self.interfaceFrame.enabled = True

        # IMAG2: Set red lookup table and change contrast of the transformed image
        displayNode = transformed.GetDisplayNode()
        displayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeRed')
        displayNode.AutoWindowLevelOff()
        # displayNode.SetThreshold(1,1)
        displayNode.SetWindowLevel(0.2, 1)

    def cleanup(self):
        self.removeObservers()
        self.landmarksWidget.removeLandmarkObservers()

    def addObservers(self):
        """Observe the mrml scene for changes that we wish to respond to.
        scene observer:
         - whenever a new node is added, check if it was a new fiducial.
           if so, transform it into a landmark by creating a matching
           fiducial for other volumes
        fiducial obserers:
         - when fiducials are manipulated, perform (or schedule) an update
           to the currently active registration method.
        """
        tag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.landmarksWidget.requestNodeAddedUpdate)
        self.observerTags.append((slicer.mrmlScene, tag))
        tag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeRemovedEvent,
                                           self.landmarksWidget.requestNodeAddedUpdate)
        self.observerTags.append((slicer.mrmlScene, tag))

    def removeObservers(self):
        """Remove observers and any other cleanup needed to
        disconnect from the scene"""
        for obj, tag in self.observerTags:
            obj.RemoveObserver(tag)
        self.observerTags = []

    def registationState(self):
        """Return an instance of RegistrationState populated
        with current gui parameters"""
        state = RegistrationLib.RegistrationState()
        state.logic = self.logic
        state.fixed = self.volumeSelectors["Fixed"].currentNode()
        state.moving = self.volumeSelectors["Moving"].currentNode()
        state.transformed = self.volumeSelectors["Transformed"].currentNode()
        state.fixedFiducials = self.logic.volumeFiducialList(state.fixed)
        state.movingFiducials = self.logic.volumeFiducialList(state.moving)
        state.transformedFiducials = self.logic.volumeFiducialList(state.transformed)
        state.transform = self.transformSelector.currentNode()
        state.currentLandmarkName = self.landmarksWidget.selectedLandmark

        return (state)

    def currentVolumeNodes(self):
        """List of currently selected volume nodes"""
        volumeNodes = []
        for selector in self.volumeSelectors.values():
            volumeNode = selector.currentNode()
            if volumeNode:
                volumeNodes.append(volumeNode)
        return (volumeNodes)

    def onVolumeNodeSelect(self):
        """When one of the volume selectors is changed"""
        volumeNodes = self.currentVolumeNodes()
        self.landmarksWidget.setVolumeNodes(volumeNodes)
        fixed = self.volumeSelectors['Fixed'].currentNode()
        moving = self.volumeSelectors['Moving'].currentNode()
        transformed = self.volumeSelectors['Transformed'].currentNode()
        self.registrationCollapsibleButton.enabled = bool(fixed and moving)
        self.logic.hiddenFiducialVolumes = (transformed,)

    def onLayout(self, layoutMode="Axi/Sag/Cor", volumesToShow=None):
        """When the layout is changed by the VisualizationWidget
        volumesToShow: list of the volumes to include, None means include all
        """
        volumeNodes = []
        activeViewNames = []
        for viewName in self.viewNames:
            volumeNode = self.volumeSelectors[viewName].currentNode()
            if volumeNode and not (volumesToShow and viewName not in volumesToShow):
                volumeNodes.append(volumeNode)
                activeViewNames.append(viewName)
        import CompareVolumes
        compareLogic = CompareVolumes.CompareVolumesLogic()
        oneViewModes = ('Axial', 'Sagittal', 'Coronal',)
        if layoutMode in oneViewModes:
            self.sliceNodesByViewName = compareLogic.viewerPerVolume(volumeNodes, viewNames=activeViewNames,
                                                                     orientation=layoutMode)
        elif layoutMode == 'Axi/Sag/Cor':
            self.sliceNodesByViewName = compareLogic.viewersPerVolume(volumeNodes)
        self.overlayFixedOnTransformed()
        self.updateSliceNodesByVolumeID()
        self.onLandmarkPicked(self.landmarksWidget.selectedLandmark)

    def overlayFixedOnTransformed(self):
        """If there are viewers showing the transformed volume
        in the background, make the foreground volume be the fixed volume
        and set opacity to 0.5"""
        fixedNode = self.volumeSelectors['Fixed'].currentNode()
        transformedNode = self.volumeSelectors['Transformed'].currentNode()
        if transformedNode:
            compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
            for compositeNode in compositeNodes.values():
                if compositeNode.GetBackgroundVolumeID() == transformedNode.GetID():
                    compositeNode.SetForegroundVolumeID(fixedNode.GetID())
                    compositeNode.SetForegroundOpacity(0.5)

    def onRegistrationType(self, pickedRegistrationType):
        """Pick which registration type to display"""
        if self.currentRegistrationInterface:
            self.currentRegistrationInterface.destroy()
        interfaceClass = slicer.modules.registrationPlugins[pickedRegistrationType]
        self.currentRegistrationInterface = interfaceClass(self.registrationCollapsibleButton)
        # argument registationState is a callable that gets current state
        self.currentRegistrationInterface.create(self.registationState)
        self.currentRegistrationInterface.onLandmarkEndMoving(self.registationState)

    def onLocalRefinementMethod(self, pickedLocalRefinementMethod):
        """Pick which local refinement method to display"""
        if self.currentLocalRefinementInterface:
            self.currentLocalRefinementInterface.destroy()
        interfaceClass = slicer.modules.registrationPlugins[pickedLocalRefinementMethod]
        self.currentLocalRefinementInterface = interfaceClass(self.localRefinementCollapsibleButton)
        # argument registrationState is a callable that gets current state, current same instance is shared for registration and local refinement
        self.currentLocalRefinementInterface.create(self.registationState)

    def updateSliceNodesByVolumeID(self):
        """Build a mapping to a list of slice nodes
        node that are currently displaying a given volumeID"""
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        self.sliceNodesByVolumeID = {}
        if self.sliceNodesByViewName:
            for sliceNode in self.sliceNodesByViewName.values():
                for compositeNode in compositeNodes.values():
                    if compositeNode.GetLayoutName() == sliceNode.GetLayoutName():
                        volumeID = compositeNode.GetBackgroundVolumeID()
                        if self.sliceNodesByVolumeID.has_key(volumeID):
                            self.sliceNodesByVolumeID[volumeID].append(sliceNode)
                        else:
                            self.sliceNodesByVolumeID[volumeID] = [sliceNode, ]

    def restrictLandmarksToViews(self):
        """Set fiducials so they only show up in the view
        for the volume on which they were defined.
        Also turn off other fiducial lists, since leaving
        them visible can interfere with picking."""
        volumeNodes = self.currentVolumeNodes()
        if self.sliceNodesByViewName:
            landmarks = self.logic.landmarksForVolumes(volumeNodes)
            activeFiducialLists = []
            for landmarkName in landmarks:
                for fiducialList, index in landmarks[landmarkName]:
                    activeFiducialLists.append(fiducialList)
                    displayNode = fiducialList.GetDisplayNode()
                    displayNode.RemoveAllViewNodeIDs()
                    volumeNodeID = fiducialList.GetAttribute("AssociatedNodeID")
                    if volumeNodeID:
                        if self.sliceNodesByVolumeID.has_key(volumeNodeID):
                            for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
                                displayNode.AddViewNodeID(sliceNode.GetID())
                                for hiddenVolume in self.logic.hiddenFiducialVolumes:
                                    if hiddenVolume and volumeNodeID == hiddenVolume.GetID():
                                        displayNode.SetVisibility(False)
            allFiducialLists = slicer.util.getNodes('vtkMRMLMarkupsFiducialNode').values()
            for fiducialList in allFiducialLists:
                if fiducialList not in activeFiducialLists:
                    displayNode = fiducialList.GetDisplayNode()
                    if displayNode:
                        displayNode.SetVisibility(False)
                        displayNode.RemoveAllViewNodeIDs()
                        displayNode.AddViewNodeID("__invalid_view_id__")

    def onLocalRefineClicked(self):
        """Refine the selected landmark"""
        timing = True
        slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

        if self.landmarksWidget.selectedLandmark != None:
            if self.currentLocalRefinementInterface:
                state = self.registationState()
                self.currentLocalRefinementInterface.refineLandmark(state)
            if timing: onLandmarkPickedStart = time.time()
            self.onLandmarkPicked(self.landmarksWidget.selectedLandmark)
            if timing: onLandmarkPickedEnd = time.time()
            if timing: print('Time to update visualization ' + str(
                onLandmarkPickedEnd - onLandmarkPickedStart) + ' seconds')

        slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

    def onLandmarkPicked(self, landmarkName):
        """Jump all slice views such that the selected landmark
        is visible"""
        if not self.landmarksWidget.movingView:
            # only change the fiducials if they are not being manipulated
            self.restrictLandmarksToViews()
        self.updateSliceNodesByVolumeID()
        volumeNodes = self.currentVolumeNodes()
        landmarksByName = self.logic.landmarksForVolumes(volumeNodes)
        if landmarksByName.has_key(landmarkName):
            for fiducialList, index in landmarksByName[landmarkName]:
                volumeNodeID = fiducialList.GetAttribute("AssociatedNodeID")
                if self.sliceNodesByVolumeID.has_key(volumeNodeID):
                    point = [0, ] * 3
                    fiducialList.GetNthFiducialPosition(index, point)
                    for sliceNode in self.sliceNodesByVolumeID[volumeNodeID]:
                        if sliceNode.GetLayoutName() != self.landmarksWidget.movingView:
                            sliceNode.JumpSliceByCentering(*point)

    # if landmarkName != None :
    #  self.localRefineButton.text = 'Refine landmark ' + landmarkName
    # else:
    #  self.localRefineButton.text = 'No landmark selected for refinement'

    def onLandmarkMoved(self, landmarkName):
        """Called when a landmark is moved (probably through
        manipulation of the widget in the slice view).
        This updates the active registration"""
        if self.currentRegistrationInterface:
            state = self.registationState()
            self.currentRegistrationInterface.onLandmarkMoved(state)

    def onLandmarkEndMoving(self, landmarkName):
        """Called when a landmark is done being moved (e.g. when mouse button released)"""
        if self.currentRegistrationInterface:
            state = self.registationState()
            self.currentRegistrationInterface.onLandmarkEndMoving(state)

    def onReload(self, moduleName="BonesSegmentation"):
        """Generic reload method for any scripted module.
        ModuleWizard will subsitute correct default moduleName.
        Note: customized for use in BonesSegmentation
        """
        import imp, sys, os, slicer

        # first, destroy the current plugin, since it will
        # contain subclasses of the RegistrationLib modules
        if self.currentRegistrationInterface:
            self.currentRegistrationInterface.destroy()
        if self.currentLocalRefinementInterface:
            self.currentLocalRefinementInterface.destroy()

        # now reload the RegistrationLib source code
        # - set source file path
        # - load the module to the global space
        filePath = eval('slicer.modules.%s.path' % moduleName.lower())
        p = os.path.dirname(filePath)
        if not sys.path.__contains__(p):
            sys.path.insert(0, p)
        for subModuleName in ("pqWidget", "Visualization", "Landmarks",):
            fp = open(filePath, "r")
            globals()[subModuleName] = imp.load_module(
                subModuleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
            fp.close()

        # now reload all the support code and have the plugins
        # re-register themselves with slicer
        oldPlugins = slicer.modules.registrationPlugins
        slicer.modules.registrationPlugins = {}
        for plugin in oldPlugins.values():
            pluginModuleName = plugin.__module__.lower()
            if hasattr(slicer.modules, pluginModuleName):
                # for a plugin from an extension, need to get the source path
                # from the module
                module = getattr(slicer.modules, pluginModuleName)
                sourceFile = module.path
            else:
                # for a plugin built with slicer itself, the file path comes
                # from the pyc path noted as __file__ at startup time
                sourceFile = plugin.sourceFile.replace('.pyc', '.py')
            imp.load_source(plugin.__module__, sourceFile)
        oldPlugins = None

        widgetName = moduleName + "Widget"

        # now reload the widget module source code
        # - set source file path
        # - load the module to the global space
        filePath = eval('slicer.modules.%s.path' % moduleName.lower())
        p = os.path.dirname(filePath)
        if not sys.path.__contains__(p):
            sys.path.insert(0, p)
        fp = open(filePath, "r")
        globals()[moduleName] = imp.load_module(
            moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
        fp.close()

        # rebuild the widget
        # - find and hide the existing widget
        # - create a new widget in the existing parent
        parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
        for child in parent.children():
            try:
                child.hide()
            except AttributeError:
                pass
        # Remove spacer items
        item = parent.layout().itemAt(0)
        while item:
            parent.layout().removeItem(item)
            item = parent.layout().itemAt(0)

        # delete the old widget instance
        if hasattr(globals()['slicer'].modules, widgetName):
            getattr(globals()['slicer'].modules, widgetName).cleanup()

        # create new widget inside existing parent
        globals()[widgetName.lower()] = eval(
            'globals()["%s"].%s(parent)' % (moduleName, widgetName))
        globals()[widgetName.lower()].setup()
        setattr(globals()['slicer'].modules, widgetName, globals()[widgetName.lower()])

    def onReloadAndTest(self, moduleName="BonesSegmentation", scenario=None):
        try:
            self.onReload()
            evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
            tester = eval(evalString)
            tester.runTest(scenario=scenario)
        except Exception:
            import traceback
            traceback.print_exc()
            qt.QMessageBox.warning(slicer.util.mainWindow(),
                                   "Reload and Test",
                                   'Exception!\n\n'  + "\n\nSee Python Console for Stack Trace")

    def on_edit_source(self):
        fpath = slicer.util.modulePath(self.module_name)
        qt.QDesktopServices.openUrl(qt.QUrl("file:///" + fpath, qt.QUrl.TolerantMode))


#
# LandmarkRegistrationLogic
#

class BonesSegmentationLogic:
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget

    The representation of Landmarks is in terms of matching FiducialLists
    with one list per VolumeNode.

    volume1 <-- associated node -- FiducialList1
                                   - anatomy 1
                                   - anatomy 2
                                   ...
    volume2 <-- associated node -- FiducialList2
                                   - anatomy 1
                                   - anatomy 2
                                   ...

    The Fiducial List is only made visible in the viewer that
    has the associated node in the bg.

    Set of identically named fiducials in lists associated with the
    current moving and fixed volumes define a 'landmark'.

    Note that it is the name, not the index, of the anatomy that defines
    membership in a landmark.  Use a pair (fiducialListNodes,index) to
    identify a fiducial.
    """

    def __init__(self):
        self.linearMode = 'Rigid'
        self.hiddenFiducialVolumes = ()
        self.cropLogic = None
        if hasattr(slicer.modules, 'cropvolume'):
            self.cropLogic = slicer.modules.cropvolume.logic()

    def setFiducialListDisplay(self, fiducialList):
        displayNode = fiducialList.GetDisplayNode()
        # TODO: pick appropriate defaults
        # 135,135,84
        displayNode.SetTextScale(6.)
        displayNode.SetGlyphScale(6.)
        displayNode.SetGlyphTypeFromString('Sphere3D')
        displayNode.SetColor((1, 0, 0))  # ((1,1,0.4))
        displayNode.SetSelectedColor((1, 0, 0))  # ((1,1,0))
        # displayNode.GetAnnotationTextDisplayNode().SetColor((1,1,0))
        displayNode.SetVisibility(True)

    def addFiducial(self, name, position=(0, 0, 0), associatedNode=None):
        """Add an instance of a fiducial to the scene for a given
        volume node.  Creates a new list if needed.
        If list already has a fiducial with the given name, then
        set the position to the passed value.
        """

        markupsLogic = slicer.modules.markups.logic()
        originalActiveListID = markupsLogic.GetActiveListID()  # TODO: naming convention?
        slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

        # make the fiducial list if required
        listName = associatedNode.GetName() + "-landmarks"
        try:
            fiducialList = slicer.util.getNode(listName)
        except slicer.util.MRMLNodeNotFoundException:
            fiducialList = None
        if not fiducialList:
            fiducialListNodeID = markupsLogic.AddNewFiducialNode(listName, slicer.mrmlScene)
            try:
                fiducialList = slicer.util.getNode(fiducialListNodeID)
            except slicer.util.MRMLNodeNotFoundException:
                fiducialList = None
            if associatedNode:
                fiducialList.SetAttribute("AssociatedNodeID", associatedNode.GetID())
            self.setFiducialListDisplay(fiducialList)

        # make this active so that the fids will be added to it
        markupsLogic.SetActiveListID(fiducialList)

        foundLandmarkFiducial = False
        fiducialSize = fiducialList.GetNumberOfFiducials()
        for fiducialIndex in range(fiducialSize):
            if fiducialList.GetNthFiducialLabel(fiducialIndex) == name:
                fiducialList.SetNthFiducialPosition(fiducialIndex, *position)
                foundLandmarkFiducial = True
                break

        if not foundLandmarkFiducial:
            if associatedNode:
                # clip point to min/max bounds of target volume
                rasBounds = [0, ] * 6
                associatedNode.GetRASBounds(rasBounds)
                for i in range(3):
                    if position[i] < rasBounds[2 * i]:
                        position[i] = rasBounds[2 * i]
                    if position[i] > rasBounds[2 * i + 1]:
                        position[i] = rasBounds[2 * i + 1]
            fiducialList.AddFiducial(*position)
            fiducialIndex = fiducialList.GetNumberOfFiducials() - 1

        fiducialList.SetNthFiducialLabel(fiducialIndex, name)
        fiducialList.SetNthFiducialSelected(fiducialIndex, False)
        fiducialList.SetNthMarkupLocked(fiducialIndex, False)

        try:
            originalActiveList = slicer.util.getNode(originalActiveListID)
        except slicer.util.MRMLNodeNotFoundException:
            originalActiveList = None
        if originalActiveList:
            markupsLogic.SetActiveListID(originalActiveList)
        slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

    def addLandmark(self, volumeNodes=[], position=(0, 0, 0), movingPosition=(0, 0, 0)):
        """Add a new landmark by adding correspondingly named
        fiducials to all the current volume nodes.
        Find a unique name for the landmark and place it at the origin.
        As a special case if the fiducial list corresponds to the
        moving volume in the current state, then assign the movingPosition
        (this way it can account for the current transform).
        """
        state = self.registationState()
        landmarks = self.landmarksForVolumes(volumeNodes)
        index = 0
        while True:
            landmarkName = 'L-%d' % index
            if not landmarkName in landmarks.keys():
                break
            index += 1
        for volumeNode in volumeNodes:
            # if the volume is the moving on, map position through transform to world
            if volumeNode == state.moving:
                positionToAdd = movingPosition
            else:
                positionToAdd = position
            fiducial = self.addFiducial(landmarkName, position=positionToAdd, associatedNode=volumeNode)
        return landmarkName

    def removeLandmarkForVolumes(self, landmark, volumeNodes):
        """Remove the fiducial nodes from all the volumes.
        """
        slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)
        landmarks = self.landmarksForVolumes(volumeNodes)
        if landmarks.has_key(landmark):
            for fiducialList, fiducialIndex in landmarks[landmark]:
                fiducialList.RemoveMarkup(fiducialIndex)
        slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

    def volumeFiducialList(self, volumeNode):
        """return fiducial list node that is
        list associated with the given volume node"""
        if not volumeNode:
            return None
        listName = volumeNode.GetName() + "-landmarks"
        try:
            listNode = slicer.util.getNode(listName)
        except slicer.util.MRMLNodeNotFoundException:
            listNode = None
        if listNode:
            if listNode.GetAttribute("AssociatedNodeID") != volumeNode.GetID():
                self.setFiducialListDisplay(listNode)
                listNode.SetAttribute("AssociatedNodeID", volumeNode.GetID())
        return listNode

    def landmarksForVolumes(self, volumeNodes):
        """Return a dictionary of keyed by
        landmark name containing pairs (fiducialListNodes,index)
        Only fiducials that exist for all volumes are returned."""
        landmarksByName = {}
        for volumeNode in volumeNodes:
            listForVolume = self.volumeFiducialList(volumeNode)
            if listForVolume:
                fiducialSize = listForVolume.GetNumberOfMarkups()
                for fiducialIndex in range(fiducialSize):
                    fiducialName = listForVolume.GetNthFiducialLabel(fiducialIndex)
                    if landmarksByName.has_key(fiducialName):
                        landmarksByName[fiducialName].append((listForVolume, fiducialIndex))
                    else:
                        landmarksByName[fiducialName] = [(listForVolume, fiducialIndex), ]
        for fiducialName in landmarksByName.keys():
            if len(landmarksByName[fiducialName]) != len(volumeNodes):
                landmarksByName.__delitem__(fiducialName)
        return landmarksByName

    def ensureFiducialInListForVolume(self, volumeNode, landmarkName, landmarkPosition):
        """Make sure the fiducial list associated with the given
        volume node contains a fiducial named landmarkName and that it
        is associated with volumeNode.  If it does not have one, add one
        and put it at landmarkPosition.
        Returns landmarkName if a new one is created, otherwise none
        """
        fiducialList = self.volumeFiducialList(volumeNode)
        if not fiducialList:
            return None
        fiducialSize = fiducialList.GetNumberOfMarkups()
        for fiducialIndex in range(fiducialSize):
            if fiducialList.GetNthFiducialLabel(fiducialIndex) == landmarkName:
                fiducialList.SetNthMarkupAssociatedNodeID(fiducialIndex, volumeNode.GetID())
                return None
        # if we got here, then there is no fiducial with this name so add one
        fiducialList.AddFiducial(*landmarkPosition)
        fiducialIndex = fiducialList.GetNumberOfFiducials() - 1
        fiducialList.SetNthFiducialLabel(fiducialIndex, landmarkName)
        fiducialList.SetNthFiducialSelected(fiducialIndex, False)
        fiducialList.SetNthMarkupLocked(fiducialIndex, False)
        return landmarkName

    def collectAssociatedFiducials(self, volumeNodes):
        """Look at each fiducial list in scene and find any fiducials associated
        with one of our volumes but not in in one of our lists.
        Add the fiducial as a landmark and delete it from the other list.
        Return the name of the last added landmark if it exists.
        """
        state = self.registationState()
        addedLandmark = None
        volumeNodeIDs = []
        for volumeNode in volumeNodes:
            volumeNodeIDs.append(volumeNode.GetID())
        landmarksByName = self.landmarksForVolumes(volumeNodes)
        fiducialListsInScene = slicer.util.getNodes('vtkMRMLMarkupsFiducialNode*')
        landmarkFiducialLists = []
        for landmarkName in landmarksByName.keys():
            for fiducialList, index in landmarksByName[landmarkName]:
                if fiducialList not in landmarkFiducialLists:
                    landmarkFiducialLists.append(fiducialList)
        listIndexToRemove = []  # remove back to front after identifying them
        for fiducialList in fiducialListsInScene.values():
            if fiducialList not in landmarkFiducialLists:
                # this is not one of our fiducial lists, so look for fiducials
                # associated with one of our volumes
                fiducialSize = fiducialList.GetNumberOfMarkups()
                for fiducialIndex in range(fiducialSize):
                    associatedID = fiducialList.GetNthMarkupAssociatedNodeID(fiducialIndex)
                    if associatedID in volumeNodeIDs:
                        # found one, so add it as a landmark
                        landmarkPosition = fiducialList.GetMarkupPointVector(fiducialIndex, 0)
                        try:
                            volumeNode = slicer.util.getNode(associatedID)
                        except slicer.util.MRMLNodeNotFoundException:
                            volumeNode = None
                        # if new fiducial is associated with moving volume,
                        # then map the position back to where it would have been
                        # if it were not transformed, if not, then calculate where
                        # the point would be on the moving volume
                        movingPosition = [0., ] * 3
                        volumeTransformNode = state.transformed.GetParentTransformNode()
                        volumeTransform = vtk.vtkGeneralTransform()
                        if volumeTransformNode:
                            if volumeNode == state.moving:
                                # in this case, moving stays and other point moves
                                volumeTransformNode.GetTransformToWorld(volumeTransform)
                                movingPosition[:] = landmarkPosition
                                volumeTransform.TransformPoint(movingPosition, landmarkPosition)
                            else:
                                # in this case, landmark stays and moving point moves
                                volumeTransformNode.GetTransformFromWorld(volumeTransform)
                                volumeTransform.TransformPoint(landmarkPosition, movingPosition)
                        addedLandmark = self.addLandmark(volumeNodes, landmarkPosition, movingPosition)
                        listIndexToRemove.insert(0, (fiducialList, fiducialIndex))
        for fiducialList, fiducialIndex in listIndexToRemove:
            fiducialList.RemoveMarkup(fiducialIndex)
        return addedLandmark

    def landmarksFromFiducials(self, volumeNodes):
        """Look through all fiducials in the scene and make sure they
        are in a fiducial list that is associated with the same
        volume node.  If they are in the wrong list fix the node id, and make a new
        duplicate fiducial in the correct list.
        This can be used when responding to new fiducials added to the scene.
        Returns the most recently added landmark (or None).
        """
        addedLandmark = None
        for volumeNode in volumeNodes:
            fiducialList = self.volumeFiducialList(volumeNode)
            if not fiducialList:
                print("no fiducialList for volume %s" % volumeNode.GetName())
                continue
            fiducialSize = fiducialList.GetNumberOfMarkups()
            for fiducialIndex in range(fiducialSize):
                fiducialAssociatedVolumeID = fiducialList.GetNthMarkupAssociatedNodeID(fiducialIndex)
                landmarkName = fiducialList.GetNthFiducialLabel(fiducialIndex)
                landmarkPosition = fiducialList.GetMarkupPointVector(fiducialIndex, 0)
                if fiducialAssociatedVolumeID != volumeNode.GetID():
                    # fiducial was placed on a viewer associated with the non-active list, so change it
                    fiducialList.SetNthMarkupAssociatedNodeID(fiducialIndex, volumeNode.GetID())
                # now make sure all other lists have a corresponding fiducial (same name)
                for otherVolumeNode in volumeNodes:
                    if otherVolumeNode != volumeNode:
                        addedFiducial = self.ensureFiducialInListForVolume(otherVolumeNode, landmarkName,
                                                                           landmarkPosition)
                        if addedFiducial:
                            addedLandmark = addedFiducial
        return addedLandmark

    def vtkPointsForVolumes(self, volumeNodes, fiducialNodes):
        """Return dictionary of vtkPoints instances containing the fiducial points
        associated with current landmarks, indexed by volume"""
        points = {}
        for volumeNode in volumeNodes:
            points[volumeNode] = vtk.vtkPoints()
        sameNumberOfNodes = len(volumeNodes) == len(fiducialNodes)
        noNoneNodes = None not in volumeNodes and None not in fiducialNodes
        if sameNumberOfNodes and noNoneNodes:
            fiducialCount = fiducialNodes[0].GetNumberOfFiducials()
            for fiducialNode in fiducialNodes:
                if fiducialCount != fiducialNode.GetNumberOfFiducials():
                    raise Exception("Fiducial counts don't match {0}".format(fiducialCount))
            point = [0, ] * 3
            indices = range(fiducialCount)
            for fiducials, volumeNode in zip(fiducialNodes, volumeNodes):
                for index in indices:
                    fiducials.GetNthFiducialPosition(index, point)
                    points[volumeNode].InsertNextPoint(point)
        return points


class BonesSegmentationTest(unittest.TestCase):
    """
    This is the test case for your scripted module.
    """

    def delayDisplay(self, message, msec=1000):
        """This utility method displays a small dialog and waits.
        This does two things: 1) it lets the event loop catch up
        to the state of the test so that rendering and widget updates
        have all taken place before the test continues and 2) it
        shows the user/developer/tester the state of the test
        so that we'll know when it breaks.
        """
        print(message)
        self.info = qt.QDialog()
        self.infoLayout = qt.QVBoxLayout()
        self.info.setLayout(self.infoLayout)
        self.label = qt.QLabel(message, self.info)
        self.infoLayout.addWidget(self.label)
        qt.QTimer.singleShot(msec, self.info.close)
        self.info.exec_()

    def clickAndDrag(self, widget, button='Left', start=(10, 10), end=(10, 40), steps=20, modifiers=[]):
        """Send synthetic mouse events to the specified widget (qMRMLSliceWidget or qMRMLThreeDView)
        button : "Left", "Middle", "Right", or "None"
        start, end : window coordinates for action
        steps : number of steps to move in
        modifiers : list containing zero or more of "Shift" or "Control"
        """
        style = widget.interactorStyle()
        interator = style.GetInteractor()
        if button == 'Left':
            down = style.OnLeftButtonDown
            up = style.OnLeftButtonUp
        elif button == 'Right':
            down = style.OnRightButtonDown
            up = style.OnRightButtonUp
        elif button == 'Middle':
            down = style.OnMiddleButtonDown
            up = style.OnMiddleButtonUp
        elif button == 'None' or not button:
            down = lambda: None
            up = lambda: None
        else:
            raise Exception("Bad button - should be Left or Right, not %s" % button)
        if 'Shift' in modifiers:
            interator.SetShiftKey(1)
        if 'Control' in modifiers:
            interator.SetControlKey(1)
        interator.SetEventPosition(*start)
        down()
        for step in range(steps):
            frac = float(step + 1) / steps
            x = int(start[0] + frac * (end[0] - start[0]))
            y = int(start[1] + frac * (end[1] - start[1]))
            interator.SetEventPosition(x, y)
            style.OnMouseMove()
        up()
        interator.SetShiftKey(0)
        interator.SetControlKey(0)

    def moveMouse(self, widget, start=(10, 10), end=(10, 40), steps=20, modifiers=[]):
        """Send synthetic mouse events to the specified widget (qMRMLSliceWidget or qMRMLThreeDView)
        start, end : window coordinates for action
        steps : number of steps to move in
        modifiers : list containing zero or more of "Shift" or "Control"
        """
        style = widget.interactorStyle()
        interator = style.GetInteractor()
        if 'Shift' in modifiers:
            interator.SetShiftKey(1)
        if 'Control' in modifiers:
            interator.SetControlKey(1)
        interator.SetEventPosition(*start)
        for step in range(steps):
            frac = float(step + 1) / steps
            x = int(start[0] + frac * (end[0] - start[0]))
            y = int(start[1] + frac * (end[1] - start[1]))
            interator.SetEventPosition(x, y)
            style.OnMouseMove()
        interator.SetShiftKey(0)
        interator.SetControlKey(0)

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear(0)

    def runTest(self, scenario=None):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        if scenario == "Basic":
            self.test_BonesSegmentationBasic()
        elif scenario == "Affine":
            self.test_BonesSegmentationAffine()
        elif scenario == "ThinPlate":
            self.test_BonesSegmentationThinPlate()
        elif scenario == "VTKv6Picking":
            self.test_BonesSegmentationVTKv6Picking()
        else:
            self.test_BonesSegmentationBasic()
            self.test_BonesSegmentationAffine()
            self.test_BonesSegmentationThinPlate()

    def test_BonesSegmentationBasic(self):
        """
        This tests basic landmarking with two volumes
        """

        self.delayDisplay("Starting test_BonesSegmentationBasic")
        #
        # first, get some data
        #
        import SampleData
        sampleDataLogic = SampleData.SampleDataLogic()
        mrHead = sampleDataLogic.downloadMRHead()
        dtiBrain = sampleDataLogic.downloadDTIBrain()
        self.delayDisplay('Two data sets loaded')

        mainWindow = slicer.util.mainWindow()
        mainWindow.moduleSelector().selectModule('BonesSegmentation')

        w = slicer.modules.BonesSegmentationWidget
        w.volumeSelectors["Fixed"].setCurrentNode(dtiBrain)
        w.volumeSelectors["Moving"].setCurrentNode(mrHead)

        logic = BonesSegmentationLogic()

        for name, point in (
                ('middle-of-right-eye', [35.115070343017578, 74.803565979003906, -21.032917022705078]),
                ('tip-of-nose', [0.50825262069702148, 128.85432434082031, -48.434154510498047]),
                ('right-ear', [80.0, -26.329217910766602, -15.292181015014648]),
        ):
            logic.addFiducial(name, position=point, associatedNode=mrHead)

        for name, point in (
                ('middle-of-right-eye', [28.432207107543945, 71.112533569335938, -41.938472747802734]),
                ('tip-of-nose', [0.9863210916519165, 94.6998291015625, -49.877540588378906]),
                ('right-ear', [79.28509521484375, -12.95069694519043, 5.3944296836853027]),
        ):
            logic.addFiducial(name, position=point, associatedNode=dtiBrain)

        w.onVolumeNodeSelect()
        w.onLayout()
        w.onLandmarkPicked('tip-of-nose')

        self.delayDisplay('test_BonesSegmentationBasic passed!')

    def test_BonesSegmentationAffine(self):
        """
        This tests basic linear registration with two
        volumes (pre- post-surgery)
        """

        self.delayDisplay("Starting test_BonesSegmentationAffine")
        #
        # first, get some data
        #
        import SampleData
        sampleDataLogic = SampleData.SampleDataLogic()
        pre, post = sampleDataLogic.downloadDentalSurgery()
        self.delayDisplay('Two data sets loaded')

        mainWindow = slicer.util.mainWindow()
        mainWindow.moduleSelector().selectModule('BonesSegmentation')

        w = slicer.modules.BonesSegmentationWidget
        w.setupDialog()
        w.volumeDialogSelectors["Fixed"].setCurrentNode(post)
        w.volumeDialogSelectors["Moving"].setCurrentNode(pre)
        w.onVolumeDialogApply()

        # initiate linear registration
        w.registrationTypeButtons["Affine"].checked = True
        w.registrationTypeButtons["Affine"].clicked()

        w.onLayout(layoutMode="Axi/Sag/Cor")

        self.delayDisplay('test_BonesSegmentationAffine passed!')

    def test_BonesSegmentationThinPlate(self):
        """Test the thin plate spline transform"""
        self.test_BonesSegmentationAffine()

        self.delayDisplay('starting test_BonesSegmentationThinPlate')

        mainWindow = slicer.util.mainWindow()
        mainWindow.moduleSelector().selectModule('BonesSegmentation')

        w = slicer.modules.BonesSegmentationWidget
        pre = w.volumeSelectors["Fixed"].currentNode()
        post = w.volumeSelectors["Moving"].currentNode()

        for name, point in (
                ('L-0', [-91.81303405761719, -36.81013488769531, 76.78043365478516]),
                ('L-1', [-91.81303405761719, -41.065155029296875, 19.57413101196289]),
                ('L-2', [-89.75, -121.12535858154297, 33.5537223815918]),
                ('L-3', [-91.29727935791016, -148.6207275390625, 54.980953216552734]),
                ('L-4', [-89.75, -40.17485046386719, 153.87451171875]),
                ('L-5', [-144.15321350097656, -128.45083618164062, 69.85309600830078]),
                ('L-6', [-40.16628646850586, -128.70603942871094, 71.85968017578125]),):
            w.logic.addFiducial(name, position=point, associatedNode=post)

        for name, point in (
                ('L-0', [-89.75, -48.97413635253906, 70.87068939208984]),
                ('L-1', [-91.81303405761719, -47.7024040222168, 14.120864868164062]),
                ('L-2', [-89.75, -130.1315155029297, 31.712587356567383]),
                ('L-3', [-90.78448486328125, -160.6336212158203, 52.85344696044922]),
                ('L-4', [-85.08663940429688, -47.26158905029297, 143.84193420410156]),
                ('L-5', [-144.1186065673828, -138.91270446777344, 68.24700927734375]),
                ('L-6', [-40.27879333496094, -141.29898071289062, 67.36009216308594]),):
            w.logic.addFiducial(name, position=point, associatedNode=pre)

        # initiate linear registration
        w.registrationTypeButtons["ThinPlate"].checked = True
        w.registrationTypeButtons["ThinPlate"].clicked()

        w.landmarksWidget.pickLandmark('L-4')
        w.onRegistrationType("ThinPlate")

        self.delayDisplay('Applying transform')
        w.currentRegistrationInterface.onThinPlateApply()

        self.delayDisplay('Exporting as a grid node')
        w.currentRegistrationInterface.onExportGrid()

        self.delayDisplay('test_BonesSegmentationThinPlate passed!')

    def test_BonesSegmentationVTKv6Picking(self):
        """Test the picking situation on VTKv6"""

        self.delayDisplay('starting test_BonesSegmentationVTKv6Picking')

        mainWindow = slicer.util.mainWindow()
        mainWindow.moduleSelector().selectModule('BonesSegmentation')

        #
        # first, get some data
        #
        import SampleData
        sampleDataLogic = SampleData.SampleDataLogic()

        dataSource = SampleData.SampleDataSource('fixed',
                                                 'http://slicer.kitware.com/midas3/download/item/157188/small-mr-eye-fixed.nrrd',
                                                 'fixed.nrrd', 'fixed')
        fixed = sampleDataLogic.downloadFromSource(dataSource)[0]

        dataSource = SampleData.SampleDataSource('moving',
                                                 'http://slicer.kitware.com/midas3/download/item/157189/small-mr-eye-moving.nrrd',
                                                 'moving.nrrd', 'moving')
        moving = sampleDataLogic.downloadFromSource(dataSource)[0]

        self.delayDisplay('Two data sets loaded')

        w = slicer.modules.BonesSegmentationWidget
        w.setupDialog()

        w.volumeDialogSelectors["Fixed"].setCurrentNode(fixed)
        w.volumeDialogSelectors["Moving"].setCurrentNode(moving)
        w.onVolumeDialogApply()

        # to help debug picking manager, set some variables that
        # can be accessed via the python console.
        self.delayDisplay('setting widget variables')
        w.lm = slicer.app.layoutManager()
        w.fa = w.lm.sliceWidget('fixed-Axial')
        w.fav = w.fa.sliceView()
        w.favrw = w.fav.renderWindow()
        w.favi = w.fav.interactor()
        w.favpm = w.favi.GetPickingManager()
        w.rens = w.favrw.GetRenderers()
        w.ren = w.rens.GetItemAsObject(0)
        w.cam = w.ren.GetActiveCamera()
        print(w.favpm)

        logic = BonesSegmentationLogic()

        # initiate registration
        w.registrationTypeButtons["ThinPlate"].checked = True
        w.registrationTypeButtons["ThinPlate"].clicked()

        # enter picking mode
        w.landmarksWidget.addLandmark()

        # move the mouse to the middle of the widget so that the first
        # mouse move event will be exactly over the fiducial to simplify
        # breakpoints in mouse move callbacks.
        layoutManager = slicer.app.layoutManager()
        fixedAxialView = layoutManager.sliceWidget('fixed-Axial').sliceView()
        center = (fixedAxialView.width / 2, fixedAxialView.height / 2)
        offset = map(lambda element: element + 100, center)
        self.clickAndDrag(fixedAxialView, start=center, end=center, steps=0)
        self.delayDisplay('Added a landmark, translate to drag at %s to %s' % (center, offset), 200)

        self.clickAndDrag(fixedAxialView, button='Middle', start=center, end=offset, steps=10)
        self.delayDisplay('dragged to translate', 200)
        self.clickAndDrag(fixedAxialView, button='Middle', start=offset, end=center, steps=10)
        self.delayDisplay('translate back', 200)

        globalPoint = fixedAxialView.mapToGlobal(qt.QPoint(*center))
        qt.QCursor().setPos(globalPoint)
        self.delayDisplay('moved to %s' % globalPoint, 200)

        offset = map(lambda element: element + 10, center)
        globalPoint = fixedAxialView.mapToGlobal(qt.QPoint(*offset))
        if False:
            # move the cursor
            qt.QCursor().setPos(globalPoint)
        else:
            # generate the event
            mouseEvent = qt.QMouseEvent(qt.QEvent.MouseMove, globalPoint, 0, 0, 0)
            fixedAxialView.VTKWidget().mouseMoveEvent(mouseEvent)

        self.delayDisplay('moved to %s' % globalPoint, 200)

        self.delayDisplay('test_BonesSegmentationVTKv6Picking passed!')
