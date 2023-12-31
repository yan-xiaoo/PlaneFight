# 该文件用于保存一些游戏的配置
# 这些配置的修改直到重启游戏前都无法生效
# 用文件存储设置是因为pygame没啥按钮，文本框之类的控件
# 导致我想做个更改键位的对话框都做不了
import pygame


# 暂停键
# K_e表示按下e即可暂停游戏，再次按下解除暂停
PAUSE_KEY = pygame.K_e

# 游戏的最大帧率
# None: 不限制最大帧率 数字：1s内最多运行这么多帧
# 游戏物体移动计算与帧率无关，因此物体速度不会随帧率变化，帧率怎么改都无所谓
MAX_RATE = 120

# 显示帧率的按键
# 游戏中按下该按键左上角显示帧率
FPS_KEY = pygame.K_q

# 退出按键
# 游戏中按下该按键退出游戏，和点击关闭键效果一样
QUIT_KEY = pygame.K_ESCAPE

# 开火按键
# 游戏中按下该按键玩家发射子弹
FIRE_KEY = pygame.K_SPACE

# 全屏按键
# 游戏中按下该按键切换全屏
FULL_KEY = pygame.K_f

# 追踪攻击按键
# 追踪弹仅能在打Boss时释放
CHASE_KEY = pygame.K_c
