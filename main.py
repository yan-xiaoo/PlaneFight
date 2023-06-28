import math
import random
import threading
import time

import pygame.sprite

import resource
import widget
from configure import *

if not pygame.get_init():
    pygame.init()
# 窗口的尺寸（宽，高）
SCREEN_RECT = pygame.rect.Rect(0, 0, 640, 480)

# 规定普通飞机不同难度下的数据
# speed: 该难度下飞机速度的上下限（像素/秒）
# batch: 该难度下一次出飞机数量的上下限
# full_time: 飞机出场时具有一小段无敌时间（防止被爆炸连环炸干净）
# fire: 飞机能否可开火
# chase: 飞机子弹是否可追踪玩家
DIFFICULTY = {0: {'speed': (150, 200), "batch": (1, 3), "full_time": 0.5, "fire": False, "chase": False},
              1: {'speed': (175, 225), "batch": (2, 4), "full_time": 0.4, "fire": False, "chase": False},
              2: {'speed': (175, 250), "batch": (2, 5), "full_time": 0.3, "fire": True, "chase": False},
              3: {'speed': (175, 250), "batch": (3, 5), "full_time": 0.25, "fire": True, "chase": True},
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
        if isinstance(images, pygame.Surface):
            images = [images]
        self.images = images
        self.image_number = 0
        self.image = images[self.image_number]
        self.rect = self.image.get_rect()
        self.rect.center = center
        # 每隔多久轮播一次图片，单位：秒
        if not isinstance(change_time, float):
            self.total_change_time = 0.2
        else:
            self.total_change_time = change_time
        self.change_time = self.total_change_time

    def update(self, dt, *args) -> None:
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

    def __init__(self, images, center, fire=None, *group):
        super().__init__(images, center, None, *group)
        # 减小玩家的碰撞箱，降低撞到敌机的可能
        self.rect.width = 60
        self.rect.height = 40
        # 图片视觉上中心与rect中心不一致，需要修正rect的位置
        # 记住！！更改飞机图片后要再次校准！
        self.rect.centerx += 15
        # 速度：300像素每秒
        self.speed = 300
        # 飞机的尾焰，在飞机向上飞行时才会出现
        # 注意：更改尾焰图片后要再次校准！
        self.fire_sprite = CommonSprite([fire], (self.rect.centerx, self.rect.centery + 35))
        # 开火cd，单位：秒
        self.total_fire_cd = 0.25
        self.fire_cd = 0

    # noinspection PyTypeChecker
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
        # clamp是指把自己的矩形限制在屏幕矩形内，可以防止自己飞出屏幕
        self.rect = self.rect.clamp(SCREEN_RECT)
        # 如果飞机在向上飞，就渲染尾焰
        if horizontal_direction == -1:
            self.groups()[0].add(self.fire_sprite)
            self.fire_sprite.rect.centerx = self.rect.centerx + 30
            self.fire_sprite.rect.centery = self.rect.centery + 75
        # 飞机不向上飞了，把尾焰从渲染组(all_objects)里移除掉
        else:
            self.groups()[0].remove(self.fire_sprite)

    def kill(self):
        # 玩家死亡时，把尾焰也移除掉
        # 不然向上飞行的时候死掉会有个尾焰留下来
        self.fire_sprite.kill()
        # 必须先干掉尾焰，再干掉自己
        super().kill()

    def fire(self, images, *group) -> None:
        """
        我方开火
        :param images: 子弹图片
        :param group: 子弹所要添加到的组，可以有任意多个
        :return: 无
        """
        if self.fire_cd <= 0:
            self.fire_cd = self.total_fire_cd
            # 生成子弹
            PlayerBullet(images, self.rect.midtop, *group)

    def update(self, dt, *args):
        super().update(dt, *args)
        self.fire_cd -= dt


class Enemy(CommonSprite):
    """
    代表敌人的飞机
    """

    def __init__(self, images: list[pygame.Surface], *group):
        """
        生成一个敌机
        :param images: 敌机图片，必须是个列表，可以只有一张。多于一张时，图片将会轮播
        :param group: 该精灵所要添加到的组，可以有任意多个
        """
        super().__init__(images, (SCREEN_RECT.width * random.random(), 0), None, *group)
        # 减小敌机的碰撞箱，降低撞到玩家的可能
        # 由于敌机有很多种可能的图片，这里将它们的碰撞箱统一为80x60
        self.rect.width = 80
        self.rect.height = 60

        # 以下的数据全部在spawn_simple_enemy中被更改
        # __init__不接受用于更改这些参数的输入
        # 速度：100-200像素每秒,玩的就是随机，玩的就是刺激
        self.speed = random.randint(100, 200)
        # 为防止敌机出来就死（被连锁爆炸干掉），给点无敌时间
        self.full_time = 0.5
        # 敌机如果能发射子弹的话，其子弹的冷却时间
        self.fire_cd = self.total_fire_cd = 1
        # 敌机发射过的子弹
        # 存储这些子弹的信息可以做到在敌机死亡时清除它发射过的子弹
        self.bullets = []
        # 发射的子弹是否为追踪弹
        self.chase = False

    def update(self, dt, *args) -> None:
        """
        更新敌人的状态，这个敌人只会从上向下飞，不会蛇皮走位
        :param dt: 两次调用该函数的间隔（用来计算应当移动的距离）
        :return:无
        """
        super().update(dt, *args)
        self.full_time -= dt
        self.fire_cd -= dt
        self.rect.move_ip(0, self.speed * dt)
        # 如果敌机向下飞出屏幕，就把它删掉
        if self.rect.top >= SCREEN_RECT.bottom:
            self.kill()
        # 校正敌机位置，防止它出现半边跑出屏幕的情况
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_RECT.right:
            self.rect.right = SCREEN_RECT.right

    def fire(self, images, *group) -> None:
        """
        敌机发射子弹。
        如果该难度下敌机不允许发射子弹，那么spawn_simple_enemy函数会用一个接受两个参数但啥也不干的函数代替本函数，
        以禁用开火功能
        :param images: 子弹图片，需要是列表，可以只有一张。存在多张时轮播
        :param group: 子弹所要添加到的组，可以有任意多个
        :return: 无
        """
        # 当开火cd为0时，才能开火
        if self.fire_cd <= 0:
            self.fire_cd = self.total_fire_cd
            # 如果允许飞机发射追踪弹，则产生追踪弹
            if self.chase:
                # 那个0.75表示追踪0.75秒后不再追踪
                self.bullets.append(HardEnemyBullet(images, self.rect.center, 0.75, *group))
            else:
                self.bullets.append(EnemyBullet(images, self.rect.center, *group))

    def kill(self):
        """
        敌机死亡时调用，先清除它发射过的子弹，再清除它自己
        为啥要清除发射过的子弹？因为满屏追踪弹的话作者本人打不过
        :return:
        """
        # 清除敌机发射过的子弹
        for one_bullet in self.bullets:
            one_bullet.kill()
        # 必须先清除子弹，再清除自己
        super().kill()


class Boss(CommonSprite):
    """
    可怕的大boss
    """

    def __init__(self, images, bullet_image, fire_ball_image, large_fireball_image, group, bullet_group, no_disappear_bullet_group, boss_group, plane_images):
        super().__init__(images, (SCREEN_RECT.width / 2, 100), None, *group)
        # 减小敌机的碰撞箱，降低撞到玩家的可能
        self.left_limit = 0
        self.right_limit = SCREEN_RECT.width

        self.rect.width = 80
        self.rect.height = 60

        self.direction = 1

        self.skills = {1: self.chase_fire, 2: self.fire_balls, 3: self.many_bullets, 4: self.normal_attack,
                       5: self.large_fireball, 6: self.plane_attack}
        self.skill_total = [5, 7, 10, 12.5, 15, 35]
        self.skill_cds = [5, 7, 10, 12.5, 15, 20]
        self.total_main_cd = 6
        self.main_cd = 0

        self.bullet_image = bullet_image
        self.bullet_group = bullet_group
        self.fire_ball_image = fire_ball_image
        self.boss_group = boss_group
        self.no_disappear_bullet_group = no_disappear_bullet_group
        self.large_fireball_image = large_fireball_image
        self.player_position = None
        self.plane_images = plane_images

    def update(self, dt, player_position=None, *args, **kwargs) -> None:
        super().update(dt)
        self.player_position = player_position
        self.rect.move_ip(random.randint(0, 200) * dt * self.direction, 0)
        if self.rect.right >= self.right_limit:
            self.rect.right = self.right_limit
            self.direction = -self.direction
        if self.rect.left <= self.left_limit:
            self.rect.left = self.left_limit
            self.direction = -self.direction
        self.rect.clamp(SCREEN_RECT)

        for i in range(len(self.skill_cds)):
            self.skill_cds[i] -= dt
        self.main_cd -= dt

        available = []
        for i in range(len(self.skill_cds)):
            if self.skill_cds[i] <= 0:
                available.append(i + 1)
        if available and random.random() < 0.1 and self.main_cd <= 0:
            ch = random.choice(available)
            threading.Thread(target=self.skills[ch], daemon=True).start()
            self.skill_cds[ch - 1] = self.skill_total[ch - 1]
            self.main_cd = self.total_main_cd

    def chase_fire(self):
        """
        追踪弹发射
        """
        HardEnemyBullet(self.bullet_image, (self.rect.centerx - 30, self.rect.centery), 1.5,
                        *self.bullet_group).speed = 300
        HardEnemyBullet(self.bullet_image, (self.rect.centerx + 30, self.rect.centery), 1.5,
                        *self.bullet_group).speed = 300
        HardEnemyBullet(self.bullet_image, (self.rect.centerx, self.rect.centery), 1.5,
                        *self.bullet_group).speed = 300

    def fire_balls(self):
        """
        发射火球
        """
        for i in range(0, 360, 20):
            FireBall(self.fire_ball_image, self.rect.center, (math.cos(math.radians(i)), math.sin(math.radians(i))),
                     self.boss_group,
                     *self.bullet_group)

    def normal_attack(self):
        """
        普通攻击，持续5秒内向前发射一颗子弹
        :return: 无
        """
        for i in range(10):
            EnemyBullet(self.bullet_image, (self.rect.centerx, self.rect.centery), *self.bullet_group)
            time.sleep(0.75)

    def many_bullets(self):
        """发射大量子弹"""
        for i in range(0, 25):
            if self.player_position is not None:
                dis = math.sqrt((self.player_position[0] - self.rect.centerx) ** 2 + (
                        self.player_position[1] - self.rect.centery) ** 2)
                x = (self.player_position[0] - self.rect.centerx) / dis
                y = (self.player_position[1] - self.rect.centery) / dis
            else:
                x = 0
                y = 1
            a = FireBall(self.bullet_image, (self.rect.centerx - 30, self.rect.centery), (x, y), self.boss_group,
                         *self.bullet_group)
            b = FireBall(self.bullet_image, (self.rect.centerx, self.rect.centery), (x, y), self.boss_group,
                         *self.bullet_group)
            c = FireBall(self.bullet_image, (self.rect.centerx + 30, self.rect.centery), (x, y), self.boss_group,
                         *self.bullet_group)
            a.speed = b.speed = c.speed = 300
            time.sleep(0.05)

    def large_fireball(self):
        """
        小火球不够。我们要更大，更大，更大的大大大大大大火球！
        :return: 无
        """
        LargeFireBall(self.large_fireball_image, self.rect.center, self, self.boss_group, *self.no_disappear_bullet_group)

    def plane_attack(self):
        """
        替身攻击！
        :return: 无
        """
        self.left_limit = 120
        self.right_limit = SCREEN_RECT.width - 120
        BossPlane(random.choice(self.plane_images), (50, 100), self, self.no_disappear_bullet_group,
                  self.bullet_image, self.bullet_group)
        BossPlane(random.choice(self.plane_images), (SCREEN_RECT.width - 50, 100), self, self.no_disappear_bullet_group,
                  self.bullet_image, self.bullet_group)
        time.sleep(15)
        self.left_limit = 0
        self.right_limit = SCREEN_RECT.width


class FireBall(CommonSprite):
    """大火球！"""

    def __init__(self, images, center, position, boss_group, *group):
        super().__init__(images, center, boss_group, *group)
        self.speed = 300
        self.position = position

    def update(self, dt, *args) -> None:
        super().update(dt)
        self.rect.move_ip(self.speed * dt * self.position[0], self.speed * dt * self.position[1])
        if self.rect.top > SCREEN_RECT.bottom or self.rect.bottom < SCREEN_RECT.top or self.rect.left > SCREEN_RECT.right or self.rect.right < SCREEN_RECT.left:
            self.kill()


class LargeFireBall(CommonSprite):
    def __init__(self, images, center, boss, boss_group, *group):
        super().__init__(images, center, boss_group, *group)
        self.speed = 0
        self.a = 500  # 加速度: 500像素每秒
        self.stay_time = 1.5
        self.stay = True
        self.boss = boss
        self.towards = [0, 1]

    def update(self, dt, player_position=None, *args) -> None:
        super().update(dt)
        self.stay_time -= dt
        if self.stay_time <= 0:
            if self.stay:
                self.stay = False
                self.towards[0] = (player_position[0] - self.rect.centerx) / math.sqrt(
                    (player_position[0] - self.rect.centerx) ** 2 + (player_position[1] - self.rect.centery) ** 2)
                self.towards[1] = (player_position[1] - self.rect.centery) / math.sqrt(
                    (player_position[0] - self.rect.centerx) ** 2 + (player_position[1] - self.rect.centery) ** 2)

            self.speed += self.a * dt
            self.rect.move_ip(self.speed * dt * self.towards[0], self.speed * dt * self.towards[1])
        else:
            self.rect.update(self.boss.rect)
        if self.rect.top > SCREEN_RECT.bottom:
            self.kill()


class BossPlane(Enemy):
    """
    Boss召唤出的小替身飞机，无敌，一段时间后自动死亡
    """
    def __init__(self, images, center, boss: Boss, group, bullet_images, bullet_group):
        super().__init__(images, *group)
        self.rect.center = center
        self.live_time = 15
        self.boss = boss
        self.fire_cd = self.total_fire_cd = 1
        self.chase = False
        self.bullet_image = bullet_images
        self.bullet_group = bullet_group

    def update(self, dt, *args):
        self.live_time -= dt
        self.fire_cd -= dt
        if self.live_time <= 0:
            self.kill()
        self.fire(self.bullet_image, self.bullet_group)


class Explosion(CommonSprite):
    """
    爆炸特效
    在我方或敌方飞机坏掉的时候都会出现该特效
    由于敌方飞机可能会叠起来出，因此爆炸特效还有个功能：爆炸特效在产生0.05s内会摧毁所有碰撞到特效的敌机
    （问就是为了降低难度）
    """

    def __init__(self, images, center, *group):
        """
        创建一个爆炸特效
        :param images: 爆炸特效图片，必须是个列表，可以只有一张。多于一张时，图片将会轮播
        :param center: 爆炸特效的中心位置
        :param group: 爆炸特效所要添加到的组，可以有任意多个
        """
        # 爆炸特效是由一张图片和它的倒过来的图片轮播产生的
        # 轮播时间固定为0.2
        super().__init__(images, center, 0.2, *group)
        self.life_time = 0.5  # 单位：秒
        # 测试中发现一个bug，由于后期飞机飞行速度过快，导致后出来的所有飞机全都被爆炸特效炸没了
        # 所以加了一个时间限制，爆炸特效仅会在这段时间内引发连锁爆炸
        # 剩下的0.45秒只有特效，不会再摧毁敌机
        # 这个chain_time是在主函数里调用并判断是否要连锁爆炸的
        self.chain_time = 0.05

    def update(self, dt, *args):
        """
        更新爆炸特效的状态，从出现到消失
        :param dt: 每两次调用间隔
        :return: 无
        """
        super().update(dt, *args)
        self.life_time -= dt
        self.chain_time -= dt
        # 如果爆炸特效的持续时间到了，就删了
        if self.life_time <= 0:
            self.kill()


class PlayerBullet(CommonSprite):
    """
    我方用来击打敌方的子弹
    为啥敌我子弹要区分呢？因为它们的飞行方向不一样
    而且我方可没有追踪弹这种开挂级别的东西（
    """

    def __init__(self, images, center, *group):
        center = list(center)
        # 因为我方飞机图片中心与实际矩形中心不准，要进行发射位置的校准
        # 更换飞机图片之后改这里
        center[0] = center[0] + 25
        super().__init__(images, center, None, *group)
        # 速度：500像素/秒 方向：上
        self.speed = -500

    def update(self, dt, *args) -> None:
        super().update(dt, *args)
        # 向上以每秒500像素的速度飞行
        self.rect.move_ip(0, self.speed * dt)
        # 如果飞出屏幕边界，就删了
        # 因为它只能向上飞，不存在从左/右侧离开了屏幕的情况
        if self.rect.bottom < SCREEN_RECT.top:
            self.kill()


class EnemyBullet(CommonSprite):
    """
    敌方飞机可以发射的子弹
    这种是不追踪的，直线飞行。该类有一个子类是可以追踪我方的
    """

    def __init__(self, images, center, *group):
        center = list(center)
        # 因为敌方飞机图片中心与实际矩形中心不准，要进行发射位置的校准
        center[0] = center[0] + 15
        center[1] = center[1] + 50
        super().__init__(images, center, None, *group)
        # 速度：300像素/秒 方向：下
        # 注：pygame的y轴是以向下为正向
        self.speed = 300

    def update(self, dt, *args) -> None:
        super().update(dt, *args)
        self.rect.move_ip(0, self.speed * dt)
        # 因为这种子弹只会向下走，只需要看它是否从下侧离开屏幕就行了
        if self.rect.top >= SCREEN_RECT.bottom:
            self.kill()


class HardEnemyBullet(EnemyBullet):
    """
    敌方飞机可以发射的追踪弹
    该子弹会追踪我方飞机，原理为：每帧获取我方飞机的位置，并计算自己应当向哪个方向飞行
    简直是战神级别，把作者打死了好多次（
    """

    def __init__(self, images, center, chase_time: float = None, *group):
        super().__init__(images, center, *group)
        # 子弹仅在一段时间内可以追踪我方
        # 要是一直能追踪我方就真成超级战神了
        if chase_time is None:
            chase_time = 0.75
        self.chase_time = chase_time
        # 这个用来存储追踪的最后一帧的方向，子弹失去追踪特性之后会一直沿这个方向飞行
        self.dx = self.dy = None
        self.speed = 225

    def update(self, dt: float, player_position: tuple[float, float] = None, *args) -> None:
        # 如果没有传入我方飞机的位置，就不追踪了，直接按普通子弹的方法飞行
        if player_position is None:
            super().update(dt)
            return
        if self.chase_time <= 0:
            # 追踪时间到了，就不追踪了，直接按追踪最后一帧确定的方向飞行
            # 这里提前判断self.chase_time，假如子弹不追踪了，就能少点计算量
            self.rect.move_ip(self.dx, self.dy)
        else:
            # 如果有传入我方飞机的位置，就追踪
            self.chase_time -= dt
            # dis是子弹到我方的距离，用来求cosa与sina
            dis = math.sqrt((self.rect.centerx - player_position[0]) ** 2 +
                            (self.rect.centery - player_position[1]) ** 2)
            # dx 相当于cosa * ds, dy相当于sina * ds
            # ds是一帧内子弹可以移动的长度
            dx = self.speed * dt * (player_position[0] - self.rect.centerx) / dis
            dy = self.speed * dt * (player_position[1] - self.rect.centery) / dis
            # 如果子弹追踪时间没有结束，就按计算出的方向移动
            if self.chase_time >= 0 and self.dx is None and self.dy is None:
                self.rect.move_ip(dx, dy)
            # 子弹的追踪时间刚刚结束，还没有存储最后一帧的信息，就存一下最后一帧子弹运行的方向
            elif self.dx is None and self.dy is None:
                self.dx = dx
                self.dy = dy
                self.rect.move_ip(dx, dy)
        # 如果子弹出界就删掉
        if self.rect.top >= SCREEN_RECT.bottom or self.rect.bottom <= SCREEN_RECT.top or \
                self.rect.left >= SCREEN_RECT.right or self.rect.right <= SCREEN_RECT.left:
            self.kill()

    def weak_chase(self, dt: float, player_position: tuple[float, float]) -> None:
        """
        实现子弹追踪，但这种追踪没有上面那种紧
        这个方法目前没有追踪子弹使用，单纯先写出来记录一下
        方法原理如下：子弹仅仅沿着x/y轴正负向移动。当子弹在x轴方向与我的距离大于在y轴方向时，仅在x轴上向我靠近。y轴同理
        很明显，这种折线追踪法比起上面那种直线追踪法要弱一些
        :param dt: 每两次调用的间隔
        :param player_position: 我方飞机的位置
        :return: 无
        """
        # 如果子弹在y轴方向与我的距离大于在x轴方向时，仅在y轴上向我靠近
        if abs(self.rect.centery - player_position[1]) > abs(self.rect.centerx - player_position[0]):
            # modifier表示子弹在我方上面还是下面, 1表示在下面，-1表示在上面
            modifier = -1 if self.rect.centery > player_position[1] else 1
            # 仅仅在y轴上移动
            self.rect.move_ip(0, self.speed * dt * modifier)
        else:
            # -1: 在右边，1: 在左边
            modifier = -1 if self.rect.centerx > player_position[0] else 1
            # 仅仅在x轴上移动
            self.rect.move_ip(self.speed * dt * modifier, 0)


class ScoreBoard(widget.Text):
    """
    记分板，左上角那个显示分数的东西
    记分板用法：直接更改self.score，记分板会自动重新渲染
    """

    def __init__(self, center, font='arial', *group):
        """
        创建一个记分板
        :param center: 记分板的中心位置
        :param font:  记分板的字体，可以是加载好的pygame.font.Font，也可以是字体文件的路径
        :param group: 记分板所在的组
        """
        self._score = 0
        super().__init__(text=f"Score: {self._score}", center=center, font=font, color=(255, 0, 0), font_size=30,
                         group=group)
        self.score = 0

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self._score = new_score
        # 由于该类继承widget.Text，所以更改text属性，字会自动重新渲染
        self.text = f"Score: {self._score}"


class FPSView(widget.Text):
    """
    用来显示FPS的控件，游戏中左下角那个
    用法：直接更改self.fps，控件会自动重新渲染
    """

    def __init__(self, center, font='arial', *group):
        """
        创建一个FPS显示控件
        :param center: 控件的中心位置
        :param font: 控件的字体，可以是加载好的pygame.font.Font，也可以是字体文件的路径
        :param group: 控件所在的组
        """
        # 先放一个差不多长度的字符串作为待渲染字符串，方便计算控件rect的大小
        super().__init__(text="FPS: 0", center=center, font=font, color=(0, 0, 255), font_size=30, group=group)
        self.fps = 0

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, new_fps):
        self._fps = new_fps
        # 由于该类继承widget.Text，所以更改text属性，字会自动重新渲染
        self.text = f"FPS: {self._fps}"


class BossHealthBar(widget.Text):
    """
    用来显示boss血量的控件
    用法：直接更改self.health，控件会自动重新渲染
    """

    def __init__(self, center, health, font='arial', *group):
        """
        创建一个boss血量显示控件
        :param center: 控件的中心位置
        :param font: 控件的字体，可以是加载好的pygame.font.Font，也可以是字体文件的路径
        :param group: 控件所在的组
        """
        # 先放一个差不多长度的字符串作为待渲染字符串，方便计算控件rect的大小
        super().__init__(text="Health: 100%", center=center, font=font, color=(255, 0, 0), font_size=30, group=group)
        self.total_health = health
        self._health = health

    @property
    def health(self):
        return self._health

    @health.setter
    def health(self, new_health):
        if self._health == new_health / self.total_health * 100:
            return
        self._health = new_health / self.total_health * 100
        # 由于该类继承widget.Text，所以更改text属性，字会自动重新渲染
        self.text = "Health: {:.1f}%".format(self._health)


class Background(pygame.sprite.Sprite):
    """
    背景类，用来实现背景滚动
    """

    def __init__(self, image: pygame.Surface, speed, *groups: pygame.sprite.Group):
        """
        创建一个背景
        :param image: 背景图片
        :param speed: 背景滚动的速度，单位为像素/秒
        :param groups: 背景所在的组
        """
        super().__init__(*groups)
        self.image = image
        self.rect = self.image.get_rect()
        self.speed = speed

    def update(self, dt: float, *args) -> None:
        """
        更新背景位置
        :param dt: 每两次调用的间隔
        :return: 无
        """
        self.rect.top += self.speed * dt
        if self.rect.top >= SCREEN_RECT.bottom:
            self.rect.top = 0


def spawn_simple_enemy(groups: list[pygame.sprite.Group], images: list[pygame.Surface], difficulty: int = 0) -> None:
    """
    以difficulty为难度等级召唤出amount个普通飞机敌人（不是boss）加入groups中
    :param images: 这些敌人所使用的一些图片,每个敌人仅会用一张图片，不同敌人的图片可能不同
    :param groups: 这些召唤出的敌人需要被加入的组
    :param difficulty: 这些召唤的敌人的难度，详情见difficulty字典边上的注释。难度影响飞机速度的上下限,一批飞机多少，飞机是否可发弹，飞机是否可发追踪弹等
    :return: 无
    """
    # 用for循环计数，生成difficulty字典中对应的数量上下限之间数量的飞机
    for _ in range(random.randint(*DIFFICULTY[difficulty]['batch'])):
        # 游戏为敌机准备了多种图片，这里给每一架飞机都随便选一张
        e = Enemy([random.choice(images)], *groups)
        # 速度填写成difficulty规定的上下限间的随机数
        e.speed = random.randint(*DIFFICULTY[difficulty]['speed'])
        e.full_time = DIFFICULTY[difficulty]['full_time']
        # 如果难度不允许飞机攻击，则禁用攻击方法
        # 用一个接受无限个参数但啥也不干的函数替代掉飞机的fire方法
        if not DIFFICULTY[difficulty]['fire']:
            e.fire = lambda *a: a
        e.chase = DIFFICULTY[difficulty]['chase']
        if e.chase:
            e.total_fire_cd = e.fire_cd = 1.5


class MainApp:
    """
    游戏主程序
    """

    def __init__(self):
        """
        加载游戏资源，创建游戏屏幕
        """
        # 屏幕，在多局游戏中重复使用
        self.screen = pygame.display.set_mode(SCREEN_RECT.size, 0,
                                              pygame.display.mode_ok(SCREEN_RECT.size, 0, 32))
        pygame.display.set_caption("飞机大战")
        # 这张图是示例里的aliens.py用的，感觉很适合主题就拿来了
        self.background_image = resource.load("./data/background.gif", True)
        self.background = pygame.surface.Surface(SCREEN_RECT.size)

        # 加载游戏资源，这样重新开始游戏时不用再加载了
        self.plane_image = resource.load("./data/plane_1.png", True).convert_alpha()
        self.enemy_images = [resource.load(f"./data/enemy_{i}.png", True).convert_alpha() for i in range(1, 4)]
        self.boss_image = resource.load(f"./data/boss.png", True).convert_alpha()
        self.total_boss_health = 100
        self.boss_health = 100
        self.boss_fight = False

        self.explosion_image = resource.load("./data/explosion_1.gif", True).convert_alpha()
        self.shot_image = resource.load('./data/shot.gif', True).convert_alpha()

        self.fire_ball_image = resource.load("./data/fire_ball.png", False, self.shot_image).convert_alpha()
        self.large_fireball_image = resource.load("./data/fireball_128.png", False, self.shot_image).convert_alpha()

        # 加载即使丢失也能用其他资源代替的资源
        self.fire_image = resource.load("data/fire.png", False, pygame.Surface((0, 0))).convert_alpha()
        # 这两个用的是字体，但大小不同
        self.font = resource.load("./data/Kenney Pixel.ttf", False, pygame.font.SysFont("arial", 30), 45)
        self.font_large = resource.load("./data/Kenney Pixel.ttf", False, pygame.font.SysFont("arial", 45), 80)

        # 加载音乐
        self.shot_sound = resource.load("./data/car_door.wav", False, None)
        if self.shot_sound is not None:
            self.shot_sound.set_volume(0.1)

        # 这个控制变量很特殊，必须放在start外面，不然实现不了重玩
        self.running = False

    def start(self):
        # 由于这张图片特别窄（左右距离小），但左右侧衔接很自然，所以不断从左向右绘制该图片，直至它填满屏幕
        for tile in range(0, SCREEN_RECT.width, self.background_image.get_width()):
            # blit:把self.background_image画到self.background这个画布上，位置是(tile, 0)
            self.background.blit(self.background_image, (tile, 0))
        # 把self.background画到self.screen上,相当于直接把背景涂上去
        # 背景的绘制必须每局游戏前都来一次，不然会发现上局游戏的飞机和爆炸特效啥的还留在这当背景（
        self.screen.blit(self.background, (0, 0))
        # 先更新一次屏幕
        pygame.display.flip()

        # 加载背景音乐，并尝试播放
        resource.load_bgm("./data/mus_anothermedium.ogg", False)
        try:
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

        # 初始化游戏控制内容
        # 初始处于运行状态
        self.running = True
        # 初始没有暂停
        paused = False
        # 初始游戏没有结束
        playing = True
        # 初始没有胜利
        win = False
        # 初始不全屏
        fullscreen = False
        # 调试模式
        debug = False
        # 存放在游戏正常运行时所有需要更新的对象
        all_objects = pygame.sprite.RenderUpdates()
        # 存放需要在玩家死后更新的对象，一般是爆炸特效和失败界面，平时不会更新这些内容
        after_player_dead = pygame.sprite.RenderUpdates()
        # 存放玩家胜利后还需要更新的对象，一般只有胜利界面
        after_player_win = pygame.sprite.RenderUpdates()
        # 存放暂停时允许更新的对象，一般只有帧率显示器和暂停界面
        paused_objects = pygame.sprite.RenderUpdates()

        boss_render_group = pygame.sprite.RenderUpdates()
        # 用于控制帧率
        clock = pygame.time.Clock()
        # 初始不展示帧率
        show_fps = False
        # 每帧间隔，初始设为0
        diff = 0

        # 初始化游戏对象
        # 记分板
        score_board = ScoreBoard((70, 50), self.font, all_objects)
        # 胜利界面
        # 先写个差不多长度的文字，反正不显示（因为需要在创建时计算rect的位置）
        widget.Text(text="You Win! Score: 0", center=SCREEN_RECT.center, font=self.font_large,
                    color=(255, 0, 0),
                    font_size=50,
                    group=[after_player_win])
        # 失败界面
        widget.Text(text="You Lose!", center=SCREEN_RECT.center, font=self.font_large, color=(255, 0, 0), font_size=50,
                    group=[after_player_dead])  # 仅在失败界面展示
        # 暂停界面
        widget.Text(text="Paused", center=SCREEN_RECT.center, font=self.font_large, color=(0, 0, 255), font_size=50,
                    group=[paused_objects])  # 仅在暂停时展示
        # 重玩按钮
        widget.Button(center=(SCREEN_RECT.centerx, SCREEN_RECT.centery + 100), text="Replay",
                      group=[after_player_win, after_player_dead],
                      font=self.font,
                      command=self.replay_game)  # 在胜利或失败界面展示
        # 用于显示帧率的对象
        fps_view = FPSView((50, SCREEN_RECT.height - 35), self.font, all_objects, paused_objects)
        # 血条
        health_bar = BossHealthBar((SCREEN_RECT.width / 2, 25), self.total_boss_health, self.font, boss_render_group,
                                   after_player_dead, after_player_win)
        # 难度，默认为0
        difficulty = 0
        # 玩家
        player = Player([self.plane_image], SCREEN_RECT.center, self.fire_image, all_objects)
        # 敌人
        enemy = pygame.sprite.Group()
        # 爆炸特效
        explosion_group = pygame.sprite.Group()
        # 子弹
        player_bullet_group = pygame.sprite.Group()
        # 敌方子弹组
        enemy_bullet_group = pygame.sprite.Group()
        # 碰到我方也不会消失的子弹组
        enemy_no_disappear_group = pygame.sprite.Group()
        # boss
        boss_group = pygame.sprite.Group()
        # 我方与敌方子弹组分开是为了方便碰撞检测
        multi_keys = []

        # 游戏正式开始
        while self.running:
            # 每一帧待更新的区域
            dirty_rects = []
            # 这部分专门处理事件
            events = pygame.event.get(pygame.QUIT)
            if events:
                # 在一轮循环结束后退出游戏
                self.running = False
            multi_keys = [] if pygame.K_b and pygame.K_u and pygame.K_g in multi_keys else multi_keys
            for key_event in pygame.event.get(pygame.KEYDOWN):
                # 如果按下的按键为配置文件中的暂停键，那么切换暂停状态
                # 只有游戏没有结束（没有输赢）的时候才能暂停
                multi_keys.append(key_event.key)
                if key_event.key == PAUSE_KEY and playing:
                    paused = not paused
                if key_event.key == FPS_KEY:
                    show_fps = not show_fps
                if key_event.key == QUIT_KEY:
                    self.running = False
                if key_event.key == FULL_KEY:
                    # 进行强制暂停，防止玩家在切换屏幕的时候寄掉
                    if playing:
                        paused = True
                    if not fullscreen:
                        screen_backup = self.screen.copy()
                        self.screen = pygame.display.set_mode(SCREEN_RECT.size, pygame.FULLSCREEN,
                                                              pygame.display.mode_ok(SCREEN_RECT.size,
                                                                                     pygame.FULLSCREEN, 32)
                                                              )
                        self.screen.blit(screen_backup, (0, 0))
                    else:
                        screen_backup = self.screen.copy()
                        self.screen = pygame.display.set_mode(SCREEN_RECT.size, 0,
                                                              pygame.display.mode_ok(SCREEN_RECT.size, 0, 32))
                        self.screen.blit(screen_backup, (0, 0))
                    fullscreen = not fullscreen
                    # 切换屏幕后绘制一帧，不然除了那个暂停界面之外其他屏幕都是黑的
                    dirty_rects.extend(all_objects.draw(self.screen))

            if pygame.K_b in multi_keys and pygame.K_u in multi_keys and pygame.K_g in multi_keys:
                print("debug")
                debug = not debug
            # 暂停时相当于除了处理时间外，其他所有内容停止运行
            # 这里检查目前是否在暂停，如果不在暂停才令游戏运行
            # 下面是游戏循环主要内容：
            if not paused and playing:
                # 清除可能存在的暂停界面，不然会很难看
                paused_objects.clear(self.screen, self.background)
                keys_pressed = pygame.key.get_pressed()
                # 玩家移动, 注意diff单位为毫秒
                # 这里加减可以实现：按住a与d时不动，只按a/只按d才动
                player.move(keys_pressed[pygame.K_d] - keys_pressed[pygame.K_a]
                            + keys_pressed[pygame.K_RIGHT] - keys_pressed[pygame.K_LEFT],
                            keys_pressed[pygame.K_s] - keys_pressed[pygame.K_w]
                            + keys_pressed[pygame.K_DOWN] - keys_pressed[pygame.K_UP],
                            diff / 1000)

                # 更新所有非暂停时更新的游戏对象
                all_objects.update(diff / 1000, player.rect.center)

                # 以下为碰撞检测
                # 四个部分： 玩家与敌机的碰撞，玩家与敌方子弹的碰撞，敌机与我方子弹的碰撞，敌机与爆炸特效的碰撞

                # 如果玩家撞到敌机，游戏结束
                for one_enemy in pygame.sprite.spritecollide(player, enemy, True):
                    # 在敌机的中心位置生成爆炸特效
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              one_enemy.rect.center,
                              after_player_dead, explosion_group)
                    # 在玩家的中心位置生成爆炸特效
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              player.rect.center,
                              after_player_dead, explosion_group)
                    # 玩家死亡, 调试模式下无敌
                    if not debug:
                        player.kill()
                        playing = False

                # 如果敌方子弹撞到玩家，游戏结束
                for one_enemy in pygame.sprite.spritecollide(player, enemy_bullet_group, True):
                    # 在玩家的中心位置生成爆炸特效
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              (player.rect.centerx + 15, player.rect.centery),
                              after_player_dead, explosion_group, all_objects)
                    one_enemy.kill()
                    if not debug:
                        player.kill()
                        playing = False

                # 下面这两部分为：敌机尝试开火，玩家尝试使用键盘开火
                # 敌机开火
                for one_enemy in enemy.sprites():
                    one_enemy.fire([pygame.transform.flip(self.shot_image, 1, 1)], all_objects, enemy_bullet_group)

                # 玩家开火
                # 鼠标控制开火:
                # 只要鼠标左键按下并且cd为0，就可以开火
                # 这样只要一直按住鼠标左键就能一直用最大速度开火
                if keys_pressed[FIRE_KEY] or pygame.mouse.get_pressed(3)[0]:
                    player.fire([self.shot_image], player_bullet_group, all_objects)
                    if self.shot_sound is not None:
                        self.shot_sound.play()

                # 玩家子弹与敌机的碰撞检测
                for one_enemy in pygame.sprite.groupcollide(enemy, player_bullet_group, False, True).keys():
                    # 判断敌机是否无敌
                    if one_enemy.full_time <= 0:
                        # 加分，在敌机中心生成爆炸特效
                        score_board.score += 10
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  one_enemy.rect.center,
                                  all_objects, explosion_group)
                        one_enemy.kill()

                # 敌机与爆炸特效的碰撞检测
                for one_enemy in pygame.sprite.groupcollide(enemy, explosion_group, False, True).keys():
                    # 检查敌机是否无敌
                    if one_enemy.full_time <= 0:
                        # 加分，在敌机中心生成爆炸效果
                        score_board.score += 10
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  one_enemy.rect.center,
                                  all_objects, explosion_group)
                        one_enemy.kill()

                #  判断爆炸特效能引发连锁爆炸的时间是否结束，结束的话就把爆炸特效从可碰撞物体列表里移除
                for explosion_sprite in explosion_group.sprites():
                    if explosion_sprite.chain_time <= 0:
                        explosion_group.remove(explosion_sprite)

                # 检测成绩调整难度
                if 200 > score_board.score >= 100:
                    difficulty = 1
                elif 300 > score_board.score >= 200:
                    difficulty = 2
                elif 350 > score_board.score >= 300:
                    difficulty = 3
                if score_board.score >= 1 and not self.boss_fight:
                    self.boss_fight = True

                # Boss战相关内容
                # 为了减低难度，Boss血量是一个全局变量，跨游戏继承
                # 只要打到了boss，就算死了也会直接进入boss战
                if self.boss_fight and len(boss_group) == 0:
                    # 尝试切换音乐
                    resource.load_bgm("./data/asgore.mp3", False)
                    try:
                        pygame.mixer.music.set_volume(0.3)
                        pygame.mixer.music.play(-1, 0, 5000)
                    except pygame.error:
                        pass
                    Boss(images=[self.boss_image], bullet_image=[pygame.transform.flip(self.shot_image, 1, 1)],
                         fire_ball_image=[self.fire_ball_image], large_fireball_image=self.large_fireball_image, group=(boss_group, boss_render_group),
                         no_disappear_bullet_group=[all_objects, enemy_no_disappear_group, boss_render_group, after_player_dead],
                         bullet_group=[all_objects, enemy_bullet_group, boss_render_group], boss_group=boss_group, plane_images=self.enemy_images)
                # Boss死亡，我方胜利
                if self.boss_health <= 0:
                    Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                              boss_group.sprites()[0].rect.center,
                              all_objects, explosion_group)
                    boss_group.sprites()[0].kill()
                    playing = False
                    win = True
                # Boss存在时的内容
                if self.boss_fight:
                    # 更新boss血条
                    health_bar.health = self.boss_health
                    # 我方子弹cd减少
                    player.total_fire_cd = 0.05

                    # Boss与我方子弹碰撞
                    if pygame.sprite.groupcollide(boss_group, player_bullet_group, False, True):
                        self.boss_health -= 1
                    # Boss与我方碰撞
                    if pygame.sprite.spritecollide(player, boss_group, False):
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  player.rect.center,
                                  after_player_dead, explosion_group, all_objects)
                        if not debug:
                            player.kill()
                            playing = False
                        self.boss_health -= 10
                    # Boss发出的不消失的攻击内容与我方碰撞
                    if pygame.sprite.spritecollide(player, enemy_no_disappear_group, False):
                        Explosion([self.explosion_image, pygame.transform.flip(self.explosion_image, 1, 1)],
                                  player.rect.center,
                                  after_player_dead, explosion_group, all_objects)
                        if not debug:
                            player.kill()
                            playing = False

                # 如果敌人全都寄了，就再召唤一批
                if len(enemy) == 0 and not self.boss_fight:
                    spawn_simple_enemy([enemy, all_objects], self.enemy_images, difficulty)

                # 这里是绘制所有物体
                # 先清除掉上一帧画的东西，再画这一帧的东西
                all_objects.clear(self.screen, self.background)
                # 把这一帧修改了的区域放到脏区域里
                dirty_rects.extend(all_objects.draw(self.screen))
                if self.boss_fight:
                    # 更新Boss相关内容
                    boss_group.update(diff / 1000, player.rect.center)
                    boss_render_group.clear(self.screen, self.background)
                    dirty_rects.extend(boss_render_group.draw(self.screen))

            # 绘制帧率(如果设置了要显示帧率)
            if show_fps:
                fps_view.fps = "{:.2f}".format(clock.get_fps())
            else:
                fps_view.image = pygame.Surface((0, 0))

            # 玩家死后只允许部分内容（after_player_dead组中的）被更新
            if not playing and not win:
                after_player_dead.update(diff / 1000)
                after_player_dead.clear(self.screen, self.background)
                dirty_rects.extend(after_player_dead.draw(self.screen))
                if self.boss_fight:
                    try:
                        pygame.mixer.music.stop()
                    except pygame.error:
                        pass

            # 玩家赢后只允许after_player_win组中的内容被更新
            if not playing and win:
                after_player_win.update(diff / 1000)
                after_player_win.clear(self.screen, self.background)
                dirty_rects.extend(after_player_win.draw(self.screen))

            # 暂停时仅允许paused_objects组中的内容被更新
            if paused:
                paused_objects.clear(self.screen, self.background)
                paused_objects.update(diff / 1000)
                dirty_rects.extend(paused_objects.draw(self.screen))

            # 统一更新脏区域
            pygame.display.update(dirty_rects)
            # 根据配置限制帧率
            if MAX_RATE is not None:
                diff = clock.tick(MAX_RATE)
            else:
                # 只计算上一帧到这一帧的时间间隔，不等待
                diff = clock.tick()

    def replay_game(self, *_) -> None:
        """
        重新开始游戏，被replay按钮调用
        :return:无
        """
        self.running = False
        if self.boss_health == 0:
            self.boss_health = self.total_boss_health
            self.boss_fight = False
        if self.boss_fight:
            # 死亡惩罚
            self.boss_health = min(self.boss_health + 25, self.total_boss_health)
        self.start()


def main():
    game = MainApp()
    game.start()
    pygame.quit()


if __name__ == '__main__':
    main()
