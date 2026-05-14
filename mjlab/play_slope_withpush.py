"""Interactive slope-on-slope visualization with manual command and push controls."""

from dataclasses import asdict

import numpy as np
import torch
from typing_extensions import override

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_rl_cfg
from mjlab.tasks.velocity.config.go2 import unitree_go2_terrain_env_cfg
from mjlab.viewer.viser.viewer import ViserPlayViewer


class SlopeOnSlopeViewer(ViserPlayViewer):
  """Viewer for manually testing velocity commands and external pushes on slope terrain."""

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

    with self._server.gui.add_folder("Manual Velocity Control"):
      self._server.gui.add_text(
        "Set vx/vy/wz, then click Apply Command.", initial_value=""
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

    with self._server.gui.add_folder("Push Recovery Test"):
      self._server.gui.add_text(
        "Choose force direction, magnitude and duration, then click Apply Push.",
        initial_value="",
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
        mag = abs(self._force_y_slider.value or 100.0)
        self._force_x_slider.value = fx * mag
        self._force_y_slider.value = fy * mag

      @self._apply_push_button.on_click
      def _apply_push(_):
        self.push_force_x = self._force_x_slider.value
        self.push_force_y = self._force_y_slider.value
        self.push_duration = self._duration_slider.value
        self._pending_push = True
        print(
          f"[PUSH] Queued Fx={self.push_force_x:.0f}N, Fy={self.push_force_y:.0f}N, duration={self.push_duration:.2f}s"
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
    env = self.env.unwrapped
    robot = env.scene["robot"]
    env_ids = torch.tensor([0], device=env.device)
    force = torch.zeros((1, 1, 3), device=env.device)
    torque = torch.zeros((1, 1, 3), device=env.device)
    robot.write_external_wrench_to_sim(force, torque, env_ids=env_ids, body_ids=[0])

  def _apply_force(self):
    env = self.env.unwrapped
    robot = env.scene["robot"]
    env_ids = torch.tensor([0], device=env.device)
    force = torch.zeros((1, 1, 3), device=env.device)
    torque = torch.zeros((1, 1, 3), device=env.device)
    force[0, 0, 0] = self.push_force_x
    force[0, 0, 1] = self.push_force_y
    robot.write_external_wrench_to_sim(force, torque, env_ids=env_ids, body_ids=[0])

  def _draw_force_arrow(self):
    if self._scene is None:
      return

    env = self.env.unwrapped
    robot = env.scene["robot"]
    pos = robot.data.root_link_pos_w[0].cpu().numpy()
    force_vec = np.array([float(self.push_force_x), float(self.push_force_y), 0.0])
    force_mag = float(np.linalg.norm(force_vec))
    if force_mag < 1e-6:
      return

    arrow_length = min(max(force_mag / 50.0, 0.4), 2.0)
    direction = force_vec / force_mag
    self._scene.add_arrow(
      pos.copy(), pos + direction * arrow_length, color=(1.0, 0.2, 0.2, 1.0), width=0.04
    )

  @override
  def _execute_step(self) -> bool:
    env = self.env.unwrapped
    self._set_command()

    if self._pending_push and not self._push_active:
      self._push_start_time = self._step_count
      self._push_active = True
      self._pending_push = False
      print(
        f"[PUSH] Activating now: Fx={self.push_force_x:.0f}N, Fy={self.push_force_y:.0f}N"
      )

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

    return super()._execute_step()


def main():
  device = "cuda"
  slope_model = "/home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-13_22-42-35/model_900.pt"

  env_cfg = unitree_go2_terrain_env_cfg("slope")
  env_cfg.scene.num_envs = 1
  env_cfg.curriculum.pop("terrain_levels", None)
  env_cfg.curriculum.pop("command_vel", None)
  env_cfg.events.pop("push_robot", None)
  env_cfg.commands["twist"].resampling_time_range = (999999.0, 999999.0)
  env_cfg.commands["twist"].rel_standing_envs = 0.0
  env_cfg.commands["twist"].rel_forward_envs = 0.0

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(
    env, clip_actions=load_rl_cfg("Mjlab-Velocity-Slope-Unitree-Go2").clip_actions
  )
  runner = MjlabOnPolicyRunner(
    env, asdict(load_rl_cfg("Mjlab-Velocity-Slope-Unitree-Go2")), device=device
  )
  runner.load(slope_model, load_cfg={"actor": True}, strict=True)
  policy = runner.get_inference_policy(device=device)

  print("=" * 60)
  print("Slope On Slope Demo")
  print("=" * 60)
  print("- Set vx/vy/wz in Manual Velocity Control")
  print("- Click Apply Command to update the target command")
  print("- Use Push Recovery Test to apply a configurable external force")
  print("- This loads the slope-trained checkpoint on the slope terrain config")
  print("=" * 60)

  viewer = SlopeOnSlopeViewer(env, policy)
  viewer.run()


if __name__ == "__main__":
  main()
