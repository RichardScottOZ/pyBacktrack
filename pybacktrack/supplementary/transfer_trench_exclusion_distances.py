import math
import pygplates

#
# Script to transfer exclusion distances of paleobathymetry grid points from present day trenches.
#
# Many of these trenches have had their default exclusion distances (set via 'generate_present_day_trenches.py')
# manually updated (thanks Nicky Wright) on a per-trench basis.
# However, when transitioning from the Muller 2019 ('src' model) reconstruction model to Zahirovic 2022 ('dst' model),
# some present day trench locations are in slightly different positions. So we cannot just use the old trenches
# (with the manually set exclusion distances). Instead this script will transfer those exclusion distances from the
# 'src' model to the 'dst' model based on proximity. This avoids having to manually transfer them (in GPlates).
#

src_trench_filename = 'bundle_data/reconstruction/2019_v2/trenches.gpmlz'
dst_trench_filename = 'bundle_data/reconstruction/Z22/trenches.gpmlz'

src_trench_features = pygplates.FeatureCollection(src_trench_filename)
dst_trench_features = pygplates.FeatureCollection(dst_trench_filename)

# Sample point uniformly along each src and dst trench line.
uniform_spacing_radians = math.radians(0.5)

for dst_trench_feature in dst_trench_features:
    dst_trench_line = dst_trench_feature.get_geometry()
    dst_trench_points = dst_trench_line.to_uniform_points(uniform_spacing_radians)

    closest_src_to_dst_distance = float('inf')
    closest_src_trench_feature = None
    # Go through all src trenches to find the closest one to the current dst trench.
    for src_trench_feature in src_trench_features:
        src_trench_line = src_trench_feature.get_geometry()
        src_trench_points = src_trench_line.to_uniform_points(uniform_spacing_radians)

        # Find the average distance of each corresponding uniform point (between src and dst).
        min_num_points = min(len(src_trench_points), len(dst_trench_points))
        src_to_dst_distance = 0.0
        for index in range(min_num_points):  # Common points
            src_to_dst_distance += pygplates.GeometryOnSphere.distance(src_trench_points[index], dst_trench_points[index])
        if len(src_trench_points) > len(dst_trench_points):
            # Points only in src trench are tested against last point in dst trench.
            for index in range(min_num_points, len(src_trench_points)):
                src_to_dst_distance += pygplates.GeometryOnSphere.distance(src_trench_points[index], dst_trench_points[-1])
            src_to_dst_distance /= len(src_trench_points)
        else:
            # Points only in dst trench are tested against last point in src trench.
            for index in range(min_num_points, len(dst_trench_points)):
                src_to_dst_distance += pygplates.GeometryOnSphere.distance(src_trench_points[-1], dst_trench_points[index])
            src_to_dst_distance /= len(dst_trench_points)
        
        # Is the current src trench the closest so far (to the current dst trench).
        if src_to_dst_distance < closest_src_to_dst_distance:
            closest_src_to_dst_distance = src_to_dst_distance
            closest_src_trench_feature = src_trench_feature
    
    # Transfer the exclusion distance parameters from src to dst trenches.
    dst_trench_feature.set_shapefile_attribute(
        'exclude_subducting_distance_to_trenches_kms',
        closest_src_trench_feature.get_shapefile_attribute('exclude_subducting_distance_to_trenches_kms'))
    dst_trench_feature.set_shapefile_attribute(
        'exclude_overriding_distance_to_trenches_kms',
        closest_src_trench_feature.get_shapefile_attribute('exclude_overriding_distance_to_trenches_kms'))

# Overwrite the dst trench features.
dst_trench_features.write(dst_trench_filename)
