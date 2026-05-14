"""Convert Go2 URDF to MJCF XML with named collision geometries."""

import mujoco

# Load URDF
urdf_path = (
  "/home/y/ece489/lab4/mjlab/src/mjlab/asset_zoo/robots/unitree_go2/xmls/go2.urdf"
)
spec = mujoco.MjSpec.from_file(urdf_path)

# Compile to get the model
model = spec.compile()

# Name all collision geometries based on their body
# Track counts per body to handle multiple geoms per body
body_geom_counts = {}
for i, geom in enumerate(spec.geoms):
  if geom.name == "":  # Unnamed geometry
    # Find the parent body
    body = geom.parent
    if body and body.name:
      # Track how many geoms this body has
      body_name = body.name
      if body_name not in body_geom_counts:
        body_geom_counts[body_name] = 0
      else:
        body_geom_counts[body_name] += 1

      # Create a unique name
      if body_geom_counts[body_name] == 0:
        geom.name = f"{body_name}_collision"
      else:
        geom.name = f"{body_name}_collision{body_geom_counts[body_name]}"
      print(f"Named geom {i}: {geom.name}")

# Save as XML
output_path = (
  "/home/y/ece489/lab4/mjlab/src/mjlab/asset_zoo/robots/unitree_go2/xmls/go2.xml"
)
xml_string = spec.to_xml()
with open(output_path, "w") as f:
  f.write(xml_string)
print(f"\nSaved MJCF XML to: {output_path}")

# Verify the conversion
print("\nVerifying collision geometries:")
spec_check = mujoco.MjSpec.from_file(output_path)
collision_geoms = [
  g.name for g in spec_check.geoms if "collision" in g.name or "foot" in g.name
]
print(f"Found {len(collision_geoms)} collision geometries:")
for name in sorted(collision_geoms):
  print(f"  - {name}")
