

1. 环境配置+替换模型为go2

我这边本地因为有下载pinoccho所以有点问题 其实uv里面自动有pin=3.9所以不要调用本机的，所以每次运行我都要运行下面这个
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH


config/robot_configs.py



包括摩擦配置 kd kp调整


2. /home/y/ece489/lab4/pympc-quadruped/scripts/go2_mpc.py


增加了速度可视化





3. eval直接输出三种配置在flat模式下的

uv run python /home/y/ece489/lab4/pympc-quadruped/scripts/eval_mpc_go2.py


## Velocity Tracking ###
Terrain    Command                Vel_X_RMSE   Vel_Y_RMSE   Mean_X     Mean_Y    
--------------------------------------------------------------------------------
flat       Forward 1.0 m/s        0.0415       0.0505       1.0172     0.0212    
flat       Lateral 1.0 m/s        0.1364       0.0969       0.0686     1.0862    
flat       Fwd 1.0 + Lat 0.5      0.0764       0.1789       0.9809     0.6678    

### Body Stability ###
Terrain    Command                Roll_Std   Pitch_Std  Mean_R     Mean_P    
--------------------------------------------------------------------------------
flat       Forward 1.0 m/s        0.57       0.39       -0.12      6.08      
flat       Lateral 1.0 m/s        1.23       1.66       -4.50      0.65      
flat       Fwd 1.0 + Lat 0.5      1.07       1.14       -1.34      6.02      

### Energy Efficiency ###
Terrain    Command                CoT          Distance  
------------------------------------------------------------
flat       Forward 1.0 m/s        3.8658       0.5091    
flat       Lateral 1.0 m/s        6.6671       0.5435    
flat       Fwd 1.0 + Lat 0.5      5.3980       0.5948    


4. push

uv run python scripts/demo_push_test.py

5. 步态还没有完成 初版有点问题
