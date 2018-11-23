function [ Iout,gridX,gridY,gridZ,edgelength ] = imresize( Iin,res )
%imresize
% check the volume of image and change dimension if necessary
% INPUT
% -Iin: input image
% 
% OUTPUT
% -Iout:        output image
% -gridX:       List of the X axis coordinates.
% -edgelength:  remesher parameter
    
    A=regionprops(Iin,'Area'); %get volume in pixel
    if A.Area > 50000 
        gridX=1:2:size(Iin,1);
        gridY=1:2:size(Iin,2);
        gridZ=1:2:size(Iin,3);
        
        %Resize image
        x=0.5;
        T = maketform('affine',[x 0 0; 0 x 0; 0 0 x; 0 0 0;]);
        R = makeresampler({'nearest','nearest','nearest'},'fill');
        Iout = tformarray(Iin,T,R,[1 2 3],[1 2 3], round(size(Iin)*x),[],0);
        
    else   
        gridX=1:1:size(Iin,1);
        gridY=1:1:size(Iin,2);
        gridZ=1:1:size(Iin,3);
        
        Iout=Iin;        
    end
    
    surfTot=sum(sum(sum(bwperim(Iin))));
    %surf=(sqrt(3)/4)*(2)^2;
    %k=surfTot/surf;
    k=2.3e+3; %1.8117e+03;
    edgelength=sqrt(4/sqrt(3)*surfTot/k);

end

