function argswrite(returnParameterFilename, args)
% Write return values specified in the args structure to the return parameter text file

% open file for writing text file (create new)
fid=fopen(returnParameterFilename, 'wt+');
assert(fid > 0, ['Could not open output file:' returnParameterFilename]);

argsCellArr = struct2cell(args);

% Get string names for each field in the meta data
fields = fieldnames(args);

% Print the header data to the output file
for i=1:numel(fields)
  fprintf(fid,fields{i});
  fprintf(fid,' = ');
  % Print as a row vector (scalar vectors are not written correctly if they are stored in a column vector)
  [valueRows valueColumns]=size(argsCellArr{i});
  if (valueRows==1)
      value=argsCellArr{i};
  else
      value=argsCellArr{i}';
  end
  fprintf(fid,num2str(value));
  fprintf(fid,'\n');
end

fclose(fid);
