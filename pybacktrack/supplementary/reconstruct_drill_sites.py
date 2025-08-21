import csv
import numpy as np
import os
import os.path
from pathlib import Path
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
#
# Need version 1.0 to use 'pygplates.ReconstructModel', etc.
PYGPLATES_VERSION_REQUIRED = pygplates.Version(1, 0)

# The default COB features.
DEFAULT_COB_FILENAME = Path(__file__).parent / 'EarthByte_global_COBs_2024.gpmlz'


def reconstruct_drill_sites(
        drill_site_files,           # sequence of drill site filenames
        rotation_features_or_model, # any combination of rotation features and files; or a rotation model
        static_polygon_features,    # any combination of features, feature collection and files
        output_filenames,
        end_time,
        *,
        start_time = 0,
        time_increment = 1,
        anchor_plate_id=0,
        output_distance_to_cobs=False,
        cob_features=DEFAULT_COB_FILENAME):  # any combination of features, feature collection and files
    """Reconstruct the present-day location of one or more drill sites (and optionally calculate distance to COBs).
    
    Read in one or more drill sites and reconstruct each drill site location
    (by assigning a plate ID using static polygons and reconstructing using rotation files)
    through a range of times (but not older than the age of the oldest stratigraphic layer at the drill site)
    and output the reconstructed lon/lat locations and time to text files (a separate file for each drill site).

    Also, optionally calculate distance from each reconstructed drill site location to reconstructed
    continental-oceanic boundaries (COBs) at each time step, and output as a 4th column.
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

    # Prepare to reconstruct all COBs (if we're going to calculate distance to COBs).
    if output_distance_to_cobs:
        cob_reconstruct_model = pygplates.ReconstructModel(cob_features, rotation_model)

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
        drill_site_age = drill_site.stratigraphic_units[-1].bottom_age
        
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

            # Write column headers.
            drill_site_output_file.write('# paleo_longitude  paleo_latitude  time')
            if output_distance_to_cobs:
                drill_site_output_file.write('  distance_to_COBs(kms)')
            drill_site_output_file.write(os.linesep)
            
            # Reconstruct the drill site and write reconstructed locations to output file.
            drill_site_output_writer = csv.writer(drill_site_output_file, delimiter=' ')
            for time in time_range:
                # Get rotation from present day to current time using the drill site plate ID.
                rotation = rotation_model.get_rotation(time, drill_site_plate_id, from_time=0)
                
                # Reconstruct drill site to current time.
                reconstructed_drill_site_location = rotation * drill_site_location
                reconstructed_drill_site_latitude, reconstructed_drill_site_longitude = reconstructed_drill_site_location.to_lat_lon()

                # Calculate nearest distance from reconstructed drill site to all reconstructed COBs (if requested).
                if output_distance_to_cobs:
                    distance_to_all_cobs = None
                    for cob_reconstructed_geometry in cob_reconstruct_model.reconstruct_snapshot(time).get_reconstructed_geometries():
                        # Get the minimum distance from reconstructed drill site location to the current reconstructed COB geometry.
                        distance_to_cob = pygplates.GeometryOnSphere.distance(
                                reconstructed_drill_site_location,
                                cob_reconstructed_geometry.get_reconstructed_geometry(),
                                distance_to_all_cobs)
                        # If the current COB is nearer than all previous COBs.
                        if distance_to_cob is not None:
                            distance_to_all_cobs = distance_to_cob
                    # If there were no reconstructed COBs (for some reason) then set to maximum distance across globe (in radians).
                    if distance_to_all_cobs is None:
                        distance_to_all_cobs = np.pi
                
                # Determine which columns go into the row.
                row = (reconstructed_drill_site_longitude, reconstructed_drill_site_latitude, time)
                if output_distance_to_cobs:
                    # Add distance-to-COBs (in kms) as last column.
                    row = row + (distance_to_all_cobs * pygplates.Earth.mean_radius_in_kms,)
                
                # Write the row to the output file.
                drill_site_output_writer.writerow(row)


if __name__ == '__main__':
    
    ########################
    # Command-line parsing #
    ########################
    
    import argparse

    # Suffix to append to each input drill site filename if user does not specify output filenames.
    DEFAULT_OUTPUT_FILENAME_SUFFIX = "_reconstructed"
    
    
    def main():
        
        __description__ = """Reconstruct the present-day location of one or more drill sites (and optionally calculate distance to COBs).
    
    Read in one or more drill sites and reconstruct each drill site location
    (by assigning a plate ID using static polygons and reconstructing using rotation files)
    through a range of times (but not older than the age of the oldest stratigraphic layer at the drill site)
    and output the reconstructed lon/lat locations and time to text files (a separate file for each drill site, either
    specified on command-line or, if not specified, then matching drill site filename with '{}' suffix appended).

    Also, optionally calculate distance from each reconstructed drill site location to reconstructed
    continental-oceanic boundaries (COBs) at each time step, and output as a 4th column.
    
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
    
        # Basically an argparse.RawDescriptionHelpFormatter that will also preserve formatting of
        # argument help messages if they start with "R|".
        class PreserveHelpFormatter(argparse.RawDescriptionHelpFormatter):
            def _split_lines(self, text, width):
                if text.startswith('R|'):
                    return text[2:].splitlines()
                return super(PreserveHelpFormatter, self)._split_lines(text, width)
    
        #
        # Gather command-line options.
        #
        
        # The command-line parser.
        parser = argparse.ArgumentParser(description=__description__, formatter_class=PreserveHelpFormatter)
    
        # Allow user to override default rotation filenames used to reconstruct the drill site(s).
        #
        # Defaults to the rotations of the default reconstruction model built into pyBacktrack.
        parser.add_argument(
            '-r', '--rotation_filenames', type=str, nargs='+',
            default=pybacktrack.bundle_data.BUNDLE_RECONSTRUCTION_ROTATION_FILENAMES,
            metavar='rotation_filename',
            help='R|One or more rotation files used to reconstruct the drill site(s).\n'
                 'Defaults to the rotations of the default reconstruction model built into pyBacktrack :\n'
                 '{}.\n'
                 .format(pybacktrack.bundle_data.BUNDLE_RECONSTRUCTION_ROTATION_FILENAMES))
        
        # Allow user to override default static polygon filename used to assign plate IDs to the drill site(s).
        #
        # Defaults to the static polygons of the default reconstruction model built into pyBacktrack.
        parser.add_argument(
            '-p', '--static_polygon_filename', type=str,
            default=pybacktrack.bundle_data.BUNDLE_RECONSTRUCTION_STATIC_POLYGON_FILENAME,
            metavar='static_polygon_filename',
            help='R|File containing static polygons used to assign plate IDs to the drill site(s).\n'
                 'Defaults to the static polygons of the default reconstruction model built into pyBacktrack:\n'
                 '"{}".\n'
                 .format(pybacktrack.bundle_data.BUNDLE_RECONSTRUCTION_STATIC_POLYGON_FILENAME))
        
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

        # Optionally output distance to COBs.
        parser.add_argument(
            '-od', '--output_distance_to_cobs', action='store_true',
            help='Optionally calculate distance from each reconstructed drill site location to the reconstructed '
                 'continental-oceanic boundaries (COBs) at each time step, and output as a 4th column.')
        
        parser.add_argument(
            '-cob', '--cob_filenames', type=str, nargs='+',
            metavar='cob_filename',
            help='R|One or more files containing COBs.\n'
                 'Note that this is ignored unless "--output_distance_to_cobs" is also specified.\n'
                 'Defaults to the supplementary COBs in:\n'
                 '"{}".\n'
                 .format(DEFAULT_COB_FILENAME))
        
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

        if args.cob_filenames:
            cob_filenames = args.cob_filenames
        else:
            cob_filenames = DEFAULT_COB_FILENAME

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
            args.static_polygon_filename,
            output_filenames,
            args.end_time,
            start_time=args.start_time,
            time_increment=args.time_increment,
            anchor_plate_id=args.anchor_plate_id,
            output_distance_to_cobs=args.output_distance_to_cobs,
            cob_features=cob_filenames)


    import traceback
    
    try:
        main()
        sys.exit(0)
    except Exception as exc:
        print('ERROR: {0}'.format(exc), file=sys.stderr)
        # Uncomment this to print traceback to location of raised exception.
        #traceback.print_exc()
        sys.exit(1)
