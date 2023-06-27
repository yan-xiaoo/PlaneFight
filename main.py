import pygame
import random
import resource
import widget
from configure import *

if not pygame.get_init():
    pygame.init()
# 窗口的尺寸（宽，高）
SCREEN_RECT = pygame.rect.Rect(0, 0, 640, 480)

# 规定普通飞机不同难度下的数据
# speed: 该难度下飞机速度的上下限（像素/秒）
DIFFICULTY = {0: {'speed': (150, 200), "batch": (1, 3), "full_time": 0.5},
              1: {'speed': (175, 250), "batch": (2, 4), "full_time": 0.4},
              2: {'speed': (200, 300), "batch": (2, 6), "full_time": 0.3},
              3: {'speed': (250, 350), "batch": (3, 6), "full_time": 0.25},
              }


class CommonSprite(pygame.sprite.Sprite):
    """
    该游戏中所有sprite的基类，支持每隔一段时间轮播图片
    """

    def __init__(self, images, center, change_time: float = None, *group):
        """
        创建一个sprite，并在图片多于一张时每change_time更换一次图片
        注意：每张图片的尺寸最好相同，不然会出现碰撞体积和图片看起来不一样的情况
        :param images: 该精灵的图片，必须是一个列表，可以只有一张。多于一张时图片将会轮播
        :param center: 修正精灵的中心坐标。精灵碰撞矩形的中心会在这里
        :param change_time: 轮播图片的间隔，单位：秒
        :param group: 该精灵所要添加到的组，可以有任意多个
        """
        super().__init__(*group)
        self.images = images
        self.image_number = 0
        self.image = images[self.image_number]
        self.rect = self.images[self.image_number].get_rect()
        self.rect.center = center
        # 每隔多久轮播一次图片，单位：秒
        if not isinstance(change_time, float):
            self.total_change_time = 0.2
        else:
            self.total_change_time = change_time
        self.change_time = self.total_change_time

    def update(self, dt) -> None:
        """
        该方法应当被每帧调用以更新图片
        :param dt: 距离上次调用的间隔（秒）
        :return:无
        """
        if len(self.images) == 1:
            return
        self.change_time -= dt
        if self.change_time <= 0:
            self.change_time = self.total_change_time
            self.image_number = (self.image_number + 1) % len(self.images)
            self.image = self.images[self.image_number]


class Player(CommonSprite):
    """
    代表玩家的飞机
    """

    def __init__(self, images, center, *group):
        super().__init__(images, center, None, *group)
        # 减小玩家的碰撞箱，降低撞到敌机的可能
        self.rect.width = 45
        self.rect.height = 40
        # 速度：300像素每秒
        self.speed = 300

    def move(self, vertical_direction=0, horizontal_direction=0,
             dt=1 / MAX_RATE if MAX_RATE is not None else 1 / 60) -> None:
        """
        移动玩家。玩家可以在水平与竖直方向移动，且这两种方向的速度互不影响
        :param vertical_direction: 向左还是向右移动（正：右 负：左）
        :param horizontal_direction: 向上还是向下移动（正：下 负：上））
        :param dt: 本次移动距离上次移动时间
        :return: 无
        """
        vertical_direction = 1 if vertical_direction > 0 else -1 if vertical_direction < 0 else 0
        horizontal_direction = 1 if horizontal_direction > 0 else -1 if horizontal_direction < 0 else 0
        self.rect.move_ip(self.speed * vertical_direction * dt, self.speed * horizontal_direction * dt)
        self.rect = self.rect.clamp(SCREEN_RECT)


class Enemy(CommonSprite):
    """
    代表敌人的飞机
    """

    def __init__(self, images: list[pygame.Surface], *group):
        super().__init__(images, (SCREEN_RECT.width * random.random(), 0), None, *group)
        self.large_rect = self.rect.copy()
        self.small_rect = self.rect.copy()
        self.small_rect.width = 60
        self.small_rect.height = 45
        self.large_rect.width = 80
        self.large_rect.height = 60
        # 速度：100-200像素每秒,玩的就是随机，玩的就是刺激
        self.speed = random.randint(100, 200)
        # 为防止敌机出来就死，给点无敌时间
        self.full_time = 0.5

    def update(self, dt) -> None:
        """
        更新敌人的状态，这个敌人只会从上向下飞，不会蛇皮走位
        :param dt: 两次调用该函数的间隔（用来计算应当移动的距离）
        :return:无
        """
        super().update(dt)
        self.full_time -= dt
        self.rect.move_ip(0, self.speed * dt)
        # 如果敌机向下飞出屏幕，就把它删掉
        if self.rect.top >= SCREEN_RECT.bottom:
            self.kill()
        # 校正敌机位置，防止它出现半边跑出屏幕的情
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right


class Explosion(CommonSprite):
    """
    爆炸特效
    在我方或敌方飞机坏掉的时候都会出现该特效
    """

    def __init__(self, images, center, *group):
        super().__init__(images, center, 0.2, *group)
        self.images = images
        self.image_number = 0
        self.image = images[self.image_number]
        self.rect = self.images[self.image_number].get_rect()
        self.rect.center = center

        self.life_time = 0.5  # 单位：秒
        # 测试中发现一个bug，由于后期飞机飞行速度过快，导致后出来的所有飞机全都被爆炸特效炸没了
        # 所以加了一个时间限制，爆炸特效仅会在这段时间内引发连锁爆炸
        self.chain_time = 0.05

    def update(self, dt):
        """
        更新爆炸特效的状态，从出现到消失
        :param dt: 每两次调用间隔
        :return: 无
        """
        super().update(dt)
        self.life_time -= dt
        self.chain_time -= dt
        if self.life_time <= 0:
            self.kill()


class PlayerBullet(CommonSprite):
    """
    我方用来击打敌方的子弹
    """

    def __init__(self, images, center, *group):
        center = list(center)
        center[0] = center[0] + 35
        super().__init__(images, center, None, *group)
        # 速度：500像素/秒 方向：上
        self.speed = -500

    def update(self, dt) -> None:
        super().update(dt)
        self.rect.move_ip(0, self.speed * dt)
        if self.rect.bottom < SCREEN_RECT.top:
            self.kill()


class ScoreBoard(widget.Text):
    """
    记分板
    """

    def __init__(self, center, *group):
        self._score = 0
        super().__init__(text=f"Score: {self._score}", center=center, font='arial', color=(255, 0, 0), font_size=30,
                         group=group)
        self.score = 0

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self._score = new_score
        self.text = f"Score: {self._score}"


class WinMenu(widget.Text):
    """
    胜利菜单
    """

    def __init__(self, center, score, *group):
        super().__init__(f"You Win! Score: {score}", center, color=(255, 0, 0), font_size=40, group=group)
        self._score = score

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self._score = new_score
        self.text = f"You Win! Score: {self._score}"


class FPSView(widget.Text):
    """
    用来显示FPS的控件
    """

    def __init__(self, center, *group):
        super().__init__(text="FPS: 0", center=center, font='arial', color=(0, 0, 255), font_size=30, group=group)
        self.fps = 0

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, new_fps):
        self._fps = new_fps
        self.text = f"FPS: {self._fps}"


def spawn_simple_enemy(groups: list[pygame.sprite.Group], images: list[pygame.Surface], difficulty: int = 0) -> None:
    """
    以difficulty为难度等级召唤出amount个普通飞机敌人（不是boss）加入groups中
    :param images: 这些敌人所使用的一些图片（可以只有一张，多张的情况下会轮播）
    :param groups: 这些召唤出的敌人需要被加入的组
    :param difficulty: 这些召唤的敌人的难度，详情见difficulty字典边上的注释。难度影响飞机速度的上下限,一批飞机多少等
    :return: 无
    """
    for _ in range(random.randint(*DIFFICULTY[difficulty]['batch'])):
        e = Enemy(images, *groups)
        e.speed = random.randint(*DIFFICULTY[difficulty]['speed'])
        e.full_time = DIFFICULTY[difficulty]['full_time']


class MainApp:
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_RECT.size, 0,
                                              pygame.display.mode_ok(SCREEN_RECT.size, 0, 32))
        pygame.display.set_caption("飞机大战")
        # 这张图是示例里的aliens.py用的，感觉很适合主题就拿来了
        self.background_image = resource.load("./data/background.gif", True)
        self.background = pygame.surface.Surface(SCREEN_RECT.size)

        # 加载游戏资源，这样重新开始游戏时不用再加载了
        self.plane_image = resource.load("./data/plane_1.png", True).convert_alpha()
        self.enemy_image = resource.load("./data/enemy_1.png", True).convert_alpha()
        self.explosion_image = resource.load("./data/explosion_1.gif", True).convert_alpha()
        self.shot_image = resource.load('./data/shot.gif', True).convert_alpha()

        # 这个控制变量很特殊，必须放在start外面，不然实现不了重玩
        self.running = False

    def start(self):
        # 由于这张图片特别窄（左右距离小），但左右侧衔接很自然，所以不断从左向右绘制该图片，直至它填满屏幕
        for tile in range(0, SCREEN_RECT.width, self.background_image.get_width()):
            self.background.blit(self.background_image, (tile, 0))
        self.screen.blit(self.background, (0, 0))
        # 重新绘制背景图片，不然会发现上局游戏的飞机还留在这当背景（
        pygame.display.flip()

        # 初始化游戏控制内容
        # 初始处于运行状态
        self.running = True
        # 初始没有暂停
        paused = False
        # 初始游戏没有结束
        playing = True
        # 初始没有胜利
        win = False
        # 存放所有需要更新的对象
        all_objects = pygame.sprite.RenderUpdates()
        # 存放需要在玩家死后更新的对象，一般是爆炸特效，平时不会更新这些内容
        after_player_dead = pygame.sprite.RenderUpdates()
        # 存放玩家胜利后还需要更新的对象
        after_player_win = pygame.sprite.RenderUpdates()
        # 存放暂停时允许更新的对象
        paused_objects = pygame.sprite.RenderUpdates()
        # 用于控制帧率
        clock = pygame.time.Clock()
        # 初始不展示帧率
        show_fps = False
        # 每帧间隔，初始设为0
        diff = 0
        # 开火的总内置cd
        total_fire_cd = 0.25
        # 开火的剩余cd
        fire_cd = 0

        # 初始化游戏对象
        # 记分板
        score_board = ScoreBoard((70, 50), all_objects)
        # 胜利界面
        win_menu = WinMenu(SCREEN_RECT.center, 0, after_player_win)
        # 失败界面
        widget.Text(text="You Lose!", center=SCREEN_RECT.center, font='arial', color=(255, 0, 0), font_size=50, group=[after_player_dead])
        # 暂停界面
        widget.Text(text="Paused", center=SCREEN_RECT.center, font='arial', color=(0, 0, 255), font_size=50, group=[paused_objects])
        # 重玩按钮
        widget.Button(center=(SCREEN_RECT.centerx, SCREEN_RECT.centery + 100), text="Replay",
                      group=[after_player_win, after_player_dead],
                      command=self.replay_game)
        # 用于显示帧率的对象
        fps_view = FPSView((50, SCREEN_RECT.height - 35), all_objects, paused_objects)
        # 难度，默认为0
        difficulty = 0
        # 玩家
        player = Player([self.plane_image], SCREEN_RECT.center, all_objects)
        # 敌人
        enemy = pygame.sprite.Group()
        # 爆炸特效
        explosion_group = pygame.sprite.Group()
        # 子弹
        player_bullet_group = pygame.sprite.Group()

        while self.running:
            dirty_rects = []
            # 这部分专门处理事件
            events = pygame.event.get(pygame.QUIT)
            if events:
                # 在一轮循环结束后退出游戏
                self.running = False
            for key_event in pygame.event.get(pygame.KEYDOWN):
                # 如果按下的按键为配置文件中的暂停键，那么切换暂停状态
                # 只有还在玩的时候才能暂停
                if key_event.key == PAUSE_KEY and playing:
                    paused = not paused
                if key_event.key == FPS_KEY:
                    show_fps = not show_fps
                if key_event.key == QUIT_KEY:
                    self.running = False
            if pygame.mouse.get_pressed(3)[0] and fire_cd <= 0:
                fire_cd = total_fire_cd
                PlayerBullet([self.shot_image], player.rect.midtop, player_bullet_group, all_objects)

            # 暂停时相当于除了处理时间外，其他所有内容停止运行
            # 这里检查目前是否在暂停，如果不在暂停才令游戏运行
            # 下面是游戏循环主要内容：
            if not paused and playing:
                # 清除可能存在的暂停界面，不然会很难看
                paused_objects.clear(self.screen, self.background)
                keys_pressed = pygame.key.get_pressed()
                # 玩家移动, 注意diff单位为毫秒
                player.move(keys_pressed[pygame.K_d] - keys_pressed[pygame.K_a]
                            + keys_pressed[pygame.K_RIGHT] - keys_pressed[pygame.K_LEFT],
                            keys_pressed[pygame.K_s] - keys_pressed[pygame.K_w]
                            + keys_pressed[pygame.K_DOWN] - keys_pressed[pygame.K_UP],
                            diff / 1000)
                all_objects.update(diff / 1000)

                # 如果玩家撞到敌机
                # 游戏结束
                for sprite in enemy.sprites():
                    sprite.rect = sprite.large_rect
                for one_enemy in pygame.sprite.spritecollide(player, enemy, True):
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              one_enemy.rect.center,
                              after_player_dead, explosion_group)
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              player.rect.center,
                              after_player_dead, explosion_group)
                    player.kill()
                    playing = False

                # 玩家开火
                fire_cd -= diff / 1000
                if keys_pressed[FIRE_KEY]:
                    if fire_cd <= 0:
                        fire_cd = total_fire_cd
                        PlayerBullet([self.shot_image], player.rect.midtop, all_objects, player_bullet_group)

                # 检测子弹的命中
                for sprite in enemy.sprites():
                    sprite.rect = sprite.large_rect
                for one_enemy in pygame.sprite.groupcollide(enemy, player_bullet_group, False, True).keys():
                    if one_enemy.full_time <= 0:
                        score_board.score += 10
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  one_enemy.rect.center,
                                  all_objects, explosion_group)
                        one_enemy.kill()

                for one_enemy in pygame.sprite.groupcollide(enemy, explosion_group, False, False).keys():
                    if one_enemy.full_time <= 0:
                        score_board.score += 10
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  one_enemy.rect.center,
                                  all_objects, explosion_group)
                        one_enemy.kill()

                for explosion_sprite in explosion_group.sprites():
                    if explosion_sprite.chain_time <= 0:
                        explosion_group.remove(explosion_sprite)

                # 检测成绩调整难度
                if 200 > score_board.score >= 100:
                    difficulty = 1
                    win_menu.score = score_board.score
                    playing = False
                    win = True
                elif 300 > score_board.score >= 200:
                    difficulty = 2
                elif 350 > score_board.score >= 300:
                    difficulty = 3
                elif score_board.score >= 350:
                    win_menu.score = score_board.score
                    playing = False
                    win = True

                # 如果敌人全都寄了，就再召唤一批
                if len(enemy) == 0:
                    spawn_simple_enemy([enemy, all_objects], [self.enemy_image], difficulty)

                # 这里是绘制所有物体
                all_objects.clear(self.screen, self.background)
                dirty_rects.extend(all_objects.draw(self.screen))

            # 绘制帧率(如果设置了要显示帧率)
            if show_fps:
                fps_view.fps = "{:.2f}".format(clock.get_fps())
            else:
                fps_view.image = pygame.Surface((0, 0))

            # 玩家死后只允许部分内容（after_player_dead组中的）被更新
            if not playing and not win:
                after_player_dead.update(diff / 1000)
                dirty_rects.extend(after_player_dead.draw(self.screen))

            if not playing and win:
                after_player_win.update(diff / 1000)
                dirty_rects.extend(after_player_win.draw(self.screen))

            if paused:
                paused_objects.clear(self.screen, self.background)
                paused_objects.update(diff / 1000)
                dirty_rects.extend(paused_objects.draw(self.screen))

            pygame.display.update(dirty_rects)
            # 根据配置限制帧率
            if MAX_RATE is not None:
                diff = clock.tick(MAX_RATE)
            else:
                # 只计算上一帧到这一帧的时间间隔，不等待
                diff = clock.tick()

    def replay_game(self, *args):
        self.running = False
        self.start()


def main():
    game = MainApp()
    game.start()
    pygame.quit()


if __name__ == '__main__':
    main()
