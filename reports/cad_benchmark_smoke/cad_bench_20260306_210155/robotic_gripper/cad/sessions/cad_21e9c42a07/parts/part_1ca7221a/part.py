from build123d import *
import math
PARAMS = {"width_mm": 11.05, "depth_mm": 11.05, "height_mm": 52.5, "thickness_mm": 1.56, "diameter_mm": 11.05, "radius_mm": 5.525, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 0.0, "lip_height_mm": 2.0, "shaft_diameter_mm": 4.0, "bore_diameter_mm": 2.7625, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 22.1, "cross_hole_diameter_mm": 3.0940000000000003, "rib_count": 2.0}

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
    shaft_len = max(height, max(width, depth))
    shaft_r = max(shaft_diameter * 0.5, 2.0)
    Cylinder(radius=shaft_r, height=shaft_len)

    flange_r = max(flange_diameter * 0.5, shaft_r * 1.4)
    with Locations((0, 0, shaft_len * 0.32)):
        Cylinder(radius=flange_r, height=max(thickness, 1.6))

    if bore_diameter > 0:
        with Locations((0, 0, 0)):
            Cylinder(radius=max(bore_diameter * 0.5, 0.8), height=shaft_len * 1.1, mode=Mode.SUBTRACT)

    if cross_hole_diameter > 0:
        with Locations((0, 0, 0)):
            Box(
                max(shaft_r * 2.2, 4.0),
                max(cross_hole_diameter, 1.2),
                max(cross_hole_diameter, 1.2),
                mode=Mode.SUBTRACT,
            )
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_1ca7221a/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/robotic_gripper/cad/sessions/cad_21e9c42a07/parts/part_1ca7221a/part.step')
