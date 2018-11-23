function FV=Snake3D_anchors_new_final(I,FV,Options)
% 
% inputs,
%   I : An Image of type double preferable ranged [0..1]
%   FV : Structure with triangulated mesh, with list of faces FV.faces N x 3
%        and list of vertices M x 3
%   Options : A struct with all snake options
%   
% outputs,
%   OV : Structure with triangulated mesh of the final surface
%
% options (general),
%  Option.Verbose : If true show important images, default false
%  Options.Gamma : Time step, default 1
%  Options.Iterations : Number of iterations, default 100
%
% options (Image Edge Energy / Image force))
%  Options.Sigma1 : Sigma used to calculate image derivatives, default 2
%  Options.Wline : Attraction to lines, if negative to black lines otherwise white
%                    lines , default 0.04
%  Options.Wedge : Attraction to edges, default 2.0
%  Options.Sigma2 : Sigma used to calculate the gradient of the edge energy
%                    image (which gives the image force), default 2
%
% options (Gradient Vector Flow)
%  Options.Mu : Trade of between real edge vectors, and noise vectors,
%                default 0.2. (Warning setting this to high >0.5 gives
%                an instable Vector Flow)
%  Options.GIterations : Number of GVF iterations, default 0
%  Options.Sigma3 : Sigma used to calculate the laplacian in GVF, default 1.0
%
% options (Snake)
%  Options.Alpha : Membrame energy  (first order), default 0.2
%  Options.Beta : Thin plate energy (second order), default 0.2
%  Options.Delta : Baloon force, default 0.1
%  Options.Kappa : Weight of external image force, default 2
%  Options.Lambda : Weight which changes the direction of the image 
%                   potential force to the direction of the surface
%                   normal, value default 0.8 (range [0..1])
%                   (Keeps the surface from self intersecting)


% Process inputs
defaultoptions=struct('Verbose',false,'Wline',0.04,'Wedge',2,'Sigma1',2,'Sigma2',2,'Alpha',0.2,'Beta',0.2,'Delta',0.1,'Gamma',1,'Kappa',2,'Iterations',100,'GIterations',0,'Mu',0.2,'Sigma3',1,'Lambda',0.8);
if(~exist('Options','var')), 
    Options=defaultoptions; 
else
    tags = fieldnames(defaultoptions);
    for i=1:length(tags)
         if(~isfield(Options,tags{i})), Options.(tags{i})=defaultoptions.(tags{i}); end
    end
    if(length(tags)~=length(fieldnames(Options))), 
        warning('snake:unknownoption','unknown options found');
    end
end

% Convert input to single if xintxx
if(~strcmpi(class(I),'single')&&~strcmpi(class(I),'double'))
    I=single(I);
end

% The surface faces must always be clockwise (because of the balloon force)
FV=MakeContourClockwise3D(FV);

% Eext = ExternalForceImage3D(I,Options.Wline, Options.Wedge,Options.Sigma1);
Eext = ExternalForceImage3D(I,0,3,1);

% Make the external force (flow) field.
Fx=ImageDerivatives3D(Eext,Options.Sigma2,'x');
Fy=ImageDerivatives3D(Eext,Options.Sigma2,'y');
Fz=ImageDerivatives3D(Eext,Options.Sigma2,'z');

Fext(:,:,:,1)=Fx*2*Options.Sigma2^2;
Fext(:,:,:,2)=Fy*2*Options.Sigma2^2;
Fext(:,:,:,3)=Fz*2*Options.Sigma2^2;


% Do Gradient vector flow, optimalization
Fext=GVFOptimizeImageForces3D(Fext, Options.Mu, Options.GIterations, Options.Sigma3);
% Show the image, contour and force field
if(Options.Verbose)
     drawnow; pause(0.1);
     h=figure(3); set(h,'render','opengl')
     subplot(2,3,1),imshow(squeeze(Eext(:,:,round(end/2))),[]);
     subplot(2,3,2),imshow(squeeze(Eext(:,round(end/2),:)),[]);
     subplot(2,3,3),imshow(squeeze(Eext(round(end/2),:,:)),[]);
     subplot(2,3,4),imshow(squeeze(Fext(:,:,round(end/2),:))+0.5);
     subplot(2,3,5),imshow(squeeze(Fext(:,round(end/2),:,:))+0.5);
     subplot(2,3,6),imshow(squeeze(Fext(round(end/2),:,:,:))+0.5);
     drawnow; pause(0.1);
end

% Make the interal force matrix, which constrains the moving points to a
% smooth contour
local = 0; % set equal to 1 for local parameters 

if local == 1 
    S=SnakeInternalForceMatrix3D(FV,Options.Alpha,Options.Beta,Options.Gamma,1); %local parameters
else
    S=SnakeInternalForceMatrix3D(FV,Options.Alpha,Options.Beta,Options.Gamma,0); %global parameters
end

di=[];
i=1;
flag=0;
while  i<=Options.Iterations && flag==0; 
    
    Vold=FV.vertices;
    FV=SnakeMoveIteration3D(S,FV,Fext,Options.Gamma,Options.Kappa,Options.Delta,Options.Lambda);
    
    if FV.vertices==0
        FV.vertices=Vold;
    end
    
%     if anchors == 1
%     %%%%%%% Anchor to landmarks points
%     FV.vertices(fixed_idx,:) = Vold(fixed_idx,:);
%     %%%%%%%
%     end

    di=[di mean(mean(abs(Vold-FV.vertices)))];
    
    if di(i)<0.0098
        flag=1;
    end
    % Show current contour
    if(Options.Verbose)
        hh=figure(2);
        set(hh,'render','opengl')
        patch(FV,'facecolor',[1 0 0],'facealpha',0.8);
        drawnow; %pause(0.1);    
    end
    i=i+1;
end
if(Options.Verbose)
    figure(6),clf
    plot(1:numel(di),di)
    xlabel('Iteration')
    ylabel('Mean Motion verties')
    drawnow
end
