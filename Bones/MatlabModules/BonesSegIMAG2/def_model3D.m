function Segmentation = def_model3D_final(I3D, I3D_pre,res)

%def_model3D: 3D segmentation using deformable models
%   INPUTS:
%           -I3D, the MRI volume 
%           -I3D_pre, the presegmentation mask
%   OUTPUT:
%           -Segmentation, the output segmentation mask

%%Extract the connected components of the label mask
I3D_pre = logical(I3D_pre);
I3D_pre = bwareaopen(I3D_pre,500);
CC = bwconncomp(I3D_pre);

Segmentation = zeros(size(I3D_pre));

for c=1:CC.NumObjects

Preseg_cc = zeros(size(I3D_pre));
Preseg_cc(CC.PixelIdxList{c})=1;

%if the image's dimensions is too high, it resize the image. 
%It is necessary to reduce the numbers of faces and vertices of mesh.
[Preseg_cc2,gridX,gridY,gridZ,edgelength] = imresize(Preseg_cc,res);

%use the  pre-segmentation as initialization for the Snake
[VF] = CONVERT_voxels_to_stl('mesh.stl',Preseg_cc2,gridX,gridY,gridZ,'ascii');

iter=10;
[VF, ~, ~]=remesher(VF, edgelength, iter,'remeshed.stl');

%% ***********************************
%           ACTIVE CONTOUR SEG
% ***********************************

%% Parameters
OptionSN=struct;
OptionSN.Verbose=0;     % show important images
%External Force
OptionSN.Sigma2=1;      % edge energy image
%options (Gradient Vector Flow)
OptionSN.Mu=0.2;        
OptionSN.GIterations=0; % GVF iterations  
OptionSN.Sigma3=1;      % Used when calculating the Laplacian
OptionSN.Gamma=1;       % Time step
OptionSN.Alpha=0.018;   % 1st order reg parameter
OptionSN.Beta=0.01;     % 2nd order reg parameter
OptionSN.Iterations=20; % max snake iterations 
OptionSN.Kappa=0.0001;  
OptionSN.Delta=0;       % Balloon Force weight
OptionSN.Lambda=0;      % Weight which changes the direction of the image  potential force


%fixed_VF = find_anchors(VF,point_IJK,15);
VF2=Snake3D_IMAG2(I3D,VF,OptionSN);


gridX=1:1:size(Preseg_cc,1);
gridY=1:1:size(Preseg_cc,2);
gridZ=1:1:size(Preseg_cc,3);
[mask_snake] = VOXELISE(gridX,gridY,gridZ,VF2);
mask_snake=mask_snake+0;

Segmentation(mask_snake==1)=1;
%SE = strel('sphere',4); %smoothing
%Segmentation = imopen(Segmentation, SE); 

end
