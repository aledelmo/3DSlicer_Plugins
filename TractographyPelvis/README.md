# TractographyPelvis
This module aims to compensate the 3D Slicer lack of functionality regarding tractography algorithms. Here the MRTrix3
methods, at the moment the state of the art for tractography, are wrapped to extend and enrich the Slicer framework.


## Installation

## Usage

The module works directly on a diffusion image node, to obtain one load your diffusion data either using the DiffusionPelvis plug-in or the standard
module 'Diffusion-weighted DICOM Import' (despite the name it allows to import also from the NIfTI and NRRD formats).

We suggest to always denoise the image before preparing the tractogram.

Both ROI-based tractography and whole-pelvis are allowed. In the latter case, due to Slicer limitation, the output must be
saved as a .tck on the drive. The ROI-based tractograms will be automatically loaded in the main scene.

The seed map can be specified either using the standard IMAG2 segmentation list or with a binary mask.

Exploiting the most prominent MRTrix3 methods three type of tractography algorithms are available, based on both the
classical diffusion tensor analysis as well as the most recent Constrained Spherical Deconvolution theory.

The default parameters have been imposed with in mind the extraction of a ROI-based pelvic tractogram

### GUI

The main Graphical User Interface is divided in three sections: input data, tractography parameters and whole
pelvis support.

___
#### Input data

* Input DWI: node containing the diffusion weighted volume on which the tractography algorithm will be applied. (*MANDATORY*)

* Input LabelMap: The initial seed points search zone, that will eventually be propagated until all the 
fibers are tracked down in their entire lengths. In the situation the searched output is a whole-pelvis tractogram 
this field must correspond to a node with a body mask. For ROI-based tractogram two options are available: Standard LabelMap
(*default*) and Binary Mask.
    * Standard LabelMap: The seed mask is extracted directly from the IMAG2 label legend. The labels used are: 7 to 9, 15 to 27
    (extremities included). Finally using the vertebral canal and all the sacral holes.
    * Binary Mask: To use custom masks a label node can be specified (0: background, 1: seeds)

* Output Fiber Bundle: output node where the tractography will be stored. This field is only needed in case of ROI-based tractogram.
The whole-pelvis tractograms will not be loaded.

___
#### Parameters
* Whole Pelvis Mask: Limit the tractogram in the selected mask. Attention: the fibers extending over the mask border are 
not suppressed completely but truncated at the interface.

* Exclusion mask: 

* Seed Threshold:

* Cutoff:

* Admissible Angle:

* Length:

* Algorithm:

___
#### Whole Pelvis

* Use whole:

* File path:




## Team / Contacts

## License



