# Diffusion Pelvis
This module provides the three most important steps for the exploitation of diffusion images for tractography purposes:
denoising, registration and metric volumes extraction.
Contrary to other Slicer modules, this one does not requires intermediate steps and works directly on DWI image nodes.

Please note that this plug-in implements external software. More specific indication can be found on the [MRTrix3][1], [FSL][3]
and [ANTs][2] websites.

## Installation
Prerequisites: MRTrix3 and ANTs must be installed on the computer. Detailed instructions on how to install them at the following links:<br>
 <https://mrtrix.readthedocs.io/en/latest/installation/before_install.html> <br>
 <https://github.com/ANTsX/ANTs/wiki/>

Note the folder path of the MRTrix3 binaries (e.g. /usr/local/bin), they will be used in the end.<br>
Note the folder path of the ANTs binaries (e.g. /usr/local/antsbin/bin/), they will be used in the end.

From the Slicer menu bar go on Edit --> Application Settings --> Modules

In the Additional module path add the DiffusionPelvis folder and add it up to your favourite modules.

Finally, change the path in config.json file, under the plug-in config folder, with the MRTrix3 and ANTs paths you noted in the beginning (alternatively,
in Unix-based system you can obtain the requested path writing in a terminal 'which mrview' and 'which antsRegistration')

## Usage
The module works directly on diffusion image nodes, to obtain one either proceed to the first step of this plug-in or use the standard
module 'Diffusion-weighted DICOM Import' (despite the name it allows to import also from the NIfTI and NRRD formats).

The three subsection of the plug-in can be considered independent from each other and can be used in any order.
___
### Preprocessing
This section performs the denoising, artifact correction and masking of diffusion weighted images. All the parameters are
chosen automatically extracting the image information directly from the DICOM / NRRD headers.

Additionally, a DWI node is created starting from the DICOM folder containing the raw data.

* **Denoising**: correction of unwanted data fluctuations, exploiting data redundancy in the PCA domain. The window size is chosen
based on the number of diffusion directions (minimum possible: 3,3,3) 
* **Gibbs Artifact Removal**: This type of artifact is created during the reconstruction process of the image. In particular, 
it is often seen (as groups of parallel lines) at the interface between high-contrast regions, due to a spectral leakage in the
Fourier harmonics. It gets really evident especially along the phase-encoding direction and could cause problems during tractography
n case of fibers crossing into regions with different contrast.
* **Motion and Eddy currents correction**: Using a combination of the FSL eddy and topup tools both patients-caused motion
artifacts and scanner-induces eddy currents problems are corrected in one single step. Additionally. the signal dropouts visible
when the subject moves during the diffusion encoding sequence are fixed predicting their intensity values.
* **Bias field correction**: This step is not optional and it is performed automatically every time a denoise operation takes place.
It aims to correct the field inhomogeneity modeling with a B-spline the bias itself and iteratively remapping the intensities 
using histogram-based deconvolutions.
* **Masking**: The masking procedure restrict the image to the regions containing anatomical information. The mask must be
provied in input and can be estimated using the Slicer module Foreground Masking. Masking the image allows for more accurate results
during all the other steps and reduce the computational time.

#### GUI
The input of this section must be either an existing DWI node or a DICOM folder containing the raw images. Be sure to declare,
using the radio button just under the selector, which mode you intend to use.

The only other mandatory field, aside from the input, is the output DWI node. If a whole body mask label map node is present 
that can be specified in the correspondent selector.

Every combination of denoising options is allowed, select what you prefer to use ticking the square boxes. We suggest to always
perform the first two steps. The motion and eddy currents correction, being more time demanding is appropriate when visible 
shape fluctuations are visible (they can be checked analyzing the image contour).

___
### Registration
In order to use the segmentations carried on the volumetric structural image for tractography purposes (seeds positioning, segmentation, ...)
the DWI and the T2 image must be in the same space and completely aligned. Here three types os registration options are offered:

* **Rigid**: Combination of transformation that do not modify the distance between the points of the image. It will apply a
series of rotation and translations in order to have the images roughly aligned.
* **Affine**: Transformation that preserves parallel lines. Adding shears and scaling to the rigid transform a finer
registration is prepared, with an higher chance to have the two images with matching proportions.
* **Elastic**: The elastic deformation will shift and interpolate the voxels of the moving image in order to match as
best as possible the fixed image intensities. It can results in the most accurate results at the expense of the computational
time.

All the registration methods above described are all implemented used ANTs. The parameters have been chosen with in mind the
registration of a b0 image to the space of a volumetric T2w image.

The methods do not need an initialization, the rigid and affine transforms are based on the images mutual information, while the
elastic deformation checks for the cross-correlation. The process proceed iteratively until either the difference between the
images is under a certain threshold or when the algorithm reaches a certain number of iterations. To improve the accuracy 
the registration is performed at four different resolution level.

Performing the registration on image corrected from field inhomogeneities (using the first section of this plug-in) could substantially improve
the results.

Please note that the elastic deformation is a computationally intensive operation and could take a long time (up to some hours).

#### GUI
The registration is performed between a DWI (moving image) and a volumetric strutural image (fixed image). The wholy body masks
can be used to constrain the computation to the portion of the images carrying anatomical information. If only one mask is 
specified it will be ignored. We generally suggest using the masks only for the elastic deformation.

Three registration options are present, that should be set analyzing how much the two images are disaligned.
The elastic deformation can be additionaly fine tuned choosing a preset that controls the termination conditions. A more
strong deformation will force a more strict similarity control but could cause overfitting.
___
### Measures
In this section it is possible to extract metric maps and volume nodes from the DWI volumes. All the metrics are computed
using a diffusion tensor based approach.

While all the metrics can be extracted from the same DWI image, it is not allowed to compute multiple of them at the same time.

* **b-zero**: volumes acquired without the diffusion gradients on. Equivalent to a T2 weighted volume. Used for visualization,
registration and structural analysis.
* **Fractional anisotropy**: Main diffusion tensor metric. Indicates if there is a preferential directions for the water molecules
and how accentuated that is in respect to the others. It is often the starting and termination criteria of tractography algorithms.
* **Mean Diffusivity**: It shows, for each point of the image space, if a diffusion gradient is present and how strong it is,
taking the mean of all the direction vectors.

#### GUI
Straightforward module. The interface is simply composed by two node selector (one for input DWI image, one for the output volume
node) and a set of radio button to specify the metric wanted. Click 'Extract' to launch the computation

[1]: http://www.mrtrix.org
[2]: http://stnava.github.io/ANTs/
[3]: https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSL