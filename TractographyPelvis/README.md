# TractographyPelvis
This module aims to compensate the 3D Slicer lack of functionality regarding tractography algorithms. Here the MRTrix3
methods are wrapped to extend and enrich the Slicer framework.

Please note that this plug-in implements external softwares. More specific indication can be found on the [MRTrix3][1] website.

## Installation
Prerequisites: MRTrix3 must be installed on the computer. Detailed instructions on how to install it at this link: <https://mrtrix.readthedocs.io/en/latest/installation/before_install.html>

Note the folder path of the MRTrix3 binaries (e.g. /usr/local/bin), they will be used in the end.

From the Slicer menu bar go on Edit --> Application Settings --> Modules

In the Additional module path add the DiffusionPelvis folder and add it up to your favourite modules.

Finally, change the path in config.json file, under the plug-in config folder, with the MRTrix3 path you noted in the beginning (alternatively,
in Unix-based system you can obtain the requested path writing in a terminal 'which mrview')

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

* **Input DWI**: node containing the diffusion weighted volume on which the tractography algorithm will be applied. (*MANDATORY*)

* **Input LabelMap**: The initial seed points search zone, that will eventually be propagated until all the 
fibers are tracked down in their entire lengths. In the situation the searched output is a whole-pelvis tractogram 
this field must correspond to a node with a body mask. For ROI-based tractogram two options are available: Standard LabelMap
(*default*) and Binary Mask. (*MANDATORY*)
    * Standard LabelMap: The seed mask is extracted directly from the IMAG2 label legend. The labels used are: 7 to 9, 15 to 27
    (extremities included). Using the vertebral canal and all the sacral holes.
    * Binary Mask: To use custom masks a label node can be specified (0: background, 1: seeds)

* **Output Fiber Bundle**: output node where the tractography will be stored. This field is only needed in case of ROI-based tractogram.
The whole-pelvis tractograms will not be loaded.

___
#### Parameters
* **Whole Pelvis Mask**: Limit the tractogram in the selected mask. Attention: the fibers extending over the mask border are 
not suppressed completely but truncated at the interface.

* **Exclusion mask**: All the fibers entering in this zone, even if for just one point, are completely discarded.

* **Seed Threshold**: Minimum value needed to consider a voxel a seed point. It indicates an FA value for diffusion tensor based
algorithms and FOD (fiber orientation distribution) for CSD based methods.

* **Cutoff**: Fiber tracking termination condition. When a streamlines enters in a part of the image with a lower FA than the cutoff
threshold the tracking is concluded (FOD amplitude for CSD methods). (The selected Cutoff must always be lower of the Seed Threshold)

* **Admissible Angle**: maximum angle, in degree, that is allowed between tracking steps.

* **Length**: All the output fibers will be selected between those having a length respecting this range. The values are expressed
in millimeters (mm).

* **Algorithm**: The algorithm selection allows for three different methodologies: deterministic diffusion tensor based (FACT),
deterministic CSD based (SD_STREAM), probabilistic CSD based (iFOD2).
    * [FACT][2]: In each voxel the fibers change their trajectories based on the principal diffusion tensor orientation.
    * [SD_STREAM][3]: The fibers are reconstructed following the main direction of the FOD distribution for every point of the image.
    * [iFOD2][4]: Probabilistic approach using the FOD to weight the possible fiber paths.

___
#### Whole Pelvis

* **Use whole**: Ticking this box enables the whole-pelvis modality. The Input LabelMap will be assumed being a binary mask representing
the whole body. The result will be saved on the disk instead of being loaded on Slicer

* **File path**: Specify a file path for the whole-pelvis file. The file extension must be .tck (the standard MRTrix3 tractogram format)

[1]: http://www.mrtrix.org
[2]: https://www.ncbi.nlm.nih.gov/pubmed/9989633
[3]: https://onlinelibrary.wiley.com/doi/abs/10.1002/ima.22005
[4]: https://www.researchgate.net/publication/285641884_Improved_probabilistic_streamlines_tractography_by_2nd_order_integration_over_fibre_orientation_distributions