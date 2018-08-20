function outputParams=BladderSeg(inputParams)
% Segment a bladder from a choosen point inside it. 
% Give you a mask image of bladder
%
% Parameters:
%  inputParams.inputvolume: input image filename
%  inputParams.point: point locations
%  inputParams.outputvolume: output image filename, result of the processing
%

addpath(genpath(pwd));

% read input image
img=cli_imageread(inputParams.inputvolume); 
% read initilization point 
point_LPS=cli_pointvectordecode(inputParams.point); 

%convert coordinates of points from lps in ijk
point_IJK=round(img.ijkToLpsTransform\[point_LPS; ones(1,size(point_LPS,2))]); 
point_IJK=point_IJK(1:3,:)';

%get mean resolution
res=abs(img.ijkToLpsTransform(1:3,1:3));
res=mean(max(res)); 

%create a copy of input image, we will you it to put the LevelSet
%Segmentation
imgLS=img;

%save image.mat

%Kernel
[img.pixelData , imgLS.pixelData] = SegInBlad( img.pixelData , point_IJK, res );

%dilatation to reach the outer border
distM=2; %mm
distP=(distM/res); %pixel
img.pixelData=logical(img.pixelData);
temp=(bwdist(img.pixelData));

img.pixelData=(temp<=distP)+0;
imgLS.pixelData=imgLS.pixelData+0;
% set a simbolic number that slicer use to rapresent the bladder in light brown
img.pixelData(img.pixelData==1)=226;
imgLS.pixelData(imgLS.pixelData==1)=13;

%check is you are using the Matlabscript or User interface
cli_imagewrite(inputParams.outputMap, img);
if isfield(inputParams, 'outputMapLS')
	cli_imagewrite(inputParams.outputMapLS, imgLS);
end
