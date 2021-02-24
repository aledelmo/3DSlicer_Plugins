# MRI Processing

General use algorithms for structural and diffusion MRI processing

![mri](https://i.imgur.com/JE78AnT.jpg)

## Filters

1. [Canny Edge Detector](Filters)

Canny multi-stage edge detection algorithm [1]. In the first step a Gaussian filter with size 5x5 is applied to the image for denoising
purposes. In order to find the edge gradient, a Sobel kernel is then used on horizontal and vertical directions.
Non-maximum suppression is computed on the gradient for thinner edges. Thresholding with hysteresis is finally applied.

Implementation in [OpenCV](https://opencv.org) with UI for interactive thresholding.

*[1] Canny, J., A Computational Approach To Edge Detection, IEEE Transactions on Pattern Analysis and Machine Intelligence, 8(6):679–698, 1986.*

## Segmentation

1. [Bones](Bones)

In order to cope with the high variability in terms of connectivity of the children bones structure during their growth,
we propose to build bones templates from the pelvic CT exams of a few patients of different ages and sex. 

The segmentation is performed in two steps. First, a semi-automatic pre-segmentation is based on the registration of the
chosen anatomical bones template to the target MRI. In the second step, the pre-segmentation is refined through the evolution
of deformable models, in order to extract the final segmentation.

The pre-segmentation of the MRI volumes is obtained through the thin-plate spline (TPS) registration. The TPS-based
registration method [1] manages the deformation of an image M, considered as a grid structure, as an interpolation problem. 
Given two sets of points Ps and Pt in the grid, the optimal non-linear transformation T is obtained by ensuring the 
point- wise correspondence between the two sets [2]. The propagation of the deformation to the rest of the image grid is 
defined by the thin- plate interpolation model, that minimizes the bending energy [3]. 

The final segmentation of the bone structures relies on a parametric deformable model, initialized by the pre-segmentation Mt.
An original feature of the proposed approach is that the landmarks used for the registration constrain the evolution of the surface.

```bibtex
@inproceedings{inproceedings,
author = {Virzì, Alessio and Marret, Jean-Baptiste and Cecile, Muller and Laureline, Berteloot and Boddaert, Nathalie and Sarnacki, Sabine and Bloch, Isabelle},
year = {2017},
month = {04},
title = {A new method based on template registration and deformable models for pelvic bones semi-automatic segmentation in pediatric MRI},
doi = {10.1109/ISBI.2017.7950529}
}
```

*[1] F. L. Bookstein, “Principal warps: Thin-plate splines and the decomposition of deformations,” IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 11, no. 6, pp. 567–585, 1989.*

*[2] F.P.M. Oliveira and J. M. RS Tavares, “Medical image registration: a review,” Computer Methods in Biomechanics and Biomedical Engineering, vol. 17, no. 2, pp. 73–93, 2014.*

*[3] M. Holden, “A review of geometric transformations for non- rigid body registration,” IEEE Transactions on Medical Imaging, vol. 27, no. 1, pp. 111–128, 2008.*

2. [Bladder](Bladder)

Chan-Vese Level set [1] for bladder segmentation from MRI images with modified energy function.

![leveset](https://i.imgur.com/8tPtWPu.jpg)

The first term controls the regularity by penalizing the length. The second term penalizes the enclosed area of C to control its size.
The third and fourth terms penalize discrepancy between the piecewise constant model u and the input image f. 
Where C is the 3D surface, I is the filtered image, μ, η ≥ 0, λ1,λ2 > 0 are weights, c1, c2 are the mean intensity values
inside and outside C and L is a gradient- enhanced image, obtained by subtracting the gradient magnitude from the filtered image.

*[1] An Active Contour Model without Edges, Tony Chan and Luminita Vese, Scale-Space Theories in Computer Vision, 1999, DOI:10.1007/3-540-48236-9_13*

## Diffusion Weighted Imaging

*Note: More documentation is available in the respective folders.*
*Note: Please note that these plug-ins implement external software.*

1. [DiffusionPelvis](DWI)
   
This module provides the three most important steps for the exploitation of diffusion images: denoising (PCA, Gibbs, Motion and
Eddy currents), registration (rigid, affine, elastic) and volume extraction (FA, MD,b0). Contrary to other Slicer modules,
this one does not require intermediate steps and works directly on DWI image nodes.

2. [TractographyPelvis](Tractography)

This module aims to compensate the 3D Slicer lack of functionality regarding tractography algorithms. MRTrix3
methods are wrapped to extend and enrich the Slicer framework.

## Contacts

For any inquiries please contact: 
[Alessandro Delmonte](https://aledelmo.github.io) @ [alessandro.delmonte@institutimagine.org](mailto:alessandro.delmonte@institutimagine.org)

## License

This project is licensed under the [Apache License 2.0](LICENSE) - see the [LICENSE](LICENSE) file for
details