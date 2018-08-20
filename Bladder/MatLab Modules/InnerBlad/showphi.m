function showphi(I, phi)
% show curve evolution of phi 
    temp= zeros(size(I));
    seg=(phi>0)+0;
    for i=1:1:size(I,3)
        Z=I(:,:,i)/(max(max(max(I))));
        temp(:,:,i) = rgb2gray(imoverlay(Z, bwperim(seg(:,:,i)), [1 1 1]));
        %temp(:,:,i) = rgb2gray(imoverlay(Z, seg(:,:,i), [1 1 1]));
    end
    figure(1),clf
    imshow3D(temp)     
    title('Level Set Segmentation'); 
    drawnow;
end