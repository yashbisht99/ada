from build123d import *
import math
PARAMS = {"width_mm": 24.0, "depth_mm": 17.0, "height_mm": 30.0, "thickness_mm": 2.0, "diameter_mm": 12.0, "radius_mm": 6.0, "hole_diameter_mm": 3.4, "hole_count": 4.0, "vent_slots": 0.0, "lip_height_mm": 2.0, "shaft_diameter_mm": 9.6, "bore_diameter_mm": 3.0, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 20.4, "cross_hole_diameter_mm": 1.7999999999999998, "rib_count": 2.0}

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

    bearing_bore = max(shaft_diameter * 0.58, bore_diameter * 0.5, 2.0)
    with Locations((0, 0, 0)):
        Cylinder(radius=bearing_bore, height=max(height * 1.2, 4.0), mode=Mode.SUBTRACT)

    x_off = max(width * 0.28, 4.0)
    y_off = max(depth * 0.28, 4.0)
    for x_pos in (-x_off, x_off):
        for y_pos in (-y_off, y_off):
            with Locations((x_pos, y_pos, 0)):
                Cylinder(radius=max(hole_diameter * 0.45, 1.0), height=max(height * 1.2, 4.0), mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/servo_wrist_module/cad/sessions/cad_f690f88ab6/parts/part_a02cab71/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/servo_wrist_module/cad/sessions/cad_f690f88ab6/parts/part_a02cab71/part.step')
