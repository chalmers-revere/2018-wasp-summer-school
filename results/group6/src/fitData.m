%% input data

filename = 'data.txt';
delimiter = ' ';
formatSpec = '%f%f%[^\n\r]';

% Open the text file.
fileID = fopen(filename,'r');
dataArray = textscan(fileID, formatSpec, 'Delimiter', delimiter, 'MultipleDelimsAsOne', true, 'TextType', 'string',  'ReturnOnError', false);
h = dataArray{:, 1};
d = dataArray{:, 2};
h = h(100:end);
d = d(100:end);
dinv = 1./d;
fclose(fileID);

clearvars filename delimiter formatSpec fileID dataArray ans;

%% Process data
p = polyfit(h,dinv,2)
x = 0.1*(0:1:180);
y = polyval(p,x);

figure
plot(h, dinv); hold on;
plot(x, y)
