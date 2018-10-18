# DiffusionPelvis
This module provides the three most important steps for the exploitation of diffusion images for tractography purpouses:
denoising, registration and metrix extraction.
In opposition to other Slicer modules, this one does not requires intermediate steps and works directly on the DWI image node.

Please note that this plug-in implements external softwares. More specific indication can be found on the [MRTrix3][1] and
[ANTs][2] website.

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
The module works directly on a diffusion image node, to obtain one either proceed to the first step of this plug-in or use the standard
module 'Diffusion-weighted DICOM Import' (despite the name it allows to import also from the NIfTI and NRRD formats).

The three subsection of the plug-in can be considered independent from each other and be used in any order.
___
### Preprocessing
This section performs the denoising, artifact correction and masking of diffusion weighted images. All the parameters are
chosen automatically extracting the image information directly from the DICOM / NRRD headers.

Additionally, a DWI node is created starting from the DICOM folder containing the raw data.

* **Denoising**:
* **Gibbs Artifact Removal**:
* **Motion and Eddy currents correction**:
* **Bias field correction**:
* **Masking**:

#### GUI


___
### Registration

___
### Measures


[1]: http://www.mrtrix.org
[2]: http://stnava.github.io/ANTs/