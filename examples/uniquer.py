"""This python 3 script searches a .lst file and creates a duplicate file where
each bus name is unique. File name is currently hard coded
"""
import re

# make sure to escape characters when required by re module
# done this way because I'm not sure which special characters are not allowed
# by openPDC, and may need to add more later
spec = r'[&,-]+' # include any special characters, e.g. '&' and '-' that should be removed from bus names

name_counts = {} # hold each bus name and its count
f = open("WECC_OSI_out.lst", "r+")
fd = open("WECC_OSI_out-cor.lst", "w") # corrected file
for line in f:
    if "$\\theta\\" in line:
        # get bus name
        fields = line.split(",")
        theta_name = fields[1].strip()
        name = theta_name[6:]
        if re.search(spec, name): # if name contains invalid characters
            new_name = re.sub(spec, "", name) # remove special characters in spec from name
            line = re.sub(name, new_name, line)
            name = new_name
        if name in name_counts:
            line = re.sub(name, name + "_" + str(name_counts[name]), line) # replace name
            name_counts[name] += 1
        else:
            name_counts[name] = 1
    fd.write(line)
