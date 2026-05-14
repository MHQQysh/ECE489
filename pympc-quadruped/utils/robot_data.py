import os
from typing import List, Optional, Tuple, Union

import numpy as np
import pinocchio

from utils.kinematics import adSE3_Rp, quat2matrix, quat2ZYXangle, vec_format_standardization


class RobotData():
    '''
    This framework is to use the sensor data (measurement) to generate all the 
    data of the robot in our control strategy.

    Params
    ------
    robot_model: str
        path to urdf file of the robot.
    state_estimation: (optional) bool
        identify whether to use the state estimation module. If the state estimation 
        module is used, we add noises to the data to simulate the real case. 
        Otherwise we use the data provided by the simulator directly.

    Measurement
    -----------
    1. the position $q$ and velocity $\dot{q}$ of each joint, provided by the 
    incremental encoder.
    2. the position $p$, velocity $v$, orientation $R$ and angular velocity 
    $\omega$ of the base, provided by IMU. Note that the orientation is expressed 
    as quanternion.

    Sign Convention
    ---------------
    1. quanternion is recorded as (real part, imaginary part).
    2. If we want to express a quantity B with respect to C in frame A, we write 
    A_quantity_C_B. By default, if the quantity does not have the prefix A, it 
    means this quantity is expressed in world frame, or inertia frame. In such 
    case, the prefix A is omitted. Similarly, if the quantity does not have the 
    suffix C, it means this quantity is relative to the world, or the inertia 
    frame. Now we show some examples:
    Ex.1. base_pos_base_foot: the position of foot with respect to base expressed 
    in base frame.
    Ex.2. pos_base_foot: the position of foot with respect to base expressed in 
    world frame. (it is the same as world_pos_base_foot)
    Ex.3. pos_foot: the position of foot with respect world expressed in world 
    frame. (it is the same as world_pos_world_foot)
    '''

    def __init__(
        self,
        robot_model: str, 
        state_estimation: Optional[bool] = False
    ) -> None:
        self.state_estimation = state_estimation
        self.__init_pinocchio(robot_model)

        self.__contact_history = np.zeros((4, 3), dtype=np.float32)
    
    def update(
        self, 
        # data: Union[list, np.ndarray],
        pos_base: Union[list, np.ndarray],
        lin_vel_base: Union[list, np.ndarray],
        quat_base: Union[list, np.ndarray],
        ang_vel_base: Union[list, np.ndarray],
        q: Union[list, np.ndarray],
        qdot: Union[list, np.ndarray]
    ) -> None:
        if not self.state_estimation:
            self.pos_base: np.ndarray = vec_format_standardization(pos_base, '1darray')
            self.lin_vel_base: np.ndarray = vec_format_standardization(lin_vel_base, '1darray')
            self.quat_base: np.ndarray = vec_format_standardization(quat_base, '1darray')
            self.ang_vel_base: np.ndarray = vec_format_standardization(ang_vel_base, '1darray')

            self.R_base = quat2matrix(self.quat_base)
            self.rpy_base = np.array(quat2ZYXangle(self.quat_base))

            self.q: np.ndarray = vec_format_standardization(q, '1darray')
            self.qdot: np.ndarray = vec_format_standardization(qdot, '1darray')
        else:
            raise NotImplementedError

        # NOTE: quat in MuJoCo: (real part, imaginary part)
        #       quat in pinocchio: (imaginary part, real part)
        quat_base_converted = [self.quat_base[1], self.quat_base[2], 
            self.quat_base[3], self.quat_base[0]]
        # generalized joint position (floating base), dim: 3 + 3 + 12 = 18.
        generalized_q = list(self.pos_base) + list(quat_base_converted) \
            + list(self.q)
        self.__generalized_q = np.array(generalized_q, dtype=np.float32)
        pinocchio.forwardKinematics(self.__pin_model, self.__pin_data, self.__generalized_q)
        pinocchio.framesForwardKinematics(self.__pin_model, self.__pin_data, self.__generalized_q)

        # NOTE: jacobian in pinocchio is [Jv, Jw], thus this X is actually X.T defined in modern robotics
        self.X_base = adSE3_Rp(self.R_base, self.pos_base)

        self.Jv_feet, self.base_Jv_feet = self.__compute_foot_Jacobian()   # geometric jacobian
        # the position of feet relative to world expressed in world frame
        self.pos_feet = self.__compute_pos_feet()
        # the position of feet relative to base expressed in world frame
        self.pos_base_feet = self.__compute_pos_base_feet()
        # the position of feet relative to base expressed in base frame
        self.base_pos_base_feet = self.__compute_base_pos_base_feet()
        self.base_vel_base_feet = self.__compute_base_vel_base_feet()
        # print(self.base_vel_base_feet)

        self.pos_thighs = self.__compute_pos_thighs()
        self.base_pos_base_thighs = self.__compute_base_pos_base_thighs()

    def __init_pinocchio(self, robot_model) -> None:
        # NOTE: The second parameter represents the floating base.
        # see https://github.com/stack-of-tasks/pinocchio/issues/1596
        self.__pin_model = pinocchio.buildModelFromUrdf(
            robot_model, pinocchio.JointModelFreeFlyer())
        self.__pin_data = self.__pin_model.createData()
        
    def __compute_foot_Jacobian(self) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        foot_frames = ['FL_foot_fixed', 'FR_foot_fixed', 'RL_foot_fixed', 'RR_foot_fixed']
        foot_frames_ID = [self.__pin_model.getFrameId(foot_frames[i]) for i in range(4)]
        
        Jv_feet = []
        base_Jv_feet = []
        for i in range(4):
            Ji = pinocchio.computeFrameJacobian(self.__pin_model, self.__pin_data, 
                self.__generalized_q, frame_id=foot_frames_ID[i], 
                reference_frame=pinocchio.ReferenceFrame.LOCAL_WORLD_ALIGNED)
            # Jacobian in Pinocchio: [[Jv]
            #                         [Jw]]
            base_Ji = self.X_base @ Ji
            Jv_feet.append(Ji[0:3, :])
            base_Jv_feet.append(base_Ji[0:3, :])
            
        return Jv_feet, base_Jv_feet

    def __compute_pos_feet(self) -> List[np.ndarray]:
        foot_frames = ['FL_foot_fixed', 'FR_foot_fixed', 'RL_foot_fixed', 'RR_foot_fixed']
        foot_frames_ID = [self.__pin_model.getFrameId(foot_frames[i]) for i in range(4)]
        pos_feet = []
        for foot_idx in range(4):
            pos_footi = self.__pin_data.oMf[foot_frames_ID[foot_idx]].translation
            pos_feet.append(pos_footi)
        return pos_feet

    def __compute_pos_base_feet(self) -> List[np.ndarray]:
        pos_base_feet = []
        for foot_idx in range(4):
            pos_base_footi = self.pos_feet[foot_idx] - self.pos_base
            pos_base_feet.append(pos_base_footi)
        return pos_base_feet

    def __compute_base_pos_base_feet(self) -> List[np.ndarray]:
        base_pos_base_feet = []
        for foot_idx in range(4):
            base_pos_base_footi = self.R_base.T @ self.pos_base_feet[foot_idx]
            base_pos_base_feet.append(base_pos_base_footi)
        return base_pos_base_feet

    def __compute_base_vel_base_feet(self) -> List[np.ndarray]:
        base_vel_base_feet = []
        for foot_idx in range(4):
            generalized_qdot = list(self.lin_vel_base) + list(self.ang_vel_base) + list(self.qdot)
            generalized_qdot = np.array(generalized_qdot, dtype=np.float32)
            vel_footi = self.Jv_feet[foot_idx] @ generalized_qdot
            vel_base_footi = vel_footi - self.lin_vel_base
            base_vel_base_footi = self.R_base.T @ vel_base_footi
            base_vel_base_feet.append(base_vel_base_footi)
        return base_vel_base_feet

    def __compute_pos_thighs(self) -> List[np.ndarray]:
        thigh_frames = ['FL_thigh_joint', 'FR_thigh_joint', 'RL_thigh_joint', 'RR_thigh_joint']
        thigh_frames_ID = [self.__pin_model.getFrameId(thigh_frames[i]) for i in range(4)]
        pos_thighs = []
        for thigh_idx in range(4):
            pos_thighi = self.__pin_data.oMf[thigh_frames_ID[thigh_idx]].translation
            pos_thighs.append(pos_thighi)
        return pos_thighs
        
    def __compute_base_pos_base_thighs(self) -> List[np.ndarray]:
        base_pos_base_thighs = []
        for thigh_idx in range(4):
            pos_base_thighi = self.pos_thighs[thigh_idx] - self.pos_base
            base_pos_base_thighi = self.R_base.T @ pos_base_thighi
            base_pos_base_thighs.append(base_pos_base_thighi)
        return base_pos_base_thighs
    
    def init_contact_history(self) -> None:
        self.__contact_history == self.pos_feet

    def __update_contact_history(self, cur_contact_state: Union[list, np.ndarray]) -> None:
        for foot_idx in range(4):
            if cur_contact_state[foot_idx] == 1:
                self.__contact_history[foot_idx] = self.pos_feet[foot_idx]

    def update_terrain_normal(self, cur_contact_state: Union[list, np.ndarray]) -> None:
        self.__update_contact_history(cur_contact_state)

        # Least squares approach
        #      A        x  =   b
        # [1 p1x p1y] [a0]   [p1z]
        # [1 p2x p2y] [a1] = [p2z]
        # [1 p3x p3y] [a2]   [p3z]
        # [1 p4x p4y]        [p4z]
        # A = np.array([
        #     [1, self.__contact_history[0, 0], self.__contact_history[0, 1]],
        #     [1, self.__contact_history[1, 0], self.__contact_history[1, 1]],
        #     [1, self.__contact_history[2, 0], self.__contact_history[2, 1]],
        #     [1, self.__contact_history[3, 0], self.__contact_history[3, 1]]
        # ])
        # b = np.array([
        #     [self.__contact_history[0, 2]],
        #     [self.__contact_history[1, 2]],
        #     [self.__contact_history[2, 2]],
        #     [self.__contact_history[3, 2]]
        # ])

        # x = np.linalg.lstsq(A, b)[0]

        # PCA approach
        X = self.__contact_history.T
        mu = np.mean(self.__contact_history, axis=0).reshape(3, 1)
        one = np.ones((1, 4), dtype=np.float32)
        sigma = (X - mu @ one) @ ((X - mu @ one).T)
        eigenvalues, eigenvectors = np.linalg.eig(sigma)
        self.terrain_normal_est = eigenvectors[np.argmin(eigenvalues)]
        if self.terrain_normal_est[2] < 0:
            self.terrain_normal_est = -self.terrain_normal_est
        self.terrain_normal_est_yaw_aligned = self.R_base.T @ self.terrain_normal_est
        # print(self.terrain_normal_est_yaw_aligned)

    def get_log_string(self, iter_counter: int, sim_time: float) -> str:
        """Generate a formatted log string for the current robot state."""
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"Iteration: {iter_counter}, Sim Time: {sim_time:.4f}s")
        lines.append(f"{'='*60}")
        
        lines.append(f"\n[Base State]")
        lines.append(f"  pos_base (world):       [{self.pos_base[0]:.6f}, {self.pos_base[1]:.6f}, {self.pos_base[2]:.6f}] m")
        lines.append(f"  lin_vel_base (world):   [{self.lin_vel_base[0]:.6f}, {self.lin_vel_base[1]:.6f}, {self.lin_vel_base[2]:.6f}] m/s")
        lines.append(f"  rpy_base (ZYX, deg):    [{np.rad2deg(self.rpy_base[0]):.2f}, {np.rad2deg(self.rpy_base[1]):.2f}, {np.rad2deg(self.rpy_base[2]):.2f}] deg")
        lines.append(f"  ang_vel_base (world):   [{self.ang_vel_base[0]:.6f}, {self.ang_vel_base[1]:.6f}, {self.ang_vel_base[2]:.6f}] rad/s")
        lines.append(f"  quat_base:              [{self.quat_base[0]:.6f}, {self.quat_base[1]:.6f}, {self.quat_base[2]:.6f}, {self.quat_base[3]:.6f}] (w,x,y,z)")
        
        lines.append(f"\n[R_base - Rotation Matrix from Base to World]")
        for i in range(3):
            lines.append(f"  Row {i}: [{self.R_base[i,0]:.6f}, {self.R_base[i,1]:.6f}, {self.R_base[i,2]:.6f}]")
        
        lines.append(f"\n[Joint State]")
        joint_names = ['FL_hip', 'FL_thigh', 'FL_calf', 
                       'FR_hip', 'FR_thigh', 'FR_calf',
                       'RL_hip', 'RL_thigh', 'RL_calf',
                       'RR_hip', 'RR_thigh', 'RR_calf']
        for i in range(12):
            lines.append(f"  {joint_names[i]:12s}: q={self.q[i]:.6f} rad, qdot={self.qdot[i]:.6f} rad/s")
        
        lines.append(f"\n[Foot Positions - World Frame]")
        leg_names = ['FL', 'FR', 'RL', 'RR']
        for i in range(4):
            lines.append(f"  {leg_names[i]} foot:       [{self.pos_feet[i][0]:.6f}, {self.pos_feet[i][1]:.6f}, {self.pos_feet[i][2]:.6f}] m")
        
        lines.append(f"\n[Foot Positions - Relative to Base (World Frame)]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} foot_rel:   [{self.pos_base_feet[i][0]:.6f}, {self.pos_base_feet[i][1]:.6f}, {self.pos_base_feet[i][2]:.6f}] m")
        
        lines.append(f"\n[Foot Positions - Base Frame]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} foot_base:  [{self.base_pos_base_feet[i][0]:.6f}, {self.base_pos_base_feet[i][1]:.6f}, {self.base_pos_base_feet[i][2]:.6f}] m")
        
        lines.append(f"\n[Foot Velocities - Base Frame]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} vel_base:  [{self.base_vel_base_feet[i][0]:.6f}, {self.base_vel_base_feet[i][1]:.6f}, {self.base_vel_base_feet[i][2]:.6f}] m/s")
        
        lines.append(f"\n[Thigh Positions - World Frame]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} thigh:     [{self.pos_thighs[i][0]:.6f}, {self.pos_thighs[i][1]:.6f}, {self.pos_thighs[i][2]:.6f}] m")
        
        lines.append(f"\n[Thigh Positions - Base Frame]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} thigh_base:[{self.base_pos_base_thighs[i][0]:.6f}, {self.base_pos_base_thighs[i][1]:.6f}, {self.base_pos_base_thighs[i][2]:.6f}] m")
        
        lines.append(f"\n[Foot Jacobians - Geometric (3x18)]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} Jv (6x18, first 3 rows shown):")
            for row in range(3):
                row_str = ", ".join([f"{self.Jv_feet[i][row,j]:8.4f}" for j in range(min(18, self.Jv_feet[i].shape[1]))])
                lines.append(f"    [{row_str}]")
        
        lines.append(f"\n[Base Frame Foot Jacobians]")
        for i in range(4):
            lines.append(f"  {leg_names[i]} base_Jv:")
            for row in range(3):
                row_str = ", ".join([f"{self.base_Jv_feet[i][row,j]:8.4f}" for j in range(self.base_Jv_feet[i].shape[1])])
                lines.append(f"    [{row_str}]")
        
        return "\n".join(lines)


class RobotDataLogger:
    """Logger for RobotData - writes robot state to a log file."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file = open(filepath, 'w')
        self.header_written = False
    
    def log(self, robot_data: RobotData, iter_counter: int, sim_time: float):
        log_str = robot_data.get_log_string(iter_counter, sim_time)
        self.file.write(log_str + "\n\n")
        self.file.flush()
    
    def log_compact(self, robot_data: RobotData, iter_counter: int, sim_time: float):
        """Write a compact single-line log for high-frequency logging."""
        if not self.header_written:
            header = "iter,time,pos_x,pos_y,pos_z,vel_x,vel_y,vel_z,roll,pitch,yaw,ang_x,ang_y,ang_z"
            header += ",q_FL_hip,q_FL_thigh,q_FL_calf,q_FR_hip,q_FR_thigh,q_FR_calf"
            header += ",q_RL_hip,q_RL_thigh,q_RL_calf,q_RR_hip,q_RR_thigh,q_RR_calf"
            header += ",foot_FL_x,foot_FL_y,foot_FL_z"
            header += ",foot_FR_x,foot_FR_y,foot_FR_z"
            header += ",foot_RL_x,foot_RL_y,foot_RL_z"
            header += ",foot_RR_x,foot_RR_y,foot_RR_z"
            self.file.write(header + "\n")
            self.header_written = True
        
        values = [
            iter_counter,
            sim_time,
            robot_data.pos_base[0], robot_data.pos_base[1], robot_data.pos_base[2],
            robot_data.lin_vel_base[0], robot_data.lin_vel_base[1], robot_data.lin_vel_base[2],
            robot_data.rpy_base[0], robot_data.rpy_base[1], robot_data.rpy_base[2],
            robot_data.ang_vel_base[0], robot_data.ang_vel_base[1], robot_data.ang_vel_base[2],
        ]
        values.extend(robot_data.q.tolist())
        for i in range(4):
            values.extend(robot_data.pos_feet[i].tolist())
        
        line = ",".join([f"{v:.6f}" if isinstance(v, float) else str(v) for v in values])
        self.file.write(line + "\n")
        self.file.flush()
    
    def close(self):
        if self.file:
            self.file.close()


def test():
    robot_path = os.path.join(os.path.dirname(__file__), '../robot/aliengo/urdf/aliengo.urdf')

    robot_data = RobotData(robot_model=robot_path)
    robot_data.update(
        pos_base=[0.00727408, 0.00061764, 0.43571295],
        lin_vel_base=[0.0189759 , 0.00054278, 0.02322867],
        quat_base=[9.99951619e-01, -9.13191258e-03,  3.57360542e-03,  7.72221709e-04],
        ang_vel_base=[-0.06964452, -0.01762341, -0.00088601],
        q=[0.00687206, 0.52588717, -1.22975589, 
           0.02480081, 0.51914926, -1.21463939,
           0.00892169, 0.51229961, -1.20195572,
           0.02621839, 0.50635251, -1.18849609],
        qdot=[0.06341452, -0.02158136, 0.16191205,
              0.07448259, -0.04855474, 0.21399941,
              0.06280346,  0.00562435, 0.10597827,
              0.07388069, -0.02180622, 0.15909948],
    )

    print(robot_data.base_pos_base_feet)

if __name__ == '__main__':
    test()
