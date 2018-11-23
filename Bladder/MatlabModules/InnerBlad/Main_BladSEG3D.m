%% Initialization
clear all
close all
clc

%add path, folders and subfolders
addpath(genpath(pwd));

%% ******************************************
%          LOAD IMAGE - INITIALIZATION POINTS
% ******************************************

%request of image path
[file,path]=uigetfile('/media/IRON_16/dataset_coro_T2_cube/nrrd/*.nrrd','Load');
filename=sprintf('%s%s',path,file);

% Load nrrd image
nrrd=cli_imageread(filename);%(inputParams.inputvolume);
res=abs(nrrd.ijkToLpsTransform(1:3,1:3));
%res=mean(res(res>0)); %get mean resolution
res=mean(max(res)); %get mean resolution
I3D=nrrd.pixelData;

%% Ask numbers of points inside of target
newpoint=[];
for i=1:1
    figure(1),clf
    imshow3D(I3D)
    slice=input('Which Slice ? ');
    I=I3D(:,:,slice);
    figure(1),clf,colormap(gray);imagesc(I);axis image
    %get coordinate of initilize point of bladder
    [xp, yp]= ginput(1);
    newpoint(i,:)=[fix(xp) fix(yp) fix(slice)];
end
close (figure(1))
newpoint(:,1:2)=flip(newpoint(:,1:2),2);

% make a black mask with the white points
temp=zeros(size(I3D));
for i=1:numel(newpoint(:,1))
    temp(newpoint(i,1),newpoint(i,2),newpoint(i,3))=1;
end
%get the centroid from the position of points
Centr=regionprops(temp,'Centroid');
Centr=fix(Centr.Centroid);
Centr(1:2)=flip(Centr(1:2));

%% ******************************************
%          GET BOUNDING BOX
%  ******************************************

tic %start global time
t=tic;  %start partial time
fprintf('Decrease dimension of image .... ')

%size of global 3D imge
[xEnd, yEnd, zEnd]=size(I3D);

% extract dimension of Bounding box
marginX=fix(max(size(I3D))*0.3);
marginY=marginX;
marginZ=marginX;
if (Centr(1)-5)>marginX, xLimSx=Centr(1)-marginX; else xLimSx=5; end
if (Centr(1)+marginX)<xEnd, xLimDx=Centr(1)+marginX; else xLimDx=xEnd-5; end
if (Centr(2)-5)>marginY, yLimSx=Centr(2)-marginY; else yLimSx=5; end
if (Centr(2)+marginY)<yEnd, yLimDx=Centr(2)+marginY; else yLimDx=yEnd-5; end
if (Centr(3)-5)>marginZ, zLimSx=Centr(3)-marginZ; else zLimSx=5; end
if (Centr(3)+marginZ)<zEnd, zLimDx=Centr(3)+marginZ; else zLimDx=zEnd-5; end

%get bounding box
I3Drid=I3D(xLimSx:xLimDx,yLimSx:yLimDx,zLimSx:zLimDx);
clear ('marginX','marginY','marginZ','xEnd','yEnd','zEnd','Centr')
fprintf('done\n\tExecution time: %.2f s \n',toc(t))

%% ******************************************
%                BILATERAL FILTER
% ******************************************

t=tic;
fprintf('Process bilateral filter 3D .... ')
% %select filter parameters
sigmaS=5; %spatial smoothing parameters (standard deviation of the Gaussian kernel)
sigmaR=20; %the smoothing parameter in the "range" dimension
samS=5; %the amount of downsampling performed by the fast approximation in the spatial dimensions (x,y). 
        % In z direction, it is derived from spatial sigmas and samS.
samR=20; %the amount of downsampling in the "range" dimension.
%get the filter result

% process the bilateral filter on the subImage
I3Drid=bilateral3(I3Drid, sigmaS,sigmaS,sigmaR,samS,samR);
I3Drid=im2double(I3Drid);
fprintf('done\n\tExecution time: %.2f s \n',toc(t))

    
%% ******************************************
%         INITIALIZATION INNER BORDER
% *******************************************

t=tic;
fprintf('Initilization of the inner border ....')
% initilize point/s inside of bladder
% 
pointRid=zeros(size(newpoint));
pointRid(:,1)=newpoint(:,1)-xLimSx;
pointRid(:,2)=newpoint(:,2)-yLimSx;
pointRid(:,3)=newpoint(:,3)-zLimSx;

%INIT Sphere
BW=zeros(size(I3Drid));
for i=1:numel(newpoint(:,1))
    r=3;
    [m, n, l]=size(I3Drid);
    [xx,yy, zz] = ndgrid((1:m)-pointRid(i,1),(1:n)-pointRid(i,2), (1:l)-pointRid(i,3));
    temp=(xx.^2 + yy.^2 + zz.^2)<r^2; %disk mask centered in pointRid
    BW =BW + temp;
end

%get the initial distance map (distance transform)
phi = (bwdist(1-BW)-bwdist(BW)-1)+1*(1-BW);

clear('temp','xx','yy','zz','r','m','n','l')

fprintf('done\n\tExecution time: %.2f s \n',toc(t))

%% ***********************************
%           GRADIENT in XYZ
% ***********************************

t=tic;
fprintf('Process gradient in XYZ .... ')
%Get GRADIENT in XYZ
sigma=2;
gradI3D=imgradientxyz(I3Drid,sigma);
% subtract gradient from image to emphasise the border
I3Drid2= I3Drid - 8*gradI3D;
%get a new gradient with emphasised border
gradI3D2 = ExternalForceImage3D(I3Drid2,0.5, 4,sigma);

fprintf('done\n\tExecution time: %.2f s \n',toc(t))

%% ***********************************
%           LEVEL SET 3D SEG
%  ***********************************

t=tic;
fprintf('Segmentation process .... ')
%Set parameter of level set
OptionLS=struct;
OptionLS.verbose=0;     % Parameter to visualize results
OptionLS.mu=1;          % Parameter of regulation term  ( intenral energy)
OptionLS.lam1=-1.2e-2;  % Parameter of intensity term   ( external energy)
OptionLS.lam2=1.2e-2;   % Parameter of intensity term   ( external energy) 
OptionLS.ni=50;         % Parameter of gradient of image( external energy)
OptionLS.dt=1.2;        % Parameter of stepsize dt


%SEGMENTATION KERNEL
Blad3DridLS= LevelSet_3D(phi,I3Drid2,OptionLS,gradI3D2); 
%showphi(I3Drid, Blad3DridLS)

fprintf('done\n\tExecution time: %.2f s \n',toc(t))

if isempty(Blad3DridLS)
   % exit
end

%pause

%% ***********************************
%           MESHING
% ***********************************
t=tic;
fprintf('Meshing process .... ')

%if the image's dimensions is too high, it resize the image. 
%It is necessary to reduce the numbers of faces and vertices of mesh.
[ Blad3DridLS2,gridX,gridY,gridZ,edgelength ] = imresize( Blad3DridLS,res );

%use the Level Set segmentation like a initialization of Snake
[VF] = CONVERT_voxels_to_stl('mesh.stl',Blad3DridLS2,gridX,gridY,gridZ,'ascii');
fprintf('done\n\tExecution time: %.2f s \n',toc(t))

t=tic;
fprintf('Remeshing process .... \n')
iter=10;
[VF, ~, ~]=remesher(VF, edgelength, iter,'remeshed.stl');
fprintf('\n\tExecution time: %.2f s \n',toc(t))

figure(2),clf
patch(VF,'facecolor',[0 0 1],'facealpha',0.3);
axis equal
drawnow;

%% ***********************************
%           ACTIVE CONTOUR SEG
% ***********************************

%   Segmentation
OptionSN=struct;
OptionSN.Verbose=1;     % show important images

%   External Force
OptionSN.Sigma2=1;      % edge energy image

%   options (Gradient Vector Flow)
OptionSN.Mu=0.2;        % Is a trade of scalar between noise and real edge forces
OptionSN.GIterations=0;  
OptionSN.Sigma3=1;      % Used when calculating the Laplacian

%   Internal Force
OptionSN.Alpha=1.2;     % membrame energy  (first order)
OptionSN.Beta=1.2;      % thin plate energy (second order)
OptionSN.Gamma=2.1;     % Time step

%   Motion (Snake)
OptionSN.Iterations=80;        
OptionSN.Kappa=5;       % External (image) field weight
OptionSN.Delta=0.6;     % Balloon Force weight
OptionSN.Lambda=0.6;    % Weight which changes the direction of the image  potential force

t=tic;
fprintf('Segmentation process .... ')

%get the edge of image
gradI3D=canny(I3Drid,3)+0;
%gradI3D=gradI3D+0;
%Use the level set segmentation to delete every possible edge inside of bladder.
A=regionprops(Blad3DridLS,'Area');
if A.Area>40000 
    Blad3DridLSe=imerode(Blad3DridLS,strel('ball',3,0));
    gradI3D(Blad3DridLSe==1)=0;
else
    gradI3D(Blad3DridLS==1)=0;
end
%show Edge Detector
if OptionSN.Verbose==1
    figure(11),imshow3D(gradI3D)
end

%SEGMENTATION KERNEL 
VF2=Snake3D(I3Drid,VF,OptionSN,gradI3D);
fprintf('done\n\tExecution time: %.2f s \n',toc(t))

t=tic;
fprintf('Vexoling process .... ')
gridX=1:1:size(Blad3DridLS,1);
gridY=1:1:size(Blad3DridLS,2);
gridZ=1:1:size(Blad3DridLS,3);
[Blad3DridSN] = VOXELISE(gridX,gridY,gridZ,VF2);
Blad3DridSN=Blad3DridSN+0;
fprintf('done\n\tExecution time: %.2f s \n',toc(t))

if OptionSN.Verbose==1
    fprintf('Plotting .... ')
    temp= zeros(size(I3Drid));
    for i=1:1:size(I3Drid,3)
        Z=I3Drid(:,:,i)/(max(max(max(I3Drid))));
        temp(:,:,i) = rgb2gray(imoverlay(Z, bwperim(Blad3DridSN(:,:,i)), [1 1 1]));
    end
    figure(5),clf
    imshow3D(temp)  
    % pause
end
%% ***********************************
%           POST PROCESSING
% ***********************************

% get as final bladder the bigger one
temp=regionprops(Blad3DridLS,'Area');
VolLS=temp.Area;
temp=regionprops(Blad3DridSN,'Area');
VolSN=temp.Area;
if VolLS>VolSN
    Blad3Drid=Blad3DridLS;
else
    Blad3Drid=Blad3DridSN;
end
%dilatation to reach the outer border
distM=2; %mm
distP=(2/res); %pixel
Blad3Drid=logical(Blad3Drid);
temp=(bwdist(Blad3Drid));

Blad3Drid=temp<=distP+0; 

% fprintf('Plotting .... ')
% temp= zeros(size(I3Drid));
% for i=1:1:size(I3Drid,3)
%     Z=I3Drid(:,:,i)/(max(max(max(I3Drid))));
%     temp(:,:,i) = rgb2gray(imoverlay(Z, bwperim(Blad3Drid(:,:,i)), [1 1 1]));
% end
% figure(5),clf
% imshow3D(temp)



%% ***********************************
%           RESTORE IMAGE DIMENSION
% ***********************************

Blad3D=zeros(size(I3D));
Blad3D(xLimSx:xLimDx,yLimSx:yLimDx,zLimSx:zLimDx)=Blad3Drid;
% set a simbolic number that slicer use to rapresent the bladder in light brown 
Blad3D(Blad3D==1)=13;

%% ***********************************
%          SHOW TOTAL RESULTS
% ***********************************

temp= zeros(size(I3D));
I3D2=im2double(I3D);
for i=1:1:size(I3D,3)
    Z=I3D2(:,:,i)/(max(max(max(I3D2))));
    temp(:,:,i) = rgb2gray(imoverlay(Z, bwperim(Blad3D(:,:,i)), [1 1 1]));
end
figure(7),clf
imshow3D(temp) 

fprintf('Terminated!!!\n')
fprintf('TOTAL Execution time: %.2f s \n',toc)
 