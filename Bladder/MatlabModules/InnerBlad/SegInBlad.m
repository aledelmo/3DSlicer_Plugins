function [ Blad3D, Blad3DLS] = SegInBlad( I3D , point, res )
%Segment bladder
%   OUTPUT: 
%       Blad3D - Mask 3D of bladder
%   INPUT: 
%       nrrd - Original image
%       point - initial point inside of bladder

    %% ******************************************
    %          LOAD IMAGE - BOUNDING BOX
    % ******************************************
    %WAIT BAR
    steps=8;
    x=1*1/steps;
    h = waitbar(x,'Loading image ... ') ;
    
    %get initialization point    
    %point(:,1:2)=flip(point(:,1:2),2);
    temp=zeros(size(I3D));
    for i=1:numel(point(:,1))
        temp(point(i,1),point(i,2),point(i,3))=1;
    end
    %get centroid of image
    Centr=regionprops(temp,'Centroid');
    Centr=fix(Centr.Centroid);
    Centr(1:2)=flip(Centr(1:2));
       
    %size of global 3D imge
    [xEnd, yEnd, zEnd]=size(I3D);
    % extract dimension of subImage
    marginX=fix(max(size(I3D))*0.3);
    marginY=marginX;
    marginZ=marginX;
    if (Centr(1)-5)>marginX, xLimSx=Centr(1)-marginX; else xLimSx=5; end
    if (Centr(1)+marginX)<xEnd, xLimDx=Centr(1)+marginX; else xLimDx=xEnd-5; end
    if (Centr(2)-5)>marginY, yLimSx=Centr(2)-marginY; else yLimSx=5; end
    if (Centr(2)+marginY)<yEnd, yLimDx=Centr(2)+marginY; else yLimDx=yEnd-5; end
    if (Centr(3)-5)>marginZ, zLimSx=Centr(3)-marginZ; else zLimSx=5; end
    if (Centr(3)+marginZ)<zEnd, zLimDx=Centr(3)+marginZ; else zLimDx=zEnd-5; end
    
    % get bounding box of original image
    I3Drid=I3D(xLimSx:xLimDx,yLimSx:yLimDx,zLimSx:zLimDx);
    
    %% ******************************************
    %                BILATERAL FILTER
    % ******************************************
    x=2*1/steps;
    waitbar(x,h,'Processing filter 3D ....') ;

    
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
    
    %% ******************************************
    %         INITIALIZATION INNER BORDER
    % ******************************************
    x=3*1/steps;
    waitbar(x,h,'Initilization contour ....') ;
    
    %initilize point of bladder in subImage
    pointRid=zeros(size(point));
    pointRid(:,1)=point(:,1)-xLimSx;
    pointRid(:,2)=point(:,2)-yLimSx;
    pointRid(:,3)=point(:,3)-zLimSx;
    
    %INIT Sphere
    BW=zeros(size(I3Drid));
    for i=1:numel(point(:,1))
        r=3;
        [m, n, l]=size(I3Drid);
        [xx,yy, zz] = ndgrid((1:m)-pointRid(i,1),(1:n)-pointRid(i,2), (1:l)-pointRid(i,3));
        temp=(xx.^2 + yy.^2 + zz.^2)<r^2; %disk mask centered in pointRid
        BW =BW + temp;
    end

    %get the initial distance map (distance transform)
    phi = (bwdist(1-BW)-bwdist(BW)-1)+1*(1-BW);
    
    
    %% ***********************************
    %           GRADIENT in XYZ
    % ***********************************
    x=4*1/steps;
    waitbar(x,h,'Processing other filter 3D ....') ;
    
     %Get GRADIENT in XYZ
    sigma=2;
    gradI3D=imgradientxyz(I3Drid,sigma);
    % subtract gradient from image to emphasise the border
    I3Drid2= I3Drid - 8*gradI3D;
    %get a new gradient with emphasised border
    gradI3D2 = ExternalForceImage3D(I3Drid2,0.5, 4,sigma);
    
    %% ***********************************
    %           LEVEL SET 3D SEG
    % ***********************************
    x=5*1/steps;
    waitbar(x,h,'First segmentation ....') ;
    
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
    if isempty(Blad3DridLS)
        Blad3D=zeros(size(I3D));
        Blad3DLS=Blad3D;
        Blad3DSN=Blad3D;
        close(h)
        return
    end
    
    %% ***********************************
    %           MESHING
    % ***********************************
    x=6*1/steps;
    waitbar(x,h,'Getting ready for second segmentation ....') ;
    
    %Get Edgelength and Image resized
    [ Blad3DridLS2,gridX,gridY,gridZ,edgelength ] = imresize( Blad3DridLS,res );
    
    %get mesh of image, face and vertices
    [VF] = CONVERT_voxels_to_stl('mesh.stl',Blad3DridLS2,gridX,gridY,gridZ,'ascii');
    
    %remeshing to reduce numbers of triangle (structural element)  
    iter=10;
    [VF, ~, ~]=remesher(VF, edgelength, iter,'remeshed.stl');
    
    %% ***********************************
    %           ACTIVE CONTOUR SEG
    % ***********************************
    x=7*1/steps;
    waitbar(x,h,'Second segmentation ....') ;
    
    %   Segmentation
    OptionSN=struct;
    OptionSN.Verbose=0;     % show important images

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
    
    %get the edge of image
    gradI3D=canny(I3Drid,3);
    gradI3D=gradI3D+0;
    %Use the level set segmentation to delete every possible edge inside of bladder.
    A=regionprops(Blad3DridLS,'Area');
    if A.Area>40000 
        Blad3DridLSe=imerode(Blad3DridLS,strel('ball',3,0));
        gradI3D(Blad3DridLSe==1)=0;
    else
        gradI3D(Blad3DridLS==1)=0;
    end

    %SEGMENTATION KERNEL 
    VF2=Snake3D(I3Drid,VF,OptionSN,gradI3D);
    
    %voxeling process
    gridX=1:1:size(Blad3DridLS,1);
    gridY=1:1:size(Blad3DridLS,2);
    gridZ=1:1:size(Blad3DridLS,3);
    [Blad3DridSN] = VOXELISE(gridX,gridY,gridZ,VF2);
    Blad3DridSN=Blad3DridSN+0;
       
    %% ***********************************
    %           POST PROCESSING
    % ***********************************
    x=8*1/steps;
    waitbar(x,h,'Finish !!') ;
   
    
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
    
    %% ***********************************
    %           RESTORE IMAGE DIMENSION
    % ***********************************
    
    Blad3D=zeros(size(I3D));
    Blad3D(xLimSx:xLimDx,yLimSx:yLimDx,zLimSx:zLimDx)=Blad3Drid;
    Blad3DLS(xLimSx:xLimDx,yLimSx:yLimDx,zLimSx:zLimDx)=Blad3DridLS;
    
    close(h)
