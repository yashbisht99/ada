from build123d import *
import math
PARAMS = {"width_mm": 114.0, "depth_mm": 57.800000000000004, "height_mm": 2.28, "thickness_mm": 2.16, "diameter_mm": 57.0, "radius_mm": 28.5, "hole_diameter_mm": 3.4, "hole_count": 8.0, "vent_slots": 0.0, "lip_height_mm": 2.76, "shaft_diameter_mm": 17.099999999999998, "bore_diameter_mm": 14.25, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 96.89999999999999, "cross_hole_diameter_mm": 8.549999999999999, "rib_count": 2.0}

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
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/servo_wrist_module/cad/sessions/cad_f690f88ab6/parts/part_9a405c68/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/servo_wrist_module/cad/sessions/cad_f690f88ab6/parts/part_9a405c68/part.step')
