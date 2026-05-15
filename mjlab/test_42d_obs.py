"""Test script to verify 42D observation space."""

from mjlab.tasks.registry import load_env_cfg

# Load both configurations
cfg_48d = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2")
cfg_42d = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2-42")

print("=" * 60)
print("Observation Space Comparison")
print("=" * 60)

print("\n48D Configuration (Original):")
print("-" * 60)
actor_terms_48d = cfg_48d.observations["actor"].terms
for term_name in actor_terms_48d.keys():
  print(f"  - {term_name}")

print("\n42D Configuration (New):")
print("-" * 60)
actor_terms_42d = cfg_42d.observations["actor"].terms
for term_name in actor_terms_42d.keys():
  print(f"  - {term_name}")

print("\nRemoved observations:")
print("-" * 60)
removed = set(actor_terms_48d.keys()) - set(actor_terms_42d.keys())
for term_name in removed:
  print(f"  - {term_name}")

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
print(f"48D config has: {len(actor_terms_48d)} observation terms")
print(f"42D config has: {len(actor_terms_42d)} observation terms")
print(f"Removed: {len(removed)} terms (base_lin_vel, base_ang_vel)")
print("=" * 60)
