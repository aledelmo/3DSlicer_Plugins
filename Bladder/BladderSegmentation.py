import os, string
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
# import ModEditorLib
import logging
from builtins import range


#
# BladderSegmentation
#
class BladderSegmentation:

    def __init__(self, parent):
        parent.title = "Bladder"  # TODO make this more human readable by adding spaces
        parent.categories = ['IMAG2', "Pelvic Segmentation"]
        parent.dependencies = []
        parent.contributors = ["De Masi Luca (Telecom ParisTech)"]
        parent.helpText = string.Template("""
      This is a tool for coro-T2 MRI image that perform the segmentation of bladder wall in fast way.
      It required just one or more points inside of bladder.

      Please refer to <a href=\"$a/Documentation/$b.$c/Modules/BladderSegmentation\"> the documentation</a>.

      """).substitute({'a': parent.slicerWikiUrl, 'b': slicer.app.majorVersion, 'c': slicer.app.minorVersion})
        parent.acknowledgementText = """
      This file was originally developed by Steve Pieper, Isomics, Inc.
      It was partially funded by NIH grant 3P41RR013218-12S1 and P41 EB015902 the
      Neuroimage Analysis Center (NAC) a Biomedical Technology Resource Center supported
      by the National Institute of Biomedical Imaging and Bioengineering (NIBIB).
      And this work is part of the "National Alliance for Medical Image
      Computing" (NAMIC), funded by the National Institutes of Health
      through the NIH Roadmap for Medical Research, Grant U54 EB005149.
      Information on the National Centers for Biomedical Computing
      can be obtained from http://nihroadmap.nih.gov/bioinformatics.
      This work is also supported by NIH grant 1R01DE024450-01A1
      "Quantification of 3D Bony Changes in Temporomandibular Joint Osteoarthritis"
      (TMJ-OA).
      """  # replace with organization, grant and thanks.
        self.parent = parent

        # Add the corresponding icon to the module

        self.moduleName = self.__class__.__name__
        moduleDir = os.path.dirname(self.parent.path)
        iconPath = os.path.join(moduleDir, 'Icons', self.moduleName + '.png')
        if os.path.isfile(iconPath):
            parent.icon = qt.QIcon(iconPath)

        # Add this test to the SelfTest module's list for discovery when the module
        # is created.  Since this module may be discovered before SelfTests itself,
        # create the list if it doesn't already exist.
        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['BladderSegmentation'] = self.runTest

    def runTest(self):
        tester = BladderSegmentationTest()
        tester.runTest()


#
# BladderSegmentationWidget
#

class BladderSegmentationWidget:
    """The module GUI widget"""

    def __init__(self, parent=None):
        # Get module name by stripping 'Widget' from the class name
        self.moduleName = self.__class__.__name__
        if self.moduleName.endswith('Widget'):
            self.moduleName = self.moduleName[:-6]
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

    #    #LucaDMS - create a new editor istance
    #    self.ModEditor=slicer.modules.modeditor.createNewWidgetRepresentation()
    #    #LucaDMS
    #    self.ModEditorWidget=slicer.modules.ModEditorWidget

    def setup(self):
        # Instantiate and connect widgets ...

        if self.developerMode:
            #
            # Reload and Test area
            #
            """Developer interface"""
            reloadCollapsibleButton = ctk.ctkCollapsibleButton()
            reloadCollapsibleButton.text = "Advanced - Reload && Test"
            reloadCollapsibleButton.collapsed = False
            self.layout.addWidget(reloadCollapsibleButton)
            reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

            # reload button
            # (use this during development, but remove it when delivering
            #  your module to users)
            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "BladderSegmentation Reload"
            reloadFormLayout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

            # reload and test button
            # (use this during development, but remove it when delivering
            #  your module to users)
            self.reloadAndTestButton = qt.QPushButton("Reload and Test")
            self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
            reloadFormLayout.addWidget(self.reloadAndTestButton)
            self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

        #
        # Parameters Area
        #

        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Bladder Segmentation"

        # Add layout form
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        #
        # input volume selector
        #
        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = True
        self.inputSelector.showHidden = False
        self.inputSelector.showChildNodeTypes = False
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.setToolTip("Pick the input to the algorithm.")
        parametersFormLayout.addRow("Input MRI Volume: ", self.inputSelector)

        #
        # input MarkupsFiducialNode selector
        #
        self.inputPointSelector = slicer.qMRMLNodeComboBox()
        self.inputPointSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.inputPointSelector.selectNodeUponCreation = True
        self.inputPointSelector.addEnabled = True
        self.inputPointSelector.removeEnabled = False
        self.inputPointSelector.noneEnabled = True
        self.inputPointSelector.showHidden = False
        self.inputPointSelector.renameEnabled = False
        self.inputPointSelector.showChildNodeTypes = False
        self.inputPointSelector.setMRMLScene(slicer.mrmlScene)
        self.inputPointSelector.setToolTip("Pick up a Markups node listing fiducials.")
        parametersFormLayout.addRow("Source points: ", self.inputPointSelector)

        #
        # output Label selector
        #
        self.outputSelector = slicer.qMRMLNodeComboBox()
        self.outputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.outputSelector.selectNodeUponCreation = True
        self.outputSelector.addEnabled = True
        self.outputSelector.removeEnabled = False
        self.outputSelector.noneEnabled = True
        self.outputSelector.showHidden = False
        self.outputSelector.renameEnabled = False
        self.outputSelector.showChildNodeTypes = False
        self.outputSelector.setMRMLScene(slicer.mrmlScene)
        self.outputSelector.setToolTip("Pick the output to the algorithm.")
        parametersFormLayout.addRow("Output Segmentation: ", self.outputSelector)

        #
        # Apply Button
        #
        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Run the algorithm."
        self.applyButton.enabled = False
        parametersFormLayout.addRow(self.applyButton)

        #    #LucaDMS - Add editor widget
        #    self.layout.addWidget(self.ModEditor)
        #    self.ModEditor.visible=False

        # connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
        self.inputPointSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
        self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Refresh Apply button state
        self.onSelect()

    def cleanup(self):
        pass

    def onSelect(self):
        if not (self.outputSelector.currentNode() == None):
            # self.outputSelector.addEnabled=False
            # num=int(BladderEditUtil.getParameterNode().GetParameter('label'))
            self.outputSelector.currentNode().SetName(self.inputSelector.currentNode().GetName() + '-Bladder-label')

        if not (self.inputPointSelector.currentNode() == None):
            # self.inputPointSelector.addEnabled=False
            # numP=int(BladderEditUtil.getParameterNode().GetParameter('Bladder-point'))
            self.inputPointSelector.currentNode().SetName(self.inputSelector.currentNode().GetName() + '-Bladder-point')

        self.applyButton.enabled = self.inputSelector.currentNode() and self.outputSelector.currentNode() and self.inputPointSelector.currentNode()

    def onApplyButton(self):
        logic = BladderSegmentationLogic()
        # enableScreenshotsFlag = self.enableScreenshotsFlagCheckBox.checked
        # imageThreshold = self.imageThresholdSliderWidget.value
        logic.run(self.inputSelector.currentNode(), self.inputPointSelector.currentNode(),
                  self.outputSelector.currentNode())

    #    #LucaDMS - set master volume and label in ModEditor
    #    self.ModEditorWidget.setVolumes(self.inputSelector.currentNode(), self.outputSelector.currentNode())
    #    #LucaDMS
    #    self.ModEditorWidget.visibleHelperBox(False)
    #    #LucaDMS - set visible the editor
    #    self.ModEditor.visible=True

    def onReload(self):
        """
        ModuleWizard will substitute correct default moduleName.
        Generic reload method for any scripted module.
        """
        slicer.util.reloadScriptedModule(self.moduleName)

    def onReloadAndTest(self):
        try:
            self.onReload()
            test = slicer.selfTests[self.moduleName]
            test()
        except Exception, e:
            import traceback
            traceback.print_exc()
            errorMessage = "Reload and Test: Exception!\n\n" + str(e) + "\n\nSee Python Console for Stack Trace"
            slicer.util.errorDisplay(errorMessage)


#
# BladderSegmentationLogic
#

class BladderSegmentationLogic:
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        # Get module name by stripping 'Logic' from the class name
        self.moduleName = self.__class__.__name__
        if self.moduleName.endswith('Logic'):
            self.moduleName = self.moduleName[:-5]

        # If parameter node is singleton then only one parameter node
        # is allowed in a scene.
        # Derived classes can set self.isSingletonParameterNode = False
        # to allow having multiple parameter nodes in the scene.
        self.isSingletonParameterNode = True

    def hasImageData(self, volumeNode):
        """This is an example logic method that
        returns true if the passed in volume
        node has valid image data
        """
        if not volumeNode:
            logging.debug('hasImageData failed: no volume node')
            return False
        if volumeNode.GetImageData() == None:
            logging.debug('hasImageData failed: no image data in volume node')
            return False
        return True

    def isValidInputOutputData(self, inputVolumeNode, inputPointNode, outputVolumeNode):
        """Validates if the output is not the same as input
        """
        if not inputPointNode:
            logging.debug('isValidInputOutputData failed: no input point node defined')
            return False
        if not inputVolumeNode:
            logging.debug('isValidInputOutputData failed: no input volume node defined')
            return False
        if not outputVolumeNode:
            logging.debug('isValidInputOutputData failed: no output volume node defined')
            return False
        if inputVolumeNode.GetID() == outputVolumeNode.GetID():
            logging.debug(
                'isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
            return False
        return True

    def run(self, inputVolume, inputPoint, outputVolume):
        """
        Run the actual algorithm
        """

        if not self.isValidInputOutputData(inputVolume, inputPoint, outputVolume):
            slicer.util.errorDisplay('Input output error !')
            return False

        logging.info('Processing started')

        # LucaDMS Computes the segmentation output volume using bladderseg matlab script
        bladParams = {}
        bladParams['inputvolume'] = inputVolume.GetID()
        bladParams['point'] = inputPoint.GetID()
        bladParams["outputMap"] = outputVolume.GetID()

        cliNode = slicer.cli.run(slicer.modules.bladderseg, None, bladParams, wait_for_completion=True)

        # LucaDMS - It sets correct name to the parameters
        outputVolume.SetName(inputVolume.GetName() + '-Bladder-label')
        inputPoint.SetName(inputVolume.GetName() + '-Bladder-points')
        inputPoint.SetMarkupLabelFormat(inputVolume.GetName() + '-points-%d')
        # LucaDMS - It changes the label map color
        volumeNode = slicer.util.getNode(outputVolume.GetID())
        logging.info(volumeNode)
        displayNode = volumeNode.GetDisplayNode()
        displayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileGenericAnatomyColors.txt')

        # LucaDMS - It built the 3D model of the segmentation using the modelmaker module
        modelParams = {}
        modelParams['Name'] = inputVolume.GetName() + '-Bladder'
        modelParams["InputVolume"] = outputVolume.GetID()
        modelParams['FilterType'] = "Sinc"
        # Selects the refer value of label, that will be modeled
        modelParams['Labels'] = 226
        modelParams["StartLabel"] = -1
        modelParams["EndLabel"] = -1
        # Smoothing parameters
        modelParams['GenerateAll'] = False
        modelParams["JointSmoothing"] = False
        modelParams["SplitNormals"] = True
        modelParams["PointNormals"] = True
        modelParams["SkipUnNamed"] = True
        modelParams["Decimate"] = 0.25
        modelParams["Smooth"] = 10
        # output
        # - make a new hierarchy node if needed
        numNodes = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLModelHierarchyNode")
        outHierarchy = None
        for n in range(numNodes):
            node = slicer.mrmlScene.GetNthNodeByClass(n, "vtkMRMLModelHierarchyNode")
            if node.GetName() == "Bladder Models":
                outHierarchy = node
                break

        if not outHierarchy:
            outHierarchy = slicer.vtkMRMLModelHierarchyNode()
            outHierarchy.SetScene(slicer.mrmlScene)
            outHierarchy.SetName("Bladder Models")
            slicer.mrmlScene.AddNode(outHierarchy)

        modelParams["ModelSceneFile"] = outHierarchy
        #
        # run the task (in the background)
        # - use the GUI to provide progress feedback
        # - use the GUI's Logic to invoke the task
        # - model will show up when the processing is finished
        #
        modelMaker = slicer.modules.modelmaker
        slicer.cli.run(modelMaker, None, modelParams)

        slicer.util.showStatusMessage("Model Making Started...", 2000)

        logging.info('Processing completed')

        return True


class BladderSegmentationTest:

    def __init__(self, *args, **kwargs):
        super(ScriptedLoadableModuleTest, self).__init__(*args, **kwargs)

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_Bladder1()

    def test_Bladder1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")
        #
        # first, get some data
        #
        import urllib
        downloads = (
            ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

        for url, name, loader in downloads:
            filePath = slicer.app.temporaryPath + '/' + name
            if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
                logging.info('Requesting download %s from %s...\n' % (name, url))
                urllib.urlretrieve(url, filePath)
            if loader:
                logging.info('Loading %s...' % (name,))
                loader(filePath)
        self.delayDisplay('Finished with download and loading')

        volumeNode = slicer.util.getNode(pattern="FA")
        logic = BladderLogic()
        self.assertTrue(logic.hasImageData(volumeNode))
        self.delayDisplay('Test passed!')
