function Eextern = ExternalForceImage3D(I,Wline, Wedge,Sigma)
% Eextern = ExternalForceImage3D(I,Wline, Wedge,Sigma)
% 
% inputs, 
%  I : The image
%  Sigma : Sigma used to calculated image derivatives 
%  Wline : Attraction to lines, if negative to black lines otherwise white
%          lines
%  Wterm : Attraction to terminations of lines (end points) and corners
%
% outputs,
%  Eextern : The energy function described by the image
%
% Function is written by D.Kroon University of Twente (July 2010)

Ix=ImageDerivatives3D(I,Sigma,'x');
Iy=ImageDerivatives3D(I,Sigma,'y');
Iz=ImageDerivatives3D(I,Sigma,'z');
Ixy=ImageDerivatives3D(I,Sigma,'xy');
Ixz=ImageDerivatives3D(I,Sigma,'xz');
Iyz=ImageDerivatives3D(I,Sigma,'yz');

Eline = imgaussian(I,Sigma);
Eline=((Eline-min(min(min(Eline))))/(max(max(max(Eline)))-min(min(min(Eline)))));
Eedge = sqrt(Ix.^2+Iy.^2+Iz.^2+Ixy.^2+Ixz.^2+Iyz.^2);
Eedge=((Eedge-min(min(min(Eedge))))/(max(max(max(Eedge)))-min(min(min(Eedge)))));

Eextern= (Wline*Eline - Wedge*Eedge); 

