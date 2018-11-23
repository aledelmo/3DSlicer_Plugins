function [point_IJK]=getPoints(filenamePoint,img)
    %read the points file
    point=fcsvRead(filenamePoint);
    
    %convert the point's coordinates
    point_LPS=cli_pointvectordecode(point); %read initilization point
    point_IJK=round(img.ijkToLpsTransform\[point_LPS; ones(1,size(point_LPS,2))]); %convert from lps in ijk
    point_IJK=point_IJK(1:3,:)';
    %point_IJK(:,2:3)=flip(point_IJK(:,2:3),2);
    %point_IJK=flip(point_IJK,2);
end

function point=fcsvRead(filename)
    %read the text file
    pointFile=textread(filename, '%s', 'whitespace',',');
    %detelet the useless information
    pointFile(1:16)=[];
    %reshape
    pointFile=reshape(pointFile,13,numel(pointFile)/13);
    pointFile=pointFile';
    %get only the point's information
    pointFile=pointFile(:,2:4);
    temp={};
    for i=1:size(pointFile,1)
        %getting ready for the use
        temp{i}=[str2double(pointFile(i,1));str2double(pointFile(i,2));str2double(pointFile(i,3))];
    end
    point=temp;
end