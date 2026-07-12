from build123d import *
import math
PARAMS = {"width_mm": 49.6, "depth_mm": 4.2, "height_mm": 9.8, "thickness_mm": 3.1500000000000004, "diameter_mm": 24.8, "radius_mm": 12.4, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 6.0, "lip_height_mm": 3.1500000000000004, "shaft_diameter_mm": 7.4399999999999995, "bore_diameter_mm": 6.2, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 42.16, "cross_hole_diameter_mm": 3.7199999999999998, "rib_count": 2.0}

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
    Box(width, depth, height)
    count = max(1, min(vent_slots, 24))
    slot_w = max(1.4, thickness * 0.55)
    span = max(depth * 0.82, slot_w)
    step = span / max(1, count)
    for idx in range(count):
        y_pos = -span * 0.5 + (idx + 0.5) * step
        with Locations((0, y_pos, 0)):
            Box(max(width * 0.86, 6.0), slot_w, max(height * 0.9, 2.0), mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/control_enclosure/cad/sessions/cad_609eca7f9f/parts/part_570d52c5/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/control_enclosure/cad/sessions/cad_609eca7f9f/parts/part_570d52c5/part.step')
