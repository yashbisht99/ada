from build123d import *
import math
PARAMS = {"width_mm": 117.0, "depth_mm": 39.2, "height_mm": 8.0, "thickness_mm": 2.4, "diameter_mm": 58.5, "radius_mm": 29.25, "hole_diameter_mm": 3.2, "hole_count": 8.0, "vent_slots": 0.0, "lip_height_mm": 2.4, "shaft_diameter_mm": 17.55, "bore_diameter_mm": 14.625, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 99.45, "cross_hole_diameter_mm": 8.775, "rib_count": 2.0}

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
    plate_t = max(thickness, 2.0)
    Box(width, depth, plate_t)

    slot_l = max(width * 0.28, 6.0)
    slot_w = max(hole_diameter * 1.4, 2.0)
    x_off = max(width * 0.3, 6.0)
    y_off = max(depth * 0.24, 6.0)
    for x_pos in (-x_off, x_off):
        for y_pos in (-y_off, y_off):
            with Locations((x_pos, y_pos, 0)):
                Box(slot_l, slot_w, plate_t * 1.3, mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_373e0601/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_373e0601/part.step')
