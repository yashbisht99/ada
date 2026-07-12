from build123d import *
import math
PARAMS = {"width_mm": 54.6, "depth_mm": 7.0, "height_mm": 31.9, "thickness_mm": 2.16, "diameter_mm": 27.3, "radius_mm": 13.65, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 0.0, "lip_height_mm": 2.16, "shaft_diameter_mm": 8.19, "bore_diameter_mm": 6.825, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 46.41, "cross_hole_diameter_mm": 4.095, "rib_count": 3.0}

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
    Box(width, depth, max(thickness, 1.8))
    count = max(1, min(rib_count, 12))
    if count == 1:
        with Locations((0, 0, height * 0.5)):
            Box(max(thickness, 1.8), depth, max(height, 4.0))
    else:
        span = max(width * 0.8, thickness)
        step = span / (count - 1)
        for idx in range(count):
            x_pos = -span * 0.5 + (idx * step)
            with Locations((x_pos, 0, height * 0.5)):
                Box(max(thickness, 1.8), depth, max(height, 4.0))
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_704ffa7c/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_704ffa7c/part.step')
