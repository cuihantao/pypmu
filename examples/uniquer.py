"""This python 3 script searches a .lst file and creates a duplicate file where
each bus name is unique. File name is currently hard coded
"""
import re

name_counts = {} # hold each bus name and its count
f = open("WECC_OSI_out.lst", "r+")
fd = open("WECC_OSI_out-cor.lst", "w") # corrected file
for line in f:
    if "$\\theta\\" in line:
        # get bus name
        fields = line.split(",")
        theta_name = fields[1].strip()
        name = theta_name[6:]
        if name in name_counts:
            line = re.sub(name, name + "_" + str(name_counts[name]), line) # replace name 
            name_counts[name] += 1
        else:
            name_counts[name] = 1
    fd.write(line)
