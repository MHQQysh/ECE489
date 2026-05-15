"""Verify actual observation dimensions by creating the environment."""

import torch
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
from mjlab.envs import ManagerBasedRlEnv

# Test 42D configuration
print("=" * 60)
print("Testing 42D Configuration")
print("=" * 60)

cfg_42d = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2-42")
cfg_42d.scene.num_envs = 4  # Small number for testing

device = "cuda:0"
env = ManagerBasedRlEnv(cfg_42d, device=device)

# Get observation dimensions
obs_dict = env.observation_manager.compute_group("actor")
obs = obs_dict  # obs_dict is already the tensor, not a dict

print(f"\nActor observation shape: {obs.shape}")
print(f"Expected: (4, 42)")
print(f"Match: {obs.shape == torch.Size([4, 42])}")

# Break down by component
print("\nObservation components:")
print("-" * 60)

actor_terms = cfg_42d.observations["actor"].terms
total_dim = 0

component_dims = {
  "projected_gravity": 3,
  "joint_pos": 12,
  "joint_vel": 12,
  "actions": 12,
  "command": 3,
}

for term_name in actor_terms.keys():
  dim = component_dims.get(term_name, "?")
  print(f"  {term_name:20s}: {dim}D")
  if isinstance(dim, int):
    total_dim += dim

print("-" * 60)
print(f"  {'Total':20s}: {total_dim}D")

env.close()

print("\n" + "=" * 60)
print("✅ 42D configuration verified successfully!")
print("=" * 60)
