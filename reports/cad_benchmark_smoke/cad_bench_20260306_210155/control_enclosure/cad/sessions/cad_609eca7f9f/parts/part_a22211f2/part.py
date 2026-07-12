from build123d import *
import math
PARAMS = {"width_mm": 80.0, "depth_mm": 40.0, "height_mm": 35.0, "thickness_mm": 4.2, "diameter_mm": 40.0, "radius_mm": 20.0, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 6.0, "lip_height_mm": 4.2, "shaft_diameter_mm": 12.0, "bore_diameter_mm": 10.0, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 68.0, "cross_hole_diameter_mm": 6.0, "rib_count": 2.0}

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
    inner_w = max(width - 2 * thickness, 4)
    inner_d = max(depth - 2 * thickness, 4)
    inner_h = max(height - thickness, 4)
    with Locations((0, 0, thickness * 0.5)):
        Box(inner_w, inner_d, inner_h, mode=Mode.SUBTRACT)

    post_x = max(5.0, width * 0.36)
    post_y = max(5.0, depth * 0.3)
    for x_pos in (-post_x, post_x):
        for y_pos in (-post_y, post_y):
            with Locations((x_pos, y_pos, -height * 0.25)):
                Cylinder(radius=max(hole_diameter * 0.75, 2.2), height=max(height * 0.5, 6.0))
            with Locations((x_pos, y_pos, -height * 0.2)):
                Cylinder(radius=max(hole_diameter * 0.5, 1.2), height=max(height * 0.6, 6.0), mode=Mode.SUBTRACT)

    slot_count = max(0, min(vent_slots, 18))
    if slot_count > 0:
        slot_width = max(1.6, thickness * 0.55)
        span = max(depth * 0.72, slot_width)
        step = span / max(1, slot_count)
        for idx in range(slot_count):
            y_pos = -span * 0.5 + (idx + 0.5) * step
            with Locations((0, y_pos, height * 0.24)):
                Box(max(width * 0.72, 8.0), slot_width, max(thickness * 0.9, 1.5), mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/control_enclosure/cad/sessions/cad_609eca7f9f/parts/part_a22211f2/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/control_enclosure/cad/sessions/cad_609eca7f9f/parts/part_a22211f2/part.step')
