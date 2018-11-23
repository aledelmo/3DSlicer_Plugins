function [ gradI3D ] = imgradientxyz( I,sigma )
%imgradientxyz 3D gradient along x, y, z, xy, xz, yz
    Jx=ImageDerivatives3D(I,sigma,'x');
    Jy=ImageDerivatives3D(I,sigma,'y');
    Jz=ImageDerivatives3D(I,sigma,'z');
    Jxy=ImageDerivatives3D(I,sigma,'xy');
    Jxz=ImageDerivatives3D(I,sigma,'xz');
    Jyz=ImageDerivatives3D(I,sigma,'yz');
    
    gradI3D=(Jx.^2+Jy.^2+Jz.^2+Jxy.^2+Jxz.^2+Jyz.^2).^(1/2);
end

