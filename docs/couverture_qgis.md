# Couverture des propriétés QGIS par les catalogues

Produit par `outils/entrainement/couverture.py` avec QGIS 3.44.12-Solothurn. Ne pas modifier à la main.

- **convertie** : décrite par un catalogue ;
- **ignorée** : listée dans `ignorer.json`, perdue **sans être signalée** (à relire : certaines changent le dessin) ;
- **non couverte** : perdue, signalée dans le rapport en « info ».
Total : 97 convertie(s), 57 ignorée(s), 10 non couverte(s), 18 type(s) de couche absent(s).


## CentroidFill (« Centroid Fill »)

- **convertie** (2) : `point_on_all_parts`, `point_on_surface`
- **ignorée** (2) : `clip_on_current_part_only`, `clip_points`
- **non couverte** (0) : —

## FontMarker (« Font Marker »)

- **convertie** (14) : `angle`, `chr`, `color`, `font`, `font_style`, `horizontal_anchor_point`, `offset`, `offset_unit`, `outline_color`, `outline_width`, `outline_width_unit`, `size`, `size_unit`, `vertical_anchor_point`
- **ignorée** (4) : `joinstyle`, `offset_map_unit_scale`, `outline_width_map_unit_scale`, `size_map_unit_scale`
- **non couverte** (0) : —

## LinePatternFill (« Line Pattern Fill »)

- **convertie** (6) : `angle`, `coordinate_reference`, `distance`, `distance_unit`, `offset`, `offset_unit`
- **ignorée** (9) : `clip_mode`, `color`, `distance_map_unit_scale`, `line_width`, `line_width_map_unit_scale`, `line_width_unit`, `offset_map_unit_scale`, `outline_width_map_unit_scale`, `outline_width_unit`
- **non couverte** (0) : —

## MarkerLine (« Marker Line »)

- **convertie** (8) : `interval`, `interval_unit`, `offset`, `offset_along_line`, `offset_along_line_unit`, `offset_unit`, `placements`, `rotate`
- **ignorée** (6) : `average_angle_length`, `average_angle_map_unit_scale`, `average_angle_unit`, `interval_map_unit_scale`, `offset_along_line_map_unit_scale`, `offset_map_unit_scale`
- **non couverte** (2) : `place_on_every_part`, `ring_filter`

## PointPatternFill (« Point Pattern Fill »)

- **convertie** (18) : `angle`, `clip_mode`, `coordinate_reference`, `displacement_x`, `displacement_x_unit`, `distance_x`, `distance_x_unit`, `distance_y`, `distance_y_unit`, `offset_x`, `offset_x_unit`, `offset_y`, `offset_y_unit`, `random_deviation_x`, `random_deviation_x_unit`, `random_deviation_y`, `random_deviation_y_unit`, `seed`
- **ignorée** (11) : `displacement_x_map_unit_scale`, `displacement_y_map_unit_scale`, `displacement_y_unit`, `distance_x_map_unit_scale`, `distance_y_map_unit_scale`, `offset_x_map_unit_scale`, `offset_y_map_unit_scale`, `outline_width_map_unit_scale`, `outline_width_unit`, `random_deviation_x_map_unit_scale`, `random_deviation_y_map_unit_scale`
- **non couverte** (1) : `displacement_y`

## RasterFill (« Raster Image Fill »)

- **convertie** (5) : `angle`, `coordinate_mode`, `imageFile`, `width`, `width_unit`
- **ignorée** (3) : `offset_map_unit_scale`, `offset_unit`, `width_map_unit_scale`
- **non couverte** (3) : `alpha`, `height`, `offset`

## RasterMarker (« Raster Image Marker »)

- **convertie** (4) : `angle`, `imageFile`, `size`, `size_unit`
- **ignorée** (7) : `fixedAspectRatio`, `horizontal_anchor_point`, `offset_map_unit_scale`, `offset_unit`, `scale_method`, `size_map_unit_scale`, `vertical_anchor_point`
- **non couverte** (2) : `alpha`, `offset`

## SimpleFill (« Simple Fill »)

- **convertie** (9) : `color`, `joinstyle`, `offset`, `offset_unit`, `outline_color`, `outline_style`, `outline_width`, `outline_width_unit`, `style`
- **ignorée** (2) : `border_width_map_unit_scale`, `offset_map_unit_scale`
- **non couverte** (0) : —

## SimpleLine (« Simple Line »)

- **convertie** (17) : `capstyle`, `customdash`, `customdash_unit`, `dash_pattern_offset`, `dash_pattern_offset_unit`, `joinstyle`, `line_color`, `line_style`, `line_width`, `line_width_unit`, `offset`, `offset_unit`, `trim_distance_end`, `trim_distance_end_unit`, `trim_distance_start`, `trim_distance_start_unit`, `use_custom_dash`
- **ignorée** (8) : `align_dash_pattern`, `customdash_map_unit_scale`, `dash_pattern_offset_map_unit_scale`, `offset_map_unit_scale`, `trim_distance_end_map_unit_scale`, `trim_distance_start_map_unit_scale`, `tweak_dash_pattern_on_corners`, `width_map_unit_scale`
- **non couverte** (2) : `draw_inside_polygon`, `ring_filter`

## SimpleMarker (« Simple Marker »)

- **convertie** (14) : `angle`, `color`, `horizontal_anchor_point`, `name`, `offset`, `offset_unit`, `outline_color`, `outline_style`, `outline_width`, `outline_width_unit`, `scale_method`, `size`, `size_unit`, `vertical_anchor_point`
- **ignorée** (5) : `cap_style`, `joinstyle`, `offset_map_unit_scale`, `outline_width_map_unit_scale`, `size_map_unit_scale`
- **non couverte** (0) : —

## Types de couches de symboles sans équivalent dans les catalogues

- AnimatedMarker (« Animated Marker »)
- ArrowLine (« Arrow »)
- EllipseMarker (« Ellipse Marker »)
- FilledLine (« Filled Line »)
- FilledMarker (« Filled Marker »)
- GeometryGenerator (« Geometry Generator »)
- GradientFill (« Gradient Fill »)
- HashLine (« Hashed Line »)
- InterpolatedLine (« Interpolated Line »)
- LinearReferencing (« Linear Referencing »)
- Lineburst (« Lineburst »)
- MaskMarker (« Mask »)
- RandomMarkerFill (« Random Marker Fill »)
- RasterLine (« Raster Line »)
- SVGFill (« SVG Fill »)
- ShapeburstFill (« Shapeburst Fill »)
- SvgMarker (« SVG Marker »)
- VectorField (« Vector Field Marker »)
