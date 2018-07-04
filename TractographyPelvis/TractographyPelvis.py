#! /usr/bin/env python

import os
import pickle
import shutil
import sys
import tempfile
import unittest
from itertools import izip
from subprocess import (call)

import ctk
# import cv2
import numpy as np
import numpy.linalg as npl
import qt
import slicer
import vtk
from nibabel.affines import apply_affine
from nibabel.streamlines.tck import TckFile as tck
from scipy.ndimage import generate_binary_structure
from scipy.ndimage.morphology import binary_dilation, binary_fill_holes, binary_opening, binary_erosion
from scipy.spatial import ConvexHull, Delaunay
from vtk.util import numpy_support as ns

__author__ = 'Alessandro Delmonte'
__email__ = 'delmonte.ale92@gmail.com'


def pickle_open(path):
    with open(path, 'rb') as handle:
        env = pickle.load(handle)
        return env


def vtkmatrix_to_numpy(matrix):
    m = np.ones((4, 4))
    for i in range(4):
        for j in range(4):
            m[i, j] = matrix.GetElement(i, j)
    return m


def pipe(cmd, verbose=False, my_env=os.environ):
    if verbose:
        print 'Processing command: ' + str(cmd)

    slicer.app.processEvents()
    return call(cmd, shell=True, stdin=None, stdout=None, stderr=None, executable="/usr/local/bin/zsh", env=my_env)


class TractographyPelvis:
    def __init__(self, parent):
        parent.title = 'Tractography Processing'
        parent.categories = ['Diffusion Pelvis']
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

        seedsCollapsibleButton = ctk.ctkCollapsibleButton()
        seedsCollapsibleButton.text = 'Automatic Seeds generation'

        self.layout.addWidget(seedsCollapsibleButton)

        seedsFormLayout = qt.QFormLayout(seedsCollapsibleButton)

        self.sacrumSelector = slicer.qMRMLNodeComboBox()
        self.sacrumSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.sacrumSelector.selectNodeUponCreation = True
        self.sacrumSelector.addEnabled = False
        self.sacrumSelector.removeEnabled = False
        self.sacrumSelector.noneEnabled = False
        self.sacrumSelector.showHidden = False
        self.sacrumSelector.renameEnabled = False
        self.sacrumSelector.showChildNodeTypes = False
        self.sacrumSelector.setMRMLScene(slicer.mrmlScene)

        self.onsacrumSelect()

        self.sacrumSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onsacrumSelect)
        seedsFormLayout.addRow('Input Sacrum Label: ', self.sacrumSelector)

        self.faSelector = slicer.qMRMLNodeComboBox()
        self.faSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
        self.faSelector.selectNodeUponCreation = True
        self.faSelector.addEnabled = False
        self.faSelector.removeEnabled = False
        self.faSelector.noneEnabled = False
        self.faSelector.showHidden = False
        self.faSelector.renameEnabled = False
        self.faSelector.showChildNodeTypes = False
        self.faSelector.setMRMLScene(slicer.mrmlScene)

        self.onfaSelect()

        self.faSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onfaSelect)
        seedsFormLayout.addRow('FA map: ', self.faSelector)

        self.autoseedsSelector = slicer.qMRMLNodeComboBox()
        self.autoseedsSelector.nodeTypes = ['vtkMRMLLabelMapVolumeNode']
        self.autoseedsSelector.selectNodeUponCreation = True
        self.autoseedsSelector.addEnabled = True
        self.autoseedsSelector.removeEnabled = False
        self.autoseedsSelector.noneEnabled = False
        self.autoseedsSelector.showHidden = False
        self.autoseedsSelector.renameEnabled = False
        self.autoseedsSelector.showChildNodeTypes = False
        self.autoseedsSelector.setMRMLScene(slicer.mrmlScene)

        self.autoseedsSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onautoseedsSelect)
        seedsFormLayout.addRow('Output Seeds Label: ', self.autoseedsSelector)

        self.autoseedsButton = qt.QPushButton('Extract Seeds')
        self.autoseedsButton.toolTip = 'Extract tractography seed points from the sacrum segmentation and the fa map'
        self.autoseedsButton.enabled = True

        self.autoseedsButton.connect('clicked(bool)', self.onautoseedsButton)
        seedsFormLayout.addRow(self.autoseedsButton)

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
        tractoFormLayout.addRow('Input Seeds Label: ', self.seedsSelector)

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
        self.sliderSeeds.value = 0.3
        self.sliderSeeds.spinBoxVisible = True

        tractoFormLayout.addRow('Seeds Threshold (FA)', self.sliderSeeds)

        self.sliderCutoff = ctk.ctkSliderWidget()
        self.sliderCutoff.decimals = 2
        self.sliderCutoff.minimum = 0.
        self.sliderCutoff.maximum = 1.
        self.sliderCutoff.singleStep = 0.01
        self.sliderCutoff.value = 0.10
        self.sliderCutoff.spinBoxVisible = True

        tractoFormLayout.addRow('Cutoff (FA)', self.sliderCutoff)

        self.sliderMinlength = ctk.ctkSliderWidget()
        self.sliderMinlength.decimals = 0
        self.sliderMinlength.minimum = 1.
        self.sliderMinlength.maximum = 800.
        self.sliderMinlength.singleStep = 1.
        self.sliderMinlength.value = 5.
        self.sliderMinlength.spinBoxVisible = True

        tractoFormLayout.addRow('Minimum Fiber Length', self.sliderMinlength)

        self.sliderMaxlength = ctk.ctkSliderWidget()
        self.sliderMaxlength.decimals = 0
        self.sliderMaxlength.minimum = 1.
        self.sliderMaxlength.maximum = 800.
        self.sliderMaxlength.singleStep = 1.
        self.sliderMaxlength.value = 200.
        self.sliderMaxlength.spinBoxVisible = True

        tractoFormLayout.addRow('Maximum Fiber Length', self.sliderMaxlength)

        self.tractoButton = qt.QPushButton('Compute')
        self.tractoButton.toolTip = 'Run the tractography algorithm.'
        self.tractoButton.enabled = True

        self.tractoButton.connect('clicked(bool)', self.ontractoButton)
        tractoFormLayout.addRow(self.tractoButton)

        if self.developerMode:
            """Developer interface"""
            reloadCollapsibleButton = ctk.ctkCollapsibleButton()
            reloadCollapsibleButton.text = 'Advanced - Reload && Test'
            reloadCollapsibleButton.collapsed = False
            self.layout.addWidget(reloadCollapsibleButton)
            reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

            self.reloadButton = qt.QPushButton('Reload')
            self.reloadButton.toolTip = 'Reload this module.'
            self.reloadButton.name = 'TractographyPelvis Reload'
            reloadFormLayout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

            self.reloadAndTestButton = qt.QPushButton('Reload and Test')
            self.reloadAndTestButton.toolTip = 'Reload this module and then run the self tests.'
            reloadFormLayout.addWidget(self.reloadAndTestButton)
            self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

        self.layout.addStretch(1)

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

    def onsacrumSelect(self):
        if self.sacrumSelector.currentNode():
            sacrumNode = slicer.util.arrayFromVolume(self.sacrumSelector.currentNode())
            self.sacrumNode = np.copy(sacrumNode)
            self.sacrumNode = np.swapaxes(self.sacrumNode, 0, 2)
            ijkToRas = vtk.vtkMatrix4x4()
            self.sacrumSelector.currentNode().GetIJKToRASMatrix(ijkToRas)
            self.sacrum_affine = vtkmatrix_to_numpy(ijkToRas)
            self.ijkToRas = ijkToRas

    def onfaSelect(self):
        if self.faSelector.currentNode():
            faNode = slicer.util.arrayFromVolume(self.faSelector.currentNode())
            self.faNode = np.copy(faNode)
            self.faNode = np.swapaxes(self.faNode, 0, 2)
            ijkToRas = vtk.vtkMatrix4x4()
            self.faSelector.currentNode().GetIJKToRASMatrix(ijkToRas)
            self.fa_affine = vtkmatrix_to_numpy(ijkToRas)

    def onautoseedsSelect(self):
        self.autoseedsNode = self.autoseedsSelector.currentNode()

    def onautoseedsButton(self):
        if self.sacrumNode.any() and self.faNode.any():
            seeds = self.logic.autoseeds(self.sacrumNode, self.faNode, self.sacrum_affine, self.fa_affine)
            slicer.util.updateVolumeFromArray(self.autoseedsNode, np.swapaxes(seeds, 0, 2))
            self.autoseedsNode.SetIJKToRASMatrix(self.ijkToRas)

    def ontractoButton(self):
        if self.dwiNode:
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
            if self.seedsNode:
                seeds_path = os.path.join(self.logic.tmp, 'seeds.nii')
                properties = {}
                properties['useCompression'] = 0
                slicer.util.saveNode(self.seedsNode, seeds_path, properties)
            else:
                seeds_path = None
            if self.exclusionNode:
                excl_path = os.path.join(self.logic.tmp, 'exclusion.nii')
                properties = {}
                properties['useCompression'] = 0
                slicer.util.saveNode(self.exclusionNode, excl_path, properties)
            else:
                excl_path = None
            if self.sliderSeeds.value > self.sliderCutoff.value and self.sliderMaxlength.value > self.sliderMinlength.value:
                path = self.logic.tracts(self.sliderMinlength.value, self.sliderMaxlength.value,
                                         self.sliderCutoff.value, self.sliderSeeds.value, data_path, mask_path,
                                         seeds_path,
                                         excl_path, bvec_path, bval_path)
                self.tractoNode = slicer.util.loadFiberBundle(path, True)
                # _, self.tractoNode = slicer.util.loadFiberBundle(path, returnNode=True)

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
        self.my_env = pickle_open('/Applications/Slicer.app/Contents/environ.pickle')

    def __del__(self):
        shutil.rmtree(self.tmp)

    def __repr__(self):
        return 'TractographyPelvisLogic()'

    def __str__(self):
        return 'TractographyPelvis implementation class'

    @staticmethod
    def autoseeds(sacrum, fa, affine_sacrum, affine_fa):
        # struct = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        struct = np.ones((3, 3), dtype=np.uint8)
        sacrum_convex = np.zeros(sacrum.shape)
        for i in xrange(sacrum.shape[1]):
            slice2d = np.zeros(sacrum[:, i, :].shape)
            borders = np.logical_xor(sacrum[:, i, :], binary_erosion(sacrum[:, i, :], struct))
            points = np.argwhere(borders)
            try:
                hull = ConvexHull(points)
                deln = Delaunay(points[hull.vertices])
                idx = np.stack(np.indices(sacrum[:, i, :].shape), axis=-1)
                out_idx = np.nonzero(deln.find_simplex(idx) + 1)
                slice2d[out_idx] = 1
                slice2d = np.logical_xor(slice2d, sacrum[:, i, :])
            except:
                pass
            sacrum_convex[:, i, :] = slice2d

        convex_points = np.argwhere(sacrum_convex)
        label_vox2fa_vox = npl.inv(affine_fa).dot(affine_sacrum)
        fa_points = np.round(apply_affine(label_vox2fa_vox, convex_points))
        for i, ind in enumerate(fa_points.astype(int)):
            if fa[tuple(ind)] < 0.1:
                index = convex_points[i]
                sacrum_convex[tuple(index)] = 0

        struct = generate_binary_structure(3, 3)
        sacrum_convex = binary_opening(sacrum_convex, struct)
        sacrum_convex = binary_dilation(sacrum_convex, struct)
        sacrum_convex = binary_fill_holes(sacrum_convex, struct)
        sacrum_convex[np.nonzero(sacrum)] = 0

        # highest_point = np.amax(np.transpose(np.nonzero(sacrum_convex))[:, 1])
        # lowest_point = np.amin(np.transpose(np.nonzero(sacrum_convex))[:, 1])
        # print highest_point
        # print lowest_point
        #
        # sacrum_convex[:, highest_point - 3:highest_point - 3, :] = 1

        return sacrum_convex.astype(np.int16)

    def tracts(self, Minlength, Maxlength, Cutoff, Seeds_T, data_path, Mask, Seeds, ROE, fbvec, fbval):
        string = 'dwi2tensor -force ' + data_path + ' ' + os.path.join(self.tmp,
                                                                       'DTI.mif') + ' -fslgrad ' + fbvec + ' ' + fbval
        if Mask:
            string = string + ' -mask ' + Mask
        pipe(string, True, self.my_env)

        pipe('tensor2metric -force ' + os.path.join(self.tmp, 'DTI.mif') + ' -vec ' + os.path.join(self.tmp,
                                                                                                   'eigen.mif'),
             True, self.my_env)

        string = 'tckgen -force ' + os.path.join(self.tmp, 'eigen.mif') + ' ' + os.path.join(self.tmp,
                                                                                             'tracto.tck') + ' -algorithm FACT -cutoff ' + str(
            Cutoff) + ' -seed_cutoff ' + str(Seeds_T) + ' -minlength ' + str(Minlength) + \
                 ' -maxlength ' + str(Maxlength) + ' -seed_random_per_voxel ' + Seeds + ' 3 '
        if Mask:
            string = string + ' -mask ' + Mask
        if ROE:
            string = string + ' -exclude ' + ROE

        pipe(string, True, self.my_env)

        final_path = tck2vtk(os.path.join(self.tmp, 'tracto.tck'))

        return final_path


def tck2vtk(path_tck):
    streamlines, _ = read_tck(path_tck)
    file_name, _ = os.path.splitext(path_tck)
    path_vtk = file_name + '.vtk'
    save_vtk(path_vtk, streamlines)
    return path_vtk


def read_tck(filename):
    tck_object = tck.load(filename)
    streamlines = tck_object.streamlines
    header = tck_object.header

    return streamlines, header


def save_vtk(filename, tracts, lines_indices=None):
    lengths = [len(p) for p in tracts]
    line_starts = ns.numpy.r_[0, ns.numpy.cumsum(lengths)]
    if lines_indices is None:
        lines_indices = [ns.numpy.arange(length) + line_start for length, line_start in izip(lengths, line_starts)]

    ids = ns.numpy.hstack([ns.numpy.r_[c[0], c[1]] for c in izip(lengths, lines_indices)])
    vtk_ids = ns.numpy_to_vtkIdTypeArray(ids.astype('int64'), deep=True)

    cell_array = vtk.vtkCellArray()
    cell_array.SetCells(len(tracts), vtk_ids)
    points = ns.numpy.vstack(tracts).astype(ns.get_vtk_to_numpy_typemap()[vtk.VTK_DOUBLE])
    points_array = ns.numpy_to_vtk(points, deep=True)

    poly_data = vtk.vtkPolyData()
    vtk_points = vtk.vtkPoints()
    vtk_points.SetData(points_array)
    poly_data.SetPoints(vtk_points)
    poly_data.SetLines(cell_array)

    poly_data.BuildCells()

    if filename.endswith('.xml') or filename.endswith('.vtp'):
        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetDataModeToBinary()
    else:
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileTypeToBinary()

    writer.SetFileName(filename)
    if hasattr(vtk, 'VTK_MAJOR_VERSION') and vtk.VTK_MAJOR_VERSION > 5:
        writer.SetInputData(poly_data)
    else:
        writer.SetInput(poly_data)
    writer.Write()


class TractographyPelvisTest(unittest.TestCase):

    def __init__(self):
        pass

    def __repr__(self):
        return 'TractographyPelvis(). Derived from {}'.format(unittest.TestCase)

    def __str__(self):
        return 'TractographyPelvis test class'

    def runTest(self, scenario=None):
        pass
