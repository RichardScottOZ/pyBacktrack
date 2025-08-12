The Zahirovic et al. (2022) reconstruction model was obtained from https://zenodo.org/records/13899315 .

To help avoid the 260 character maximum (absolute) path length limit on Windows:
* The base folder "Zahirovic_etal_2022_GDJ/" was renamed to "Z22/".
* "Z22/Global_EarthByte_GPlates_PresentDay_StaticPlatePolygons.shp" was renamed to "Z22/static_polygons.shp".

The rift start/end time 5 minute grids were generated with 'pybacktrack/supplementary/generate_rift_grids.py' using the Zahirovic et al. (2022) deforming model to find
when deformation started and ended on submerged continental crust inside extensional deforming areas. A default rifting period of 200-0Ma was used
for non-extensional deforming areas. And non-deforming continental crust locations use the rift period from nearest location in deforming regions.

The files "subducting_boundaries.gpmlz" and "trenches.gpmlz" are used to avoid paleo bathymetry gridding near deep ocean trench locations.
These were generated with 'pybacktrack/supplementary/generate_present_day_trenches.py' using the Zahirovic et al. (2022) model.
Each trench contains a distance on the subducting side (defaults to 60km) and a distance the overriding side (defaults to 0km) of trench.
Grid points within these distances are excluded.
Some trench distances have been manually modified on a per-trench basis for better results.
