"""Add visual meshes to Go2 XML."""

xml_path = (
  "/home/y/ece489/lab4/mjlab/src/mjlab/asset_zoo/robots/unitree_go2/xmls/go2.xml"
)

# Read current XML
with open(xml_path, "r") as f:
  content = f.read()

# Add compiler meshdir and asset section with meshes
new_header = """<mujoco model="go2_description">
  <compiler angle="radian" meshdir="assets"/>

  <asset>
    <mesh name="trunk" file="trunk.stl"/>
    <mesh name="hip" file="hip.stl"/>
    <mesh name="thigh" file="thigh.stl"/>
    <mesh name="thigh_mirror" file="thigh_mirror.stl"/>
    <mesh name="calf" file="calf.stl"/>
  </asset>
"""

content = content.replace(
  '<mujoco model="go2_description">\n  <compiler angle="radian"/>', new_header
)

# Add visual geom to base body (trunk)
content = content.replace(
  '      <geom name="base_collision" size="0.1881 0.04675 0.057" type="box" rgba="1 1 1 1"/>',
  """      <geom name="base_visual" type="mesh" mesh="trunk" contype="0" conaffinity="0" group="2"/>
      <geom name="base_collision" size="0.1881 0.04675 0.057" type="box" rgba="1 1 1 1"/>""",
)

# Add visual geoms to hip bodies
for leg in ["FL", "FR", "RL", "RR"]:
  content = content.replace(
    f'      <geom name="{leg}_hip_collision"',
    f'      <geom name="{leg}_hip_visual" type="mesh" mesh="hip" contype="0" conaffinity="0" group="2"/>\n      <geom name="{leg}_hip_collision"',
  )

# Add visual geoms to thigh bodies (FL and RL use thigh_mirror, FR and RR use thigh)
for leg in ["FL", "RL"]:
  content = content.replace(
    f'        <geom name="{leg}_thigh_collision"',
    f'        <geom name="{leg}_thigh_visual" type="mesh" mesh="thigh_mirror" contype="0" conaffinity="0" group="2"/>\n        <geom name="{leg}_thigh_collision"',
  )

for leg in ["FR", "RR"]:
  content = content.replace(
    f'        <geom name="{leg}_thigh_collision"',
    f'        <geom name="{leg}_thigh_visual" type="mesh" mesh="thigh" contype="0" conaffinity="0" group="2"/>\n        <geom name="{leg}_thigh_collision"',
  )

# Add visual geoms to calf bodies
for leg in ["FL", "FR", "RL", "RR"]:
  content = content.replace(
    f'          <geom name="{leg}_calf_collision" size',
    f'          <geom name="{leg}_calf_visual" type="mesh" mesh="calf" contype="0" conaffinity="0" group="2"/>\n          <geom name="{leg}_calf_collision" size',
  )

# Write back
with open(xml_path, "w") as f:
  f.write(content)

print("✓ Added visual meshes to Go2 XML")
print("✓ Meshes: trunk, hip, thigh, thigh_mirror, calf")
