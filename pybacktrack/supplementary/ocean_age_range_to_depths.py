
#
# Copyright (C) 2025 The University of Sydney, Australia
#
# This program is free software; you can redistribute it and/or modify it under
# the Free Software Foundation.
# the terms of the GNU General Public License, version 2, as published by
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

#
# Script to convert a range of ages (in Ma, in 1 Myr increments) to
# basement depth (metres) using a specific oceanic age/depth model.
#
# This is similar to using "age_to_depth_cli"
# (see "python -m pybacktrack.age_to_depth_cli --help")
# but instead of requiring an input file containing the desired ages
# it uses uniform ages across an age range (which saves having to
# generate those into a file just to use "age_to_depth_cli").
#
# This script both prints out to console and writes to a text file
# (one age column and one depth column).
# You can comment out either one if you like.
#
# You can change the oceanic model using 'model', the age range
# using 'oldest_age' and the output filename using 'output_filename'.
#

import pybacktrack
import numpy as np

## Input parameters ##

oldest_age = 300

model = pybacktrack.AGE_TO_DEPTH_MODEL_RHCW18
#model = pybacktrack.AGE_TO_DEPTH_MODEL_GDH1
#model = pybacktrack.AGE_TO_DEPTH_MODEL_CROSBY_2007

output_filename = 'age_depth_RHCW18.txt'
#output_filename = 'age_depth_GDH1.txt'
#output_filename = 'age_depth_CROSBY_2007.txt'

######################


age_range = np.arange(oldest_age + 0.1)

# Convert ages to depths.
ages_and_depths = []
# Print header.
print('{}'.format(
    '# {0:<20}{1:<20}'.format('age', 'depth').rstrip(' ')))
for age in age_range:
    depth = pybacktrack.convert_age_to_depth(age, model)
    
    ages_and_depths.append((age, depth))
    
    # Print age and depth.
    print('  {}'.format(
            '{0:<20.3f}{1:<20.3f}'.format(age, depth).rstrip(' ')))

# Save age and depth to output file.
with open(output_filename, 'w') as output_file:
    # Write 'age depth' header.
    output_file.write('{}\n'.format(
            '# {0:<20}{1:<20}'.format('age', 'depth').rstrip(' ')))
    
    for age, depth in ages_and_depths:
        # Write age and depth.
        output_file.write('  {}\n'.format(
                '{0:<20.3f}{1:<20.3f}'.format(age, depth).rstrip(' ')))
