
根据project.pdf为我完成final report
我现在已经完成的部分是
mpc 和mjlab两种







测试环境
1. 平地​  训练500step
2. slope 训练1000step

测试速度：两种命令速度
1. x 1m/s
2. y 1m/s
3. x 1m/s y 0.5m/s

测试指标（每个都10次）
1. 速度跟踪误差（RMS）；
2. 身体稳定性（RMS roll & pitch，即横滚/俯仰角波动）；
3. 能量消耗（Cost of Transport, CoT = 总能耗 / 位移，越小越节能）；
4. 鲁棒性：施加横向推力（30-50N，持续0.1s），记录“恢复成功次数”（被推后能不能站稳继续走）。


Model,Terrain,Command,Velocity_X_m_per_s,Velocity_Y_m_per_s,Roll_deg,Pitch_deg,CoT,Total_Energy_J,Mean_Torque_Nm,Push_Recovery
Flat,Flat,Forward 1.0 m/s,"0.9632 ± 0.0897","-0.0034 ± 0.0422","2.50 ± 103.08","0.82 ± 7.26",133.1285,12814.77,1281.48,40.0%
Flat,Flat,Lateral 1.0 m/s,"-0.0487 ± 0.0675","0.9472 ± 0.1300","-15.67 ± 96.72","-0.84 ± 7.84",103.4327,14000.97,1400.10,0.0%
Flat,Flat,Fwd 1.0 + Lat 0.5,"0.9543 ± 0.0966","0.4762 ± 0.0728","47.98 ± 111.37","0.09 ± 6.52",78.6910,12040.02,1204.00,60.0%
Slope,Flat,Forward 1.0 m/s,"0.9326 ± 0.1828","-0.0603 ± 0.1277","-27.37 ± 76.23","0.26 ± 2.91",76.7331,10349.68,1034.97,40.0%
Slope,Flat,Lateral 1.0 m/s,"0.0718 ± 0.1101","0.8413 ± 0.2319","-5.99 ± 100.46","1.65 ± 5.29",171.3187,11954.80,1195.48,0.0%
Slope,Flat,Fwd 1.0 + Lat 0.5,"0.8941 ± 0.1954","0.4528 ± 0.1338","-32.31 ± 129.23","1.43 ± 3.02",81.7461,11941.45,1194.15,20.0%



mpc是

测试指标（每个都10次）
1. 平地​  
2. slope
1. 速度跟踪误差（RMS）；
2. 身体稳定性（RMS roll & pitch，即横滚/俯仰角波动）；
3. 能量消耗（Cost of Transport, CoT = 总能耗 / 位移，越小越节能）；
4. 鲁棒性：施加横向推力（30-50N，持续0.1s），记录“恢复成功次数”（被推后能不能站稳继续走）。





这两个我都可以给你一个



###############################################

我还是感觉现在的框架不太好 根据下面的要求进行修改



所有代码文件都在 文件在mjlab下面

3.1.3 里面格格内容你阅读一下然后填写明白 然后actoni space observation 我印象中slope和flat是不一样的 你看看代码 理解一下 然后用一个表格展示有多少


3.1.4 这个部分我有一张tensorboard的图 你留出来位置 
你可以看看 run_reward_experiments.py 理解一下我在做什么 

3.1.5我计划放一张有domain 效果的图  一张没有domain效果的图 但是我现在应该是都有 


3.1.6 根据我代码完成一下 
training curve 
在flat_slope这几张 你可以放一下


然后可视化你可以提取视频里面的一两张图
/home/y/ece489/project/rl_flat_alldirection_force.webm
/home/y/ece489/project/rl_slope_alldirection_withpush.webm


3.2部分你放到5 extension里面去

根据/home/y/ece489/lab4/pympc-quadruped/scripts/eval_mpc.py
这里面代码完成一下



然后4 标题改成evaluation & comparision

然后4.4 开始展示5.1的内容

4.5discuss 就是放下面6里面的分析就行




5里面mpc你也要选视频中的一两张图 进行展示


###################################

3.1.5部分 现在可以导入/home/y/ece489/project/reward.png 
/home/y/ece489/project/reward2.png 
/home/y/ece489/project/reward3.png 
这三个照片 然后具体每种都是什么也要说明一下

另外run_reward_experiments.py 具体配置都在这里面 用表格展示


3.1。7 要用上我现在的这些curve啊/home/y/ece489/project/flat_slope1.png 和2 3 png


可视化的部分 你在/home/y/ece489/project/rl_flat_alldirection_force.webm /home/y/ece489/project/rl_slope_alldirection_withpush.webm这里面随便截图几张 然后放上去 mpc也是随便截图几张放上去/home/y/ece489/project/mpc_flat_xfast.webm 还有另外几个webm



MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 200 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200




### Velocity Tracking ###
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




######################################

domian randomization 和nondomain randonmization效果对比


randomization这里/home/y/ece489/project/with            
  randomization.webm /home/y/ece489/project/no            
  randomization.webm截取两个图片做个对比说明一下没有rando 
  mization直接训练不出来                                  
  不动另外extension部分整体作为第五部分                   
  然后再加一个部分有关步态 我经过尝试发现                 
  不同环境决定步态 如果slope环境就得到trottingg步态       
  如果rough各种金字塔什么都有就会得到jumping步态          
  然后地形越复杂需要训练时间越长 另外mpc================= 
  ===========================================             
  RESULTS SUMMARY                                         
  ======================================================= 
  =====                                                   
                                                          
  ### Velocity Tracking ###                               
  Terrain    Command                Vel_X_RMSE            
  Vel_Y_RMSE   Mean_X     Mean_Y                          
  ------------------------------------------------------- 
  -------------------------                               
  flat       Forward 1.0 m/s        0.0415       0.0505   
       1.0172     0.0212                                  
  flat       Lateral 1.0 m/s        0.1364       0.0969   
       0.0686     1.0862                                  
  flat       Fwd 1.0 + Lat 0.5      0.0764       0.1789   
       0.9809     0.6678                                  
                                                          
  ### Body Stability ###                                  
  Terrain    Command                Roll_Std   Pitch_Std  
   Mean_R     Mean_P                                      
  ------------------------------------------------------- 
  -------------------------                               
  flat       Forward 1.0 m/s        0.57       0.39       
   -0.12      6.08                                        
  flat       Lateral 1.0 m/s        1.23       1.66       
   -4.50      0.65                                        
  flat       Fwd 1.0 + Lat 0.5      1.07       1.14       
   -1.34      6.02                                        
                                                          
  ### Energy Efficiency ###                               
  Terrain    Command                CoT          Distance 
                                                          
  ------------------------------------------------------- 
  -----                                                   
  flat       Forward 1.0 m/s        3.8658       0.5091   
                                                          
  flat       Lateral 1.0 m/s        6.6671       0.5435   
                                                          
  flat       Fwd 1.0 + Lat 0.5      5.3980       0.5948   
  这套数据作为最终结果     