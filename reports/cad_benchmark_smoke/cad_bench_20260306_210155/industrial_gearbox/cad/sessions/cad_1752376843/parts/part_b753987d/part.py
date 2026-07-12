from build123d import *
import math
PARAMS = {"width_mm": 80.0, "depth_mm": 40.0, "height_mm": 8.0, "thickness_mm": 6.0, "diameter_mm": 30.800000000000004, "radius_mm": 15.400000000000002, "hole_diameter_mm": 3.2, "hole_count": 4.0, "vent_slots": 0.0, "lip_height_mm": 6.0, "shaft_diameter_mm": 8.8, "bore_diameter_mm": 6.16, "gear_teeth": 24.0, "gear_module": 2.0, "flange_diameter_mm": 52.36000000000001, "cross_hole_diameter_mm": 4.62, "rib_count": 2.0}

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
    outer_r = max(radius, diameter * 0.5, 6.0)
    gear_thickness = max(thickness, 3.0)
    Cylinder(radius=outer_r, height=gear_thickness)

    ring_r = max(outer_r * 0.72, 4.0)
    with Locations((0, 0, 0)):
        Cylinder(radius=ring_r, height=max(gear_thickness * 0.65, 1.2), mode=Mode.SUBTRACT)

    hub_r = max(bore_diameter * 0.75, outer_r * 0.24, 2.5)
    Cylinder(radius=hub_r, height=gear_thickness)

    tooth_count = max(8, min(gear_teeth, 64))
    tooth_r = max(outer_r * 0.08, 1.2)
    with PolarLocations(radius=max(outer_r * 0.92, 1.0), count=tooth_count):
        Cylinder(radius=tooth_r, height=max(gear_thickness * 0.65, 1.2))

    spoke_count = max(3, min(8, tooth_count // 4))
    with PolarLocations(radius=max(outer_r * 0.45, 1.5), count=spoke_count):
        Cylinder(radius=max(outer_r * 0.14, 1.4), height=gear_thickness * 1.2, mode=Mode.SUBTRACT)

    with Locations((0, 0, 0)):
        Cylinder(radius=max(bore_diameter * 0.5, 0.8), height=gear_thickness * 1.3, mode=Mode.SUBTRACT)
result_part = p.part
assert result_part.volume > 0, 'Generated part has zero volume.'
assert result_part.is_valid, 'Generated geometry is invalid.'
export_stl(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_b753987d/part.stl')
export_step(result_part, r'/Users/yashbisht/ada_v2-main/reports/cad_benchmark_smoke/cad_bench_20260306_210155/industrial_gearbox/cad/sessions/cad_1752376843/parts/part_b753987d/part.step')
