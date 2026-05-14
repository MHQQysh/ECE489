"""Quick test script to verify evaluation system is working."""

import sys

import torch

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg


def test_cpg_controller():
  """Test CPG controller basic functionality."""
  print("Testing CPG Controller...")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"
  controller = CPGController(
    num_envs=4,
    device=device,
    gait="trot",
    frequency=2.0,
  )

  # Test action generation
  actions = controller.compute_actions(dt=0.02)
  assert actions.shape == (4, 12), f"Expected shape (4, 12), got {actions.shape}"

  # Test reset
  controller.reset(torch.tensor([0, 2], device=device))

  # Test frequency change
  controller.set_frequency(2.5)

  print("✅ CPG Controller test passed!")
  return True


def test_environment_loading():
  """Test environment loading."""
  print("\nTesting Environment Loading...")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Test flat terrain
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 2
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  obs, _ = env.reset()
  if isinstance(obs, dict):
    print(f"  Observation groups: {list(obs.keys())}")
    print(f"  Actor obs shape: {obs['actor'].shape}")
  else:
    print(f"  Observation shape: {obs.shape}")

  # Test step
  actions = torch.zeros(2, 12, device=device)
  obs, reward, terminated, truncated, info = env.step(actions)

  print("✅ Environment loading test passed!")
  return True


def test_cpg_in_environment():
  """Test CPG controller in environment."""
  print("\nTesting CPG in Environment...")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 2
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  # Create CPG controller
  controller = CPGController(
    num_envs=2,
    device=device,
    gait="trot",
    frequency=2.0,
  )

  # Reset
  obs, _ = env.reset()
  controller.reset()

  # Run for a few steps
  for step in range(10):
    actions = controller.compute_actions(dt=env.step_dt)
    obs, reward, terminated, truncated, info = env.step(actions)

    if step == 0:
      print(f"  Step {step}: action range [{actions.min():.3f}, {actions.max():.3f}]")

  print("✅ CPG in environment test passed!")
  return True


def test_metrics_computation():
  """Test metrics computation functions."""
  print("\nTesting Metrics Computation...")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Test velocity tracking error
  actual_vel = torch.randn(100, 3, device=device)
  target_vel = torch.ones(100, 3, device=device)

  from mjlab.scripts.evaluate_controller import compute_velocity_tracking_error

  error = compute_velocity_tracking_error(actual_vel, target_vel)
  print(f"  Velocity tracking error: {error:.4f} m/s")

  # Test body stability
  from mjlab.scripts.evaluate_controller import compute_body_stability

  # Create random quaternions (not normalized, just for testing)
  orientations = torch.randn(100, 4, device=device)
  orientations = orientations / orientations.norm(dim=1, keepdim=True)

  roll_rms, pitch_rms = compute_body_stability(orientations)
  print(f"  Roll RMS: {roll_rms:.4f} rad, Pitch RMS: {pitch_rms:.4f} rad")

  # Test CoT
  from mjlab.scripts.evaluate_controller import compute_cost_of_transport

  torques = torch.randn(100, 12, device=device) * 10
  joint_vels = torch.randn(100, 12, device=device) * 2
  cot = compute_cost_of_transport(
    torques, joint_vels, dt=0.02, mass=15.0, distance=10.0
  )
  print(f"  Cost of Transport: {cot:.4f}")

  print("✅ Metrics computation test passed!")
  return True


def main():
  """Run all tests."""
  print("=" * 60)
  print("Evaluation System Test Suite")
  print("=" * 60)

  tests = [
    ("CPG Controller", test_cpg_controller),
    ("Environment Loading", test_environment_loading),
    ("CPG in Environment", test_cpg_in_environment),
    ("Metrics Computation", test_metrics_computation),
  ]

  passed = 0
  failed = 0

  for name, test_func in tests:
    try:
      if test_func():
        passed += 1
    except Exception as e:
      print(f"❌ {name} test failed: {e}")
      failed += 1
      import traceback

      traceback.print_exc()

  print("\n" + "=" * 60)
  print(f"Test Results: {passed} passed, {failed} failed")
  print("=" * 60)

  if failed > 0:
    print("\n⚠️  Some tests failed. Please check the errors above.")
    sys.exit(1)
  else:
    print("\n✅ All tests passed! Evaluation system is ready to use.")
    print("\nNext steps:")
    print("1. Train your RL policy: uv run train Mjlab-Velocity-Flat-Unitree-Go2")
    print(
      "2. Run evaluation: uv run python src/mjlab/scripts/evaluate_controller.py --help"
    )
    print("3. Or use automated script: ./scripts/run_evaluation.sh")
    sys.exit(0)


if __name__ == "__main__":
  main()
