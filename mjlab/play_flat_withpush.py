"""Play script showing push recovery test visually with force arrow visualization."""

import torch
import numpy as np

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.velocity.config.go2 import unitree_go2_flat_env_cfg
from mjlab.tasks.registry import load_rl_cfg
from dataclasses import asdict
from typing_extensions import override

from mjlab.viewer.viser.viewer import ViserPlayViewer


class PushRecoveryViewer(ViserPlayViewer):
  """ViserPlayViewer with manual velocity and push controls."""

  def __init__(
    self,
    env,
    policy,
    push_force_x: float = 0.0,
    push_force_y: float = 100.0,
    push_duration: float = 0.3,
    **kwargs,
  ):
    super().__init__(env, policy, **kwargs)
    self.command_vx = 0.0
    self.command_vy = 0.0
    self.command_wz = 0.0
    self.push_force_x = push_force_x
    self.push_force_y = push_force_y
    self.push_duration = push_duration
    self._pending_push = False
    self._push_active = False
    self._push_start_time = None

  def _set_command(self):
    env = self.env.unwrapped
    cmd = torch.zeros((1, 3), device=env.device)
    cmd[0, 0] = float(self.command_vx)
    cmd[0, 1] = float(self.command_vy)
    cmd[0, 2] = float(self.command_wz)
    env.command_manager.command_vel = cmd

  @override
  def setup(self) -> None:
    super().setup()

    if hasattr(self._scene, "debug_visualization_enabled"):
      self._scene.debug_visualization_enabled = True

    # Manual velocity controls
    with self._server.gui.add_folder("Manual Velocity Control"):
      self._server.gui.add_text(
        "Set the desired command velocity, then use Apply Command.", initial_value=""
      )
      self._vx_slider = self._server.gui.add_slider(
        "Target Vx (m/s)", min=-1.5, max=1.5, step=0.05, initial_value=0.0
      )
      self._vy_slider = self._server.gui.add_slider(
        "Target Vy (m/s)", min=-1.5, max=1.5, step=0.05, initial_value=0.0
      )
      self._wz_slider = self._server.gui.add_slider(
        "Target Wz (rad/s)", min=-2.0, max=2.0, step=0.05, initial_value=0.0
      )
      self._apply_cmd_button = self._server.gui.add_button("Apply Command")
      self._reset_cmd_button = self._server.gui.add_button("Reset Command")

      @self._apply_cmd_button.on_click
      def _apply_cmd(_):
        self.command_vx = self._vx_slider.value
        self.command_vy = self._vy_slider.value
        self.command_wz = self._wz_slider.value
        print(
          f"[CMD] vx={self.command_vx:.2f} m/s, vy={self.command_vy:.2f} m/s, wz={self.command_wz:.2f} rad/s"
        )

      @self._reset_cmd_button.on_click
      def _reset_cmd(_):
        self.command_vx = 0.0
        self.command_vy = 0.0
        self.command_wz = 0.0
        self._vx_slider.value = 0.0
        self._vy_slider.value = 0.0
        self._wz_slider.value = 0.0
        print("[CMD] Reset to zero.")

    # Push recovery controls
    with self._server.gui.add_folder("Push Recovery Test"):
      self._server.gui.add_text(
        "Choose force direction and magnitude, then click Apply Push.", initial_value=""
      )
      self._push_dir_button = self._server.gui.add_button_group(
        "Push Direction",
        options=["+X (Forward)", "-X (Backward)", "+Y (Left)", "-Y (Right)"],
      )
      self._apply_push_button = self._server.gui.add_button("Apply Push!")
      self._reset_push_button = self._server.gui.add_button("Reset Push")
      self._force_x_slider = self._server.gui.add_slider(
        "Push Force X (N)", min=-200.0, max=200.0, step=10.0, initial_value=0.0
      )
      self._force_y_slider = self._server.gui.add_slider(
        "Push Force Y (N)", min=-200.0, max=200.0, step=10.0, initial_value=100.0
      )
      self._duration_slider = self._server.gui.add_slider(
        "Push Duration (s)", min=0.1, max=0.5, step=0.05, initial_value=0.3
      )

      @self._push_dir_button.on_click
      def _set_dir(event):
        mapping = {
          "+X (Forward)": (1.0, 0.0),
          "-X (Backward)": (-1.0, 0.0),
          "+Y (Left)": (0.0, 1.0),
          "-Y (Right)": (0.0, -1.0),
        }
        fx, fy = mapping[event.target.value]
        self._force_x_slider.value = fx * abs(self._force_y_slider.value or 100.0)
        self._force_y_slider.value = fy * abs(self._force_y_slider.value or 100.0)

      @self._apply_push_button.on_click
      def _apply_push(_):
        self.push_force_x = self._force_x_slider.value
        self.push_force_y = self._force_y_slider.value
        self.push_duration = self._duration_slider.value
        self._pending_push = True
        print(
          f"[PUSH] Push queued! Fx={self.push_force_x:.0f}N, Fy={self.push_force_y:.0f}N, Duration={self.push_duration:.2f}s"
        )

      @self._reset_push_button.on_click
      def _reset_push(_):
        self._push_active = False
        self._push_start_time = None
        self._clear_force()
        if self._scene:
          self._scene.clear()
        print("[PUSH] Reset!")

  def _clear_force(self):
    """Clear external force."""
    env = self.env.unwrapped
    robot = env.scene["robot"]
    env_ids = torch.tensor([0], device=env.device)
    force = torch.zeros((1, 1, 3), device=env.device)
    torque = torch.zeros((1, 1, 3), device=env.device)
    robot.write_external_wrench_to_sim(force, torque, env_ids=env_ids, body_ids=[0])

  def _apply_force(self):
    """Apply external force to robot root."""
    env = self.env.unwrapped
    robot = env.scene["robot"]
    env_ids = torch.tensor([0], device=env.device)
    force = torch.zeros((1, 1, 3), device=env.device)
    torque = torch.zeros((1, 1, 3), device=env.device)
    force[0, 0, 0] = self.push_force_x
    force[0, 0, 1] = self.push_force_y
    robot.write_external_wrench_to_sim(force, torque, env_ids=env_ids, body_ids=[0])

  def _draw_force_arrow(self):
    """Draw force arrow using scene's arrow method."""
    if self._scene is None:
      return

    env = self.env.unwrapped
    robot = env.scene["robot"]
    pos = robot.data.root_link_pos_w[0].cpu().numpy()

    force_vec = np.array([float(self.push_force_x), float(self.push_force_y), 0.0])
    force_mag = float(np.linalg.norm(force_vec))
    if force_mag < 1e-6:
      return

    arrow_length = force_mag / 50.0
    arrow_length = min(max(arrow_length, 0.4), 2.0)
    direction = force_vec / force_mag
    start = pos.copy()
    end = pos + direction * arrow_length

    self._scene.add_arrow(start, end, color=(1.0, 0.2, 0.2, 1.0), width=0.04)

  @override
  def _execute_step(self) -> bool:
    """Override to apply push force before each step."""
    env = self.env.unwrapped

    self._set_command()

    # Handle pending push
    if self._pending_push and not self._push_active:
      self._push_start_time = self._step_count
      self._push_active = True
      self._pending_push = False
      print(
        f"[PUSH] Activating push now! Fx={self.push_force_x:.0f}N, Fy={self.push_force_y:.0f}N"
      )

    # Apply push force if active
    if self._push_active:
      steps_for_duration = int(self.push_duration / env.step_dt)
      current_step = self._step_count - self._push_start_time

      if current_step < steps_for_duration:
        self._apply_force()
        self._draw_force_arrow()
      else:
        self._clear_force()
        self._push_active = False
        if self._scene:
          self._scene.clear()
        print("[PUSH] Push ended, recovering...")

    # Call parent implementation
    return super()._execute_step()


def main():
  device = "cuda"
  flat_model = "logs/rsl_rl/go2_velocity/flat_1000/model_999.pt"

  env_cfg = unitree_go2_flat_env_cfg()
  env_cfg.scene.num_envs = 1
  env_cfg.events.pop("push_robot", None)
  if "command_vel" in env_cfg.curriculum:
    del env_cfg.curriculum["command_vel"]

  # Disable auto-resampling by setting very long resampling time
  env_cfg.commands["twist"].resampling_time_range = (999999.0, 999999.0)
  # Disable standing envs and forward envs (they override manual commands)
  env_cfg.commands["twist"].rel_standing_envs = 0.0
  env_cfg.commands["twist"].rel_forward_envs = 0.0

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(
    env, clip_actions=load_rl_cfg("Mjlab-Velocity-Flat-Unitree-Go2").clip_actions
  )
  runner = MjlabOnPolicyRunner(
    env, asdict(load_rl_cfg("Mjlab-Velocity-Flat-Unitree-Go2")), device=device
  )
  runner.load(flat_model, load_cfg={"actor": True}, strict=True)
  policy = runner.get_inference_policy(device=device)

  print("=" * 60)
  print("Push Recovery Demo")
  print("=" * 60)
  print("- Use the Manual Velocity Control panel to set vx/vy/wz")
  print("- Click 'Apply Command' to update the target command")
  print("- Then use Push Recovery Test to choose force direction and magnitude")
  print("- Click 'Apply Push!' to test recovery under the chosen command")
  print("=" * 60)

  viewer = PushRecoveryViewer(env, policy)
  viewer.run()


if __name__ == "__main__":
  main()
