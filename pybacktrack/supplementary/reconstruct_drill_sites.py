import csv
import numpy as np
import os
import os.path
import pybacktrack
import pygplates
import sys

#
# To install the above dependencies with conda:
#   conda create -n <conda-environment> -c conda-forge numpy pybacktrack pygplates
#   conda activate <conda-environment>
# ...where <conda-environment> should be replaced with the name of your conda environment.
#


# Required pygplates version.
# Need version 0.29 to use 'default_anchor_plate_id' argument for RotationModel.
PYGPLATES_VERSION_REQUIRED = pygplates.Version(29)

def reconstruct_drill_sites(
        drill_site_files,           # sequence of drill site filenames
        rotation_features_or_model, # any combination of rotation features and files; or a rotation model
        static_polygon_features,    # any combination of features, feature collection and files
        output_filenames,
        end_time,
        start_time = 0,
        time_increment = 1,
        anchor_plate_id=0):
    """Reconstruct the present-day location of one or more drill sites.
    
    Read in one or more drill sites and reconstruct each drill site location
    (by assigning a plate ID using static polygons and reconstructing using rotation files)
    through a range of times (but not older than the age of the oldest stratigraphic layer at the drill site)
    and output the reconstructed lon/lat locations to text files (a separate file for each drill site).
    """
    
    # Check the imported pygplates version.
    if pygplates.Version.get_imported_version() < PYGPLATES_VERSION_REQUIRED:
        raise RuntimeError('Using pygplates version {0} but version {1} or greater is required'.format(
                pygplates.Version.get_imported_version(), PYGPLATES_VERSION_REQUIRED))

    if len(output_filenames) != len(drill_site_files):
        raise ValueError('Number of output files must match number of input drill site files.')

    # Read all the bundled lithologies ("primary" and "extended").
    lithologies = pybacktrack.read_lithologies_files(pybacktrack.BUNDLE_LITHOLOGY_FILENAMES)

    # Rotation model.
    rotation_model = pygplates.RotationModel(rotation_features_or_model, default_anchor_plate_id=anchor_plate_id)

    # Static polygons partitioner used to assign plate IDs to the drill sites.
    plate_partitioner = pygplates.PlatePartitioner(static_polygon_features, rotation_model)


    # Iterate over the drill sites.
    for file_index, drill_site_filename in enumerate(drill_site_files):
        
        # Read drill site file to get the site location.
        drill_site = pybacktrack.read_well_file(
            drill_site_filename,
            lithologies,
            well_attributes={
                'SiteLongitude': ('longitude', float),  # read 'SiteLongitude' into 'drill_site.longitude'
                'SiteLatitude': ('latitude', float)})   # read 'SiteLatitude' into 'drill_site.latitude'
        
        # Check drill site has stratigraphic layers.
        if not drill_site.stratigraphic_units:
            print('Not reconstructing drill site because it has no stratigraphic layers: "{}"'.format(drill_site_filename))
            continue
        
        # Age of bottom of drill site.
        drill_site_age = drill_site.stratigraphic_units[-1].bottom_age;
        
        if start_time > drill_site_age:
            print('Not reconstructing drill site because "start_time" is older than oldest drilled section: "{}"'.format(drill_site_filename))
            continue
        
        # Time range to reconstruct.
        # We don't reconstruct older than the (bottom) age of the oldest stratigraphic layer in the drill site.
        # Note: Using 1e-6 to ensure the end time gets included (if it's an exact multiple of the time increment, which it likely will be).
        time_range = [float(time) for time in np.arange(start_time, min(end_time, drill_site_age) + 1e-6, time_increment)]
        
        #print('Reconstructing drill site "{}" at location ({}, {})'.format(drill_site_filename, drill_site.longitude, drill_site.latitude))
        
        # Present day location of drill site.
        drill_site_location = pygplates.PointOnSphere(drill_site.latitude, drill_site.longitude)
        
        # Assign a plate ID to the drill site based on its location.
        partitioning_plate = plate_partitioner.partition_point(drill_site_location)
        if not partitioning_plate:
            # Not contained by any plates. Shouldn't happen since static polygons have global coverage,
            # but might if there's tiny cracks between polygons.
            raise ValueError('Unable to assign plate ID. Drill site does not intersect the static polygons.')
        drill_site_plate_id = partitioning_plate.get_feature().get_reconstruction_plate_id()
        
        # Output filename.
        drill_site_output_filename = output_filenames[file_index]
        
        # Open the output drill file for writing.
        with open(drill_site_output_filename, 'w', newline='') as drill_site_output_file:
            # Write the header information.
            drill_site_output_file.write('#' + os.linesep)
            drill_site_output_file.write('# Site file: {}'.format(os.path.basename(drill_site_output_filename)) + os.linesep)  # site filename
            drill_site_output_file.write('# Site longitude: {}'.format(drill_site.longitude) + os.linesep)  # site longitude
            drill_site_output_file.write('# Site latitude: {}'.format(drill_site.latitude) + os.linesep)  # site longitude
            drill_site_output_file.write('#' + os.linesep)
            
            # Reconstruct the drill site and write reconstructed locations to output file.
            drill_site_output_writer = csv.writer(drill_site_output_file, delimiter=' ')
            for time in time_range:
                # Get rotation from present day to current time using the drill site plate ID.
                rotation = rotation_model.get_rotation(time, drill_site_plate_id, from_time=0)
                
                # Reconstruct drill site to current time.
                reconstructed_drill_site_location = rotation * drill_site_location
                reconstructed_drill_site_latitude, reconstructed_drill_site_longitude = reconstructed_drill_site_location.to_lat_lon()
                
                # Write reconstructed location to output file.
                drill_site_output_writer.writerow((reconstructed_drill_site_longitude, reconstructed_drill_site_latitude, time))


if __name__ == '__main__':
    
    ########################
    # Command-line parsing #
    ########################
    
    import argparse

    # Suffix to append to each input drill site filename if user does not specify output filenames.
    DEFAULT_OUTPUT_FILENAME_SUFFIX = "_reconstructed"
    
    
    def main():
        
        __description__ = """Reconstruct the present-day location of one or more drill sites.
    
    Read in one or more drill sites and reconstruct each drill site location
    (by assigning a plate ID using static polygons and reconstructing using rotation files)
    through a range of times (but not older than the age of the oldest stratigraphic layer at the drill site)
    and output the reconstructed lon/lat locations to text files (a separate file for each drill site, either
    specified on command-line or, if not specified, then matching drill site filename with '{}' suffix appended).
    
    NOTE: Separate the positional and optional arguments with '--' (workaround for bug in argparse module).
    For example...

    python reconstruct_drill_sites.py ... -- drill_site.txt
    """.format(DEFAULT_OUTPUT_FILENAME_SUFFIX)

        def parse_positive_integer(value_string):
            try:
                value = int(value_string)
            except ValueError:
                raise argparse.ArgumentTypeError("%s is not an integer" % value_string)
            
            if value <= 0:
                raise argparse.ArgumentTypeError("%g is not a positive integer" % value)
            
            return value
    
        #
        # Gather command-line options.
        #
        
        # The command-line parser.
        parser = argparse.ArgumentParser(description=__description__, formatter_class=argparse.RawDescriptionHelpFormatter)
        
        # Rotation filenames.
        parser.add_argument('-r', '--rotation_filenames',
            required=True, type=str, nargs='+', metavar='rotation_filename',
            help='One or more rotation files.')
        
        # Static polygon filenames.
        parser.add_argument('-p', '--static_polygon_filenames',
            required=True, type=str, nargs='+', metavar='static_polygon_filename',
            help='One or more static polygon files.')
        
        # Time range and increment.
        parser.add_argument('-s', '--start_time',
            type=float, default=0,
            help='The start of the time range (youngest time). Defaults to 0Ma.')
        parser.add_argument('-e', '--end_time',
            required=True, type=float,
            help='The end of the time range (oldest time).')
        parser.add_argument('-i', '--time_increment',
            type=float, default = 1,
            help='The increment of the time range. Defaults to 1Myr.')
    
        parser.add_argument('-a', '--anchor', type=parse_positive_integer, default=0,
                dest='anchor_plate_id',
                help='Anchor plate id used when reconstructing drill site locations. Defaults to zero.')
        
        parser.add_argument('-o', '--output_filenames',
            type=str, nargs='+', metavar='output_filename',
            help='One or more output files containing the reconstructed drill site outputs. '
                 'If not specified, then each output filename matches each input drill site filename with the "{}" suffix appended. '
                 'If specified, then the number of output files must match the number of input drill site files '
                 '(the order written to output files will match the order read from input files).'
                 .format(DEFAULT_OUTPUT_FILENAME_SUFFIX))
        
        parser.add_argument('drill_site_filenames',
            type=str, nargs='+', metavar='drill_site_filename',
            help='One or more drill site files.')
        
        # Parse command-line options.
        args = parser.parse_args()

        if not args.output_filenames:
            output_filenames = []
            for drill_site_filename in args.drill_site_filenames:
                # Each output filename is the associated input drill site filename appended with the default suffix.
                output_base_filename, output_ext = os.path.splitext(drill_site_filename)
                output_filename = output_base_filename + DEFAULT_OUTPUT_FILENAME_SUFFIX + output_ext
                output_filenames.append(output_filename)
        else:
            output_filenames = args.output_filenames
        
        # Reconstruct the present-day location of one or more drill sites.
        reconstruct_drill_sites(
            args.drill_site_filenames,
            args.rotation_filenames,
            args.static_polygon_filenames,
            output_filenames,
            args.end_time,
            args.start_time,
            args.time_increment,
            args.anchor_plate_id)


    import traceback
    
    try:
        main()
        sys.exit(0)
    except Exception as exc:
        print('ERROR: {0}'.format(exc), file=sys.stderr)
        # Uncomment this to print traceback to location of raised exception.
        #traceback.print_exc()
        sys.exit(1)
