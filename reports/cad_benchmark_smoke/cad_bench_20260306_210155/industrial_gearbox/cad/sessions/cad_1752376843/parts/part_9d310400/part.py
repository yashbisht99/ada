from build123d import *
import math
PARAMS = {"width_mm": 80.0, "depth_mm": 40.0, "height_mm": 12.0, "thickness_mm": 2.0, "diameter_mm": 19.360000000000003, "radius_mm": 9.680000000000001, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 0.0, "lip_height_mm": 2.0, "shaft_diameter_mm": 8.8, "bore_diameter_mm": 6.6000000000000005, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 32.912000000000006, "cross_hole_diameter_mm": 2.9040000000000004, "rib_count": 2.0}

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
    outer_r = max(radius, diameter * 0.5, 4.0)
    body_len = max(height, width * 0.5, 8.0)
    Cylinder(radius=outer_r, height=body_len)

    with Locations((0, 0, 0)):
        Cylinder(radius=max(bore_diameter * 0.5, 1.0), height=body_len * 1.2, mode=Mode.SUBTRACT)

    with Locations((0, 0, 0)):
        Box(max(outer_r * 1.7, 4.0), max(thickness * 0.8, 1.2), body_len * 1.1, mode=Mode.SUBTRACT)

    z_off = max(body_len * 0.25, 1.5)
    for z_pos in (-z_off, z_off):
        with Locations((0, 0, z_pos)):
            Box(max(outer_r * 1.2, 3.0), max(hole_diameter, 1.4), max(hole_diameter, 1.4), mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_9d310400/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_9d310400/part.step')
