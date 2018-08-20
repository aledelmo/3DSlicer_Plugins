%BILATERAL3   Fast bilateral filtering of 3D images.
%   This is an implementation of fast bilateral filtering for 3D images.
%   This filter smoothes the image while preserving edges, but in its most
%   straighforward implementation is very computationally demanding,
%   especially with large 3D images. Fast bilateral filtering (S. Paris and
%   F. Durand, MIT) is an approximation technique which drastically
%   improves the speed of computation. This implementation follows the
%   Matlab version of the 2D filter[1] with some modifications.
%   
%   sigmaSxy and sigmaSz - spatial smoothing parameters (standard
%   deviation of the Gaussian kernel)
%   sigmaR - the smoothing parameter in the "range" dimension
%   samS - the amount of downsampling performed by the fast
%   approximation in the spatial dimensions (x,y). In z direction, it is
%   derived from spatial sigmas and samS.
%   samR - the amount of downsampling in the "range" dimension.
%   verbose - optional, for debugging
%
%   [1] http://people.csail.mit.edu/jiawen/software/bilateralFilter.m
%
%   Written by Igor Solovey, 2011
%   isolovey@engmail.uwaterloo.ca
%   Acknowledgements: 2D implementations of Jiawen Chen, Oleg Michailovich
%   Version 1, March 21 2011
%   
%Notes:
% - the internal function, BILATERAL3I, allows you to vary all parameters,
%   if you want to.
% - spatial sigmas are assumed to be in the units of "pixel".
% - range sigma is assumed to be in the units of range values whose
% minimum is 0 and maximum is 255 (i.e. 8-bit).

function Ibf=bilateral3(I, sigmaSxy,sigmaSz,sigmaR,samS,samR,verbose)
if ~exist('verbose','var'), verbose=0; end
I=range1(double(I),255);
%simplification #1
%smoothing and subsampling in x and y spatial directions is equal
sigmaSx=sigmaSxy;
sigmaSy=sigmaSxy;
samSx=samS;
samSy=samS;

%simplification #2
% obtain samSz by assuming samSz/samS=sigmaSz/sigmaSxy
c=sigmaSz/sigmaSxy;
samSz=ceil(c*samS);

%optional simpilification #3:
% obtain samR by assuming samS/sigmaS = samR/sigmaR
if ~exist('samR','var')
    samR = sigmaR*samS/sigmaSxy;
end

%re-scale sigmaR, samR to normalize them ( [0, 255] --> [0, 1] )
% samR has to be such that 1/samR is an integer
%e.g. if supplied samR is 12 (divide range [0,255] into bins of size 12):
%
%normalize: samR=12/256=0.0469;
%1/samR=21.3333 ~=22 bins (round up).
%the new samR = 1/22 = 0.0455;
%later on, when samR is used, 1/samR will yield the number of range bins, 22.
sigmaR  = sigmaR/256;
samR    = 1/ceil(256/samR);

%for debugging purposes:
if verbose
    displ('sigmaSx',sigmaSx);
    displ('sigmaSy',sigmaSy);
    displ('sigmaSz',sigmaSz);
    displ('sigmaR',sigmaR);
    displ('samSx',samSx);
    displ('samSy',samSy);
    displ('samSz',samSz);
    displ('samR',samR);
    disp(['{' n2s(size(I,1)) ',' n2s(size(I,2)) ',' n2s(size(I,3)) ...
        ',256} --> {' n2s(ceil(size(I,1)/samSx)) ',' n2s(ceil(size(I,2)/samSy)) ...
        ',' n2s(ceil(size(I,3)/samSz)) ',' n2s(1/samR) '}']);
end

%run the filter
Ibf=bilateral3i(I,sigmaSx,sigmaSy,sigmaSz,sigmaR,samSx,samSy,samSz,samR);
end

function Ibf=bilateral3i(I,sigmaSx,sigmaSy,sigmaSz,sigmaR,samSx,samSy,samSz,samR)
I=double(I);
[N M P]=size(I);

%find the number of bins in each spatial dimension
Xbins=ceil(N/samSx);
Ybins=ceil(M/samSy);
Zbins=ceil(P/samSz);


Np=Xbins*samSx;
Mp=Ybins*samSy;
Pp=Zbins*samSz;

Xrem=ceil((Np-N)/2);
Yrem=ceil((Mp-M)/2);
Zrem = ceil((Pp-P)/2);

%zero-pad the image as symmetrically as possible to
%attain a size divisible by the subsample rate
Ip = padarray(I,[Xrem Yrem Zrem],0);
I = Ip(1:Np,1:Mp,1:Pp);

clear Ip

%%%%%
% 1. subsampling in spatial domain
%
% quantize intensity values
% a) map the image I onto a range [0,1].
% b) map the image I onto a range [0,1/sR].
% c) round the values to obtain an image Iq in which each pixel value
% Iq(x0) represents the range bin to which x0 belongs.
Iq=round((I-min(I(:)))/range(I(:))/samR);

%what bin does each pixel belong to, based on its x,y,z coordinate?
[X Y Z]=ndgrid(1:Np,1:Mp,1:Pp);
binX=floor((X-1)/samSx)+1;
binY=floor((Y-1)/samSy)+1;
binZ=floor((Z-1)/samSz)+1;
clear X Y Z
%find which range bin each location in the x-y-z-range space belongs to
binW=repmat(reshape(1:samSx*samSy*samSz,[samSx samSy samSz]),[Xbins,Ybins Zbins]);

D=zeros(Xbins,Ybins,Zbins,samSx*samSy*samSz);
W=D;
D(sub2ind(size(D),binX(:),binY(:),binZ(:),binW(:)))=I(:);
W(sub2ind(size(D),binX(:),binY(:),binZ(:),binW(:)))=Iq(:);

clear Iq binX binY binZ binW

%- W represents which 4D bin each data point belongs to
%- D represents what the actual value of each data point is*
%both contain values oriented according to coordinate system:
%(subsampled-x,subsampled-y,subsampled-z,location-in-bin)
%- the ordering of values along the 4th dimension no longer matters after
%this point.

%* (D is simply the input image I suitably rearranged. numel(D)=numel(I).)
%if I was a 2D image of size 12 by 12, and bin size in X and Y was 3 pixels
%each,constructing D would amount to breaking the image into 3-by-3 chunks,
%then taking the 9 pixels in each chunk and arranging them in a vector,
%placing these vectors next to each other to create a 4-by-4-by-9
%rearrangement of I.

GData       =zeros(Xbins,Ybins,Zbins,1/samR);
GWeights    =zeros(Xbins,Ybins,Zbins,1/samR);

%for each range bin:
for k=1:(1/samR)
    %find the indices of pixels belonging to this range bin
    tmp  = (W==k);
    %make a copy of D but zero out all values except those belonging to
    %k-th bin
    tmp2 = zeros(size(D));
    tmp2(tmp)=D(tmp);
    %GWeights will contain the number of pixels in k-th range bin for each
    %x-y-z bin
    GWeights(:,:,:,k) = sum(tmp,4);
    %And GData will contain the sum of their values
    GData(:,:,:,k)    = sum(tmp2,4);
end

%2. Smoothing with gaussians
hSx=gkernel(sigmaSx/samSx);
hSy=gkernel(sigmaSy/samSy);
hSz=gkernel(sigmaSz/samSz);
hR=gkernel(sigmaR/samR);

GWeights=convnsep({hSx,hSy,hSz,hR},GWeights,'same');
GData=convnsep({hSx,hSy,hSz,hR},GData,'same');

%calculate coordinates in the non-subsampled X-Y-Z-Range plain
%to which filtered bin values belong
[n m p k]=size(GData);
Xloc=repmat(linspace(1,n,Np)',[1 Mp Pp]);
Yloc=repmat(linspace(1,m,Mp), [Np 1 Pp]);
Zloc=repmat(shiftdim(linspace(1,p,Pp),-1),   [Np Mp 1]);
Rloc=(I-min(I(:)))/range(I(:))*(1/samR-1)+1;

%compute the pixel values that will go to locations computed above
Indx=GWeights~=0;
Data=zeros(size(GData));
Data(Indx)=GData(Indx)./GWeights(Indx);

clear GData GWeights Indx

%At this point, values at evenly spaced locations Xloc,Yloc,Zloc are 
%known (stored in Data), but for the rest of the image they are unknown.
%Interpolation will find them.

Ibf=interpn(Data,Xloc,Yloc,Zloc,Rloc);

clear Data Xloc Yloc Zloc Rloc

%remove zero-padding
Ibf=Ibf(Xrem+1:N+Xrem,Yrem+1:M+Yrem,Zrem+1:P+Zrem);
end



%Auxiliary functions:

%displaying variable value
function displ(name,val)
disp([name '=' n2s(val) ';']);
end

%shorthand for num2str
function S = n2s(N,f)
if N~=fix(N)
    if ~exist('f','var'),S=num2str(N,'%4.2f');
    elseif f==0
        S=num2str(N);
    else
        S=num2str(N,f);
    end
else
    S=num2str(N);
end
end

%make a gaussian kernel
function [h,L] = gkernel(sd)
L=ceil(3.5*sd);
h=exp(-0.5*((-L:L)'/sd).^2);
h=h/sum(h);
end

function Y = range1(x,rg)
if ~exist('rg','var'),rg=1;end
Y=1/range(x(:))*(x-min(x(:)))*rg;
end

function y = range(x)
y=max(x)-min(x);
end


function J = convnsep(h,V,type)
%CONVNSEP   Separable N-dimensional convolution.
%   C = CONVNSEP(h,V) performs an N-dimensional convolution or matrix V
%   with N kernels defined in the cell array h.
%   C = CONVNSEP(h,V,'shape') controls the size of the output. (See help
%   for Matlab's CONVN function).
%   Example: create a random 4-D array, convolve it with 4 kernels of
%   various lengths:
%   h={[1 -2 1], [-1 1 -1 1 -1],[1 -2 1],[1]};
%   V = convnsep(h,randn([32,32,32,32]));
%   See also CONVN, CONV, CONV2
%
%   Written by Igor Solovey, 2010
%   isolovey@uwaterloo.ca
%
%   Version 1.1, February 26, 2011
%   TODO: fix handling of even-sized kernels
lh=length(h);

%input validation
assert(lh==ndims(V),'The number of kernels does not match the array dimensionality.');

L=nan(1,lh);
for j=1:lh,
    L(j)=(length(h{j})-1)/2;
end
V=padarray(V,L);
J = convnsepsame(h,V);

%implicit behaviour: if no 'type' input, then type=='full' (don't trim the
%result)
if nargin>2
    switch type
        case 'full'
            %do nothing
        case 'valid'
            J=trimarray(J,L*2);
        case 'same'
            J=trimarray(J,L);
        otherwise
    end
end

end


function J = convnsepsame(h,V)
%Perform convolution while keeping the array size the same (i.e. discarding
%boundary samples)
J=V;
sz=size(V);
n=length(sz);
indx2=nan(1,n);
for k=1:n
    %dimensions other k-th dimension, along which convolution will happen:
    otherdims = 1:n; otherdims(k)=[];
    
    % permute order: place k-th dimension as 1st, followed by all others:
    indx1=[k otherdims];
    
    % inverse permute order:
    indx2(indx1)=1:n;
    
    %perform convolution along k-th dimension:
    %
    %1. permute dimensions to place k-th dimension as 1st
    J = permute(J,indx1);
    %2. create a 2D array (i.e. "stack" all other dimensions, other than
    %k-th:
    J = reshape(J,sz(k),prod(sz(otherdims)));
    %3. perform 2D convolution with k-th kernel along the first dimension
    J = conv2(h{k},1,J,'same');
    %4. undo the "flattening" of step 2
    J = reshape(J,sz(indx1));
    %5. undo the permutation of step 1.
    J = permute(J,indx2);
end
end

%extract only the central portion of the array V, based on kernels whose
%lengths are defined in L
function V = trimarray(V,L)
str='';
for j=1:ndims(V)
    str=[str num2str(L(j)+1) ':' num2str(size(V,j)-L(j)) ','];
end
str=str(1:end-1); %remove last coma

eval(['V=V(' str ');']);
end
