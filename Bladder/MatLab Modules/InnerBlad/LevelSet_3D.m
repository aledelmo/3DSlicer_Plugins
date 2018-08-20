function [ bladder ] = LevelSet_3D(phi,I,OptionLS,gradI)
%CV_Seg Kernel of level set segmentation
%   Detailed explanation goes here
  
    % INITIALIZATION
    phiInit=phi>=0; % get mask of initialization
    phiInit=phiInit+0;
    connInit=bwconncomp(phiInit);
    
    % KERNEL SEGMENTATION
    H=(phi>=0)+0;

    % External Energy - Homogenity Term
    c1 = sum(sum(sum(I.*H)))/sum(sum(sum(H))); % average inside of Phi0
    c2 = sum(sum(sum(I.*(1-H))))/sum(sum(sum(1-H))); % average outside of Phi0
    force_ext=OptionLS.lam1*(I-c1).^2+OptionLS.lam2*(I-c2).^2+OptionLS.ni*gradI;

    % Internal Energy - Regulation term
    [ux, uy, uz]=gradient(phi+0); 
    force_int=OptionLS.mu.*sqrt(ux.^2+uy.^2+uz.^2);

    %update funtional phi
    phi = phi+OptionLS.dt.*force_ext;
    phi = phi+OptionLS.dt.*force_int;

    %get the mask of segmentation
    seg=(phi>=0); 
    temp=bwconncomp(seg); %-- Find connected element
    siz=temp.NumObjects; %-- obtain the number of element
    flag=0;
    j=1;
    %-- find the connective element that include the initialization
    while flag==0 && j<=siz
        if intersection(connInit,temp.PixelIdxList{j})
            phi=zeros(size(phi));
            phi(temp.PixelIdxList{j})=1;
            flag=1;           
        end
        j=j+1;
    end       
    
    if flag==0 
        msgbox('Invalid Points: Select the point not too much distant','Error','error');
        bladder=[];
        OptionLS.verbose=0;
    end

    
    %-- POST PROCESS, morphological operation to delete the flaws outside
    
    if flag==1
        segB=(phi>0); %segmentation before postporcessing
        A=regionprops(segB,'Area');
        %-- get the radius for erotion/dilation
        if A.Area>40000 
            if max(size(I))>200
                r=5;
            else
                r=3;
            end
        else % bladder too small, no erotion/dilation
            r=2;
        end
        %E=imerode(seg,strel3D(r));
        E=imerode(segB,strel('disk',r));
        temp=bwconncomp(E); %-- Find connected element
        siz=temp.NumObjects; %-- obtain the number of element
        
        if siz>1 && sum(sum(sum(E)))>100
%             flag=0;
%             j=1;
%              %-- find the connective element that include the initialization
%             while flag==0 && j<=siz
%                 if intersection(connInit,temp.PixelIdxList{j})
%                     phi=zeros(size(phi));
%                     phi(temp.PixelIdxList{j})=1;
%                     flag=1;
%                 end %intersection
%                 j=j+1;
%             end %while
            [seg, flag]=findConn(connInit,temp,segB);
            
            if flag==1 %good erotion 
                if r==3, r=2; end
                seg=imdilate(seg,strel('disk',r));
                %bladder=(phi>0)+0;
                bladder=seg+0;
            else %bad erotion, structural element too big
                r=2;
                seg=imopen(segB,strel('disk',r));
                %bladder=imclose(bladder,strel('disk',r));
                %bladder=seg;
                temp=bwconncomp(seg); %-- Find connected element
                siz=temp.NumObjects; %-- obtain the number of element
                if siz>1
                    [seg, flag]=findConn(connInit,temp,segB);
                    if flag==1 
                        bladder=seg+0;
                    else
                        bladder=segB+0;
                    end
                else
                    bladder=seg+0;
                end %siz>1
                
            end %flag==1
            
        else %siz==1
            if r>2
                bladder=imclose(imopen(segB,strel('disk',r)),strel('disk',r));
            else
                bladder=segB+0;
            end
        end %siz>1
    end
    
    % show results
    if OptionLS.verbose==1
        showphi(I, bladder)
    end

end

function flag = intersection(connInit, connReg)
% check if initioalization is inside of connect region
    siz=connInit.NumObjects;
    numInt=0;
    for i=1:siz
        if ~isempty(intersect(connInit.PixelIdxList{i},connReg)) 
            numInt=numInt+1;
        end
    end
    if (numInt/siz)>0.6
        flag=1;
    else
        flag=0;
    end
end

function [seg, flag]=findConn(connInit,temp,segB)
    siz=temp.NumObjects; %-- obtain the number of element
    flag=0;
    seg=segB;
    j=1;
    %-- find the connective element that include the initialization
    while flag==0 && j<=siz
        if intersection(connInit,temp.PixelIdxList{j})
            seg=zeros(size(segB));
            seg(temp.PixelIdxList{j})=1;
            flag=1;
        end %intersection
        j=j+1;
    end %while
end