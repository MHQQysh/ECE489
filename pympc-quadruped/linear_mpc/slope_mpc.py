"""Slope-specific MPC controller for the Go2 demo.

This controller keeps the flat-terrain MPC unchanged and adds a separate
slope-aware implementation used only by the slope demo.
"""

import time
from typing import Union

import numpy as np
from pydrake.all import MathematicalProgram, Solve
from qpsolvers import solve_qp
from scipy.linalg import expm

from config.linear_mpc_configs import LinearMpcConfig
from config.robot_configs import RobotConfig
from linear_mpc.mpc import ModelPredictiveController
from utils.kinematics import quat2ZYXangle, vec2so3
from utils.robot_data import RobotData


class SlopeModelPredictiveController(ModelPredictiveController):
    """Slope-aware MPC that projects the dynamics into a terrain frame."""

    def __init__(self, mpc_config: LinearMpcConfig, robot_config: RobotConfig, slope_pitch: float, slope_roll: float = 0.0):
        self.slope_pitch = float(slope_pitch)
        self.slope_roll = float(slope_roll)
        super().__init__(mpc_config, robot_config)

    def _load_parameters(self, mpc_config: LinearMpcConfig, robot_config: RobotConfig):
        super()._load_parameters(mpc_config, robot_config)
        self.slope_pitch = getattr(self, "slope_pitch", 0.0)
        self.slope_roll = getattr(self, "slope_roll", 0.0)

    def _terrain_rotation_matrix(self):
        cp = np.cos(self.slope_pitch)
        sp = np.sin(self.slope_pitch)
        cr = np.cos(self.slope_roll)
        sr = np.sin(self.slope_roll)
        rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=np.float32)
        ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=np.float32)
        return ry @ rx

    def _terrain_height(self, x_world: float, y_world: float) -> float:
        return self.com_height_des + np.tan(self.slope_pitch) * x_world + np.tan(self.slope_roll) * y_world

    def _project_velocity_to_terrain(self, vel_world: np.ndarray) -> np.ndarray:
        r_t = self._terrain_rotation_matrix()
        vel_terrain = r_t.T @ vel_world
        vel_terrain[2] = 0.0
        return r_t @ vel_terrain

    def update_robot_state(self, robot_data: RobotData):
        if not self.is_initialized:
            self.current_state = np.zeros(13, dtype=np.float32)
            self.roll_init = 0.0
            self.pitch_init = 0.0
            self.is_initialized = True

        self._SlopeModelPredictiveController__robot_data = robot_data
        rpy_base = quat2ZYXangle(robot_data.quat_base)
        pos_base = np.array(robot_data.pos_base, dtype=np.float32)
        omega_base = np.array(robot_data.ang_vel_base, dtype=np.float32)
        vel_base = np.array(robot_data.lin_vel_base, dtype=np.float32)
        for i in range(3):
            self.current_state[i] = rpy_base[i]
            self.current_state[3 + i] = pos_base[i]
            self.current_state[6 + i] = omega_base[i]
            self.current_state[9 + i] = vel_base[i]
        self.current_state[12] = -self.gravity
        self.yaw = rpy_base[2]
        self.pos_base_feet = robot_data.pos_base_feet

    def update_mpc_if_needed(self, iter_counter, base_vel_base_des, yaw_turn_rate_des,
        gait_table, solver='drake', debug=False, iter_debug=None):
        vel_world_des = self._SlopeModelPredictiveController__robot_data.R_base @ base_vel_base_des
        vel_world_des = self._project_velocity_to_terrain(vel_world_des)
        if self.is_first_run:
            self.xpos_base_desired = 0.0
            self.ypos_base_desired = 0.0
            self.yaw_desired = self.yaw
            self.is_first_run = False
        else:
            self.xpos_base_desired += self.dt_control * vel_world_des[0]
            self.ypos_base_desired += self.dt_control * vel_world_des[1]
            self.yaw_desired = self.yaw + self.dt_control * yaw_turn_rate_des

        if iter_counter % self.iterations_between_mpc == 0:
            ref_traj = self.generate_reference_trajectory(vel_world_des, yaw_turn_rate_des)
            self.ref_traj = ref_traj
            solve_start = time.time()
            self.__contact_forces = self._solve_mpc(ref_traj, gait_table, solver=solver)[:12]
            self.last_mpc_solve_time = time.time() - solve_start
            self.last_mpc_solve_iteration = iter_counter
            if debug and iter_counter == iter_debug:
                contact_forces_debug = self._solve_mpc(ref_traj, gait_table, solver=solver, debug=debug)
                self._ModelPredictiveController__visulize_com_traj_solution(contact_forces_debug)

        return self.__contact_forces[:12]

    def generate_reference_trajectory(self, vel_base_des: Union[list, np.ndarray], yaw_turn_rate: float) -> np.ndarray:
        cur_xpos_desired = self.xpos_base_desired
        cur_ypos_desired = self.ypos_base_desired
        max_pos_error = 0.1

        if cur_xpos_desired - self.current_state[3] > max_pos_error:
            cur_xpos_desired = self.current_state[3] + max_pos_error
        if self.current_state[3] - cur_xpos_desired > max_pos_error:
            cur_xpos_desired = self.current_state[3] - max_pos_error
        if cur_ypos_desired - self.current_state[4] > max_pos_error:
            cur_ypos_desired = self.current_state[4] + max_pos_error
        if self.current_state[4] - cur_ypos_desired > max_pos_error:
            cur_ypos_desired = self.current_state[4] - max_pos_error

        self.xpos_base_desired = cur_xpos_desired
        self.ypos_base_desired = cur_ypos_desired

        if np.fabs(self.current_state[9]) > 0.2:
            self.pitch_init += self.dt * ((self.slope_pitch - self.current_state[1]) / self.current_state[9])
        if np.fabs(self.current_state[10]) > 0.1:
            self.roll_init += self.dt * ((self.slope_roll - self.current_state[0]) / self.current_state[10])

        self.roll_init = np.fmin(np.fmax(self.roll_init, -0.35), 0.35)
        self.pitch_init = np.fmin(np.fmax(self.pitch_init, -0.35), 0.35)

        roll_comp = self.current_state[10] * self.roll_init + self.slope_roll
        pitch_comp = self.current_state[9] * self.pitch_init + self.slope_pitch

        X_ref = np.zeros(self.num_state * self.horizon, dtype=np.float32)
        X_ref[0::self.num_state] = roll_comp
        X_ref[1::self.num_state] = pitch_comp
        X_ref[2] = self.yaw_desired
        X_ref[3] = cur_xpos_desired
        X_ref[4] = cur_ypos_desired
        X_ref[5::self.num_state] = self._terrain_height(cur_xpos_desired, cur_ypos_desired)
        X_ref[8::self.num_state] = yaw_turn_rate
        X_ref[9::self.num_state] = vel_base_des[0]
        X_ref[10::self.num_state] = vel_base_des[1]
        X_ref[12::self.num_state] = -self.gravity

        for i in range(1, self.horizon):
            X_ref[2 + self.num_state * i] = X_ref[2 + self.num_state * (i - 1)] + self.dt * yaw_turn_rate
            X_ref[3 + self.num_state * i] = X_ref[3 + self.num_state * (i - 1)] + self.dt * vel_base_des[0]
            X_ref[4 + self.num_state * i] = X_ref[4 + self.num_state * (i - 1)] + self.dt * vel_base_des[1]
            X_ref[5 + self.num_state * i] = self._terrain_height(X_ref[3 + self.num_state * i], X_ref[4 + self.num_state * i])

        return X_ref

    def _generate_state_space_model(self):
        Ac = np.zeros((self.num_state, self.num_state), dtype=np.float32)
        Bc = np.zeros((self.num_state, self.num_input), dtype=np.float32)

        Rz = np.array([[np.cos(self.yaw), -np.sin(self.yaw), 0],
                       [np.sin(self.yaw), np.cos(self.yaw), 0],
                       [0, 0, 1]], dtype=np.float32)
        world_I = Rz @ self.base_inertia_base @ Rz.T

        terrain_R = self._terrain_rotation_matrix()
        Ac[0:3, 6:9] = terrain_R.T
        Ac[3:6, 9:12] = np.identity(3, dtype=np.float32)
        Ac[11, 12] = 1.0

        gravity_world = np.array([0.0, 0.0, -self.gravity], dtype=np.float32)
        Ac[9:12, 12] = terrain_R.T @ gravity_world / max(self.gravity, 1e-6)

        for i in range(4):
            foot_pos_terrain = terrain_R.T @ self.pos_base_feet[i]
            Bc[6:9, 3 * i:3 * i + 3] = np.linalg.inv(world_I) @ vec2so3(foot_pos_terrain)
            Bc[9:12, 3 * i:3 * i + 3] = terrain_R.T @ (np.identity(3, dtype=np.float32) / self.mass)

        return Ac, Bc

    def _generate_QP_constraints(self, gait_table):
        terrain_R = self._terrain_rotation_matrix()
        terrain_n = terrain_R @ np.array([0.0, 0.0, 1.0], dtype=np.float32)
        terrain_t1 = terrain_R @ np.array([1.0, 0.0, 0.0], dtype=np.float32)
        terrain_t2 = terrain_R @ np.array([0.0, 1.0, 0.0], dtype=np.float32)

        def local_to_world_force_rows(axis):
            return np.array(axis, dtype=np.float32)

        # Friction pyramid aligned with the terrain frame.
        constraint_coef_matrix = np.array([
            [ terrain_t1[0], terrain_t1[1], self.mu * terrain_n[2]],
            [-terrain_t1[0],-terrain_t1[1], self.mu * terrain_n[2]],
            [ terrain_t2[0], terrain_t2[1], self.mu * terrain_n[2]],
            [-terrain_t2[0],-terrain_t2[1], self.mu * terrain_n[2]],
            [ terrain_n[0],  terrain_n[1],  terrain_n[2]],
        ], dtype=np.float32)
        qp_C = np.kron(np.identity(4 * self.horizon, dtype=np.float32), constraint_coef_matrix)

        C_lb = np.zeros(4 * 5 * self.horizon, dtype=np.float32)
        C_ub = np.zeros(4 * 5 * self.horizon, dtype=np.float32)
        k = 0
        for i in range(self.horizon):
            for j in range(4):
                C_ub[5 * k:5 * k + 4] = np.inf
                C_ub[5 * k + 4] = gait_table[4 * i + j] * self.fz_max
                k += 1

        return qp_C, C_lb, C_ub

    def _solve_mpc(self, ref_traj, gait_table, solver='drake', debug=False):
        assert solver == 'drake' or solver == 'qpsolvers'
        Ac, Bc = self._generate_state_space_model()
        Ad, Bd = self._discretize_continuous_model(Ac, Bc)
        qpH, qpg = self._generate_QP_cost(Ad, Bd, self.current_state, ref_traj, debug=debug)
        qp_C, C_lb, C_ub = self._generate_QP_constraints(gait_table)

        if solver == 'drake':
            qp_problem = MathematicalProgram()
            contact_forces = qp_problem.NewContinuousVariables(self.num_input * self.horizon, 'contact_forces')
            qp_problem.AddQuadraticCost(qpH, qpg, contact_forces)
            qp_problem.AddLinearConstraint(qp_C, C_lb, C_ub, contact_forces)
            result = Solve(qp_problem)
            return result.GetSolution(contact_forces)

        return solve_qp(P=qpH, q=qpg, G=qp_C, h=C_ub, A=None, b=None, solver='osqp')
