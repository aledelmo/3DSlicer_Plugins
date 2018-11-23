function VF_fixed = find_anchors(VF,land_ijk,dist)
    
    %Input: 
    %VF: list of vertices and faces of the mesh
    %land_ijk: user selected landmarks
    %dist: distance anchoring (pixels) parameter
    
    %Output:
    %VF_fixed: index of the fixed anchors of the mesh
    
    diff_matrix = zeros(length(VF.vertices),length(land_ijk));

    for i=1:length(land_ijk)
    
    diff= VF.vertices - land_ijk(i,:);
    diff2 = diff.*diff;
    diff3 = sum(diff2,2);
    diff_eucl = diff3.^(0.5);
    
    diff_matrix(:,i) = diff_eucl;
    
    end
    
    min_matrix = min(diff_matrix,[],2);
    VF_fixed = find(min_matrix < dist);

end