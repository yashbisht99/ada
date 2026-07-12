from build123d import *
import math
PARAMS = {"width_mm": 107.8, "depth_mm": 68.6, "height_mm": 2.25, "thickness_mm": 2.25, "diameter_mm": 53.9, "radius_mm": 26.95, "hole_diameter_mm": 3.2, "hole_count": 8.0, "vent_slots": 0.0, "lip_height_mm": 3.0, "shaft_diameter_mm": 16.169999999999998, "bore_diameter_mm": 13.475, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 91.63, "cross_hole_diameter_mm": 8.084999999999999, "rib_count": 2.0}

width = PARAMS['width_mm']
depth = PARAMS['depth_mm']
height = PARAMS['height_mm']
thickness = PARAMS['thickness_mm']
diameter = PARAMS['diameter_mm']
radius = PARAMS['radius_mm']
hole_diameter = PARAMS['hole_diameter_mm']
hole_count = int(PARAMS['hole_count'])
vent_slots = int(PARAMS['vent_slots'])
lip_height = PARAMS['lip_height_mm']
shaft_diameter = PARAMS['shaft_diameter_mm']
bore_diameter = PARAMS['bore_diameter_mm']
gear_teeth = int(PARAMS['gear_teeth'])
gear_module = PARAMS['gear_module']
flange_diameter = PARAMS['flange_diameter_mm']
cross_hole_diameter = PARAMS['cross_hole_diameter_mm']
rib_count = int(PARAMS['rib_count'])

with BuildPart() as p:
    plate_thickness = max(1.6, thickness)
    Box(width, depth, plate_thickness)

    inner_w = max(width - 2 * max(1.5, thickness), 6)
    inner_d = max(depth - 2 * max(1.5, thickness), 6)
    with Locations((0, 0, -lip_height * 0.5)):
        Box(inner_w, inner_d, max(lip_height, 2.0))

    x_off = max(6.0, width * 0.36)
    y_off = max(6.0, depth * 0.3)
    corners = [(-x_off, -y_off), (x_off, -y_off), (-x_off, y_off), (x_off, y_off)]
    for x_pos, y_pos in corners[: max(1, min(hole_count, 4))]:
        with Locations((x_pos, y_pos, 0)):
            Cylinder(
                radius=max(hole_diameter * 0.5, 1.2),
                height=max(plate_thickness + lip_height + 2.0, 3.0),
                mode=Mode.SUBTRACT,
            )
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_4d8389a4/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_4d8389a4/part.step')
