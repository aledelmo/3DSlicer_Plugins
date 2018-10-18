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

Note the folder path of the MRTrix3 binaries (e.g. /usr/local/bin), they will be used in the end.
Note the folder path of the ANTs binaries (e.g. /usr/local/antsbin/bin/), they will be used in the end.

From the Slicer menu bar go on Edit --> Application Settings --> Modules

In the Additional module path add the DiffusionPelvis folder and add it up to your favourite modules.

Finally, change the path in config.json file, under the plug-in config folder, with the MRTrix3 and ANTs path syou noted in the beginning (alternatively,
in Unix-based system you can obtain the requested path writing in a terminal 'which mrview' and 'which antsRegistration')

## Usage


### GUI


[1]: http://www.mrtrix.org
[2]: http://stnava.github.io/ANTs/