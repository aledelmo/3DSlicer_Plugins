function outputParams=BonesSeg(inputParams)
% Example function that returns the minimum and maximum voxel value in a volume
% and performs thresholding operation on the volume.
%
% Parameters:
%  inputParams.inputvolumeMR: input MR image to segment filename
%  inputParams.inputvolumePRE: presegmentation mask filename
%  inputParams.outputvolume: output image filename, result of the segmentation  


addpath(horzcat(pwd,'/BonesSegIMAG2')); %add folder with other segmentation files
addpath(horzcat(pwd,'/BonesSegIMAG2/Filter3D'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Snake3D'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Filter3D/canny'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Snake3D/mesh'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Snake3D/mesh/meshalization'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Snake3D/mesh/Mesh_voxelisation'));
addpath(horzcat(pwd,'/BonesSegIMAG2/Snake3D/mesh/Remesher'));


% Loading of the images
img=cli_imageread(inputParams.inputvolumeMR);
img_p=cli_imageread(inputParams.inputvolumePRE);
im=img.pixelData;
im=double(im); 
im_p=img_p.pixelData;
im_p=double(im_p);
im_p=im_p/max(max(max(im_p))); 		
im_p(im_p>0.5)=1;
im_p(im_p<=0.5)=0;


%% Segmentation
seg = def_model3D(im,im_p,1) 
img.pixelData(:) = 0;
img.pixelData(seg == 1) = 2;
cli_imagewrite(inputParams.outputvolume, img);
