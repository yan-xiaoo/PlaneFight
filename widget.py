# 由于pygame不自带任何GUI组件
# 所以这里自己实现一些常用组件
import pygame


class Text(pygame.sprite.Sprite):
    """
    文本组件，只能放下单行文本
    该组件仅会在self.text改变时重新渲染自身
    在需要改变时：更新self.text为需要改变的字符串即可
    self.color, self.background, self.font, self.font_size也是可以改的，但需要在text更改引发的重新渲染后才生效
    """

    def __init__(self, text: str, center, font: str = 'arial',
                 font_size: int = 20, color=(255, 0, 0),
                 background=None, group=None):
        self.font = pygame.font.SysFont(name=font, size=font_size)
        self._text = ''
        self.image = self.font.render(text, True, color, background)

        self.color = color
        self.background = background
        self.text = text
        if group is None:
            group = []
        super().__init__(*group)
        self.rect = self.image.get_rect()
        self.rect.center = center

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        self._text = text
        self.image = self.font.render(text, True, self.color, self.background)


class Button(Text):
    """
    按钮组件，在鼠标左键按下时触发命令，本身是个文本
    """

    def __init__(self, command, text: str, center, font: str = 'arial',
                 font_size: int = 20, color: tuple[int] = (255, 0, 0),
                 background: tuple[int] = None, group=None, *args, **kwargs):
        """

        :param command: 回调函数，在按钮被按下时会用kwargs调用该函数
        :param text: 按钮文本
        :param center: 按钮中心坐标
        :param font: 字体
        :param font_size: 字体大小
        :param color: 字体颜色
        :param background: 按钮背景颜色
        :param group:  pygame.sprite.Group，要添加到的精灵组
        :param args: 位置参数，放你想要传给command的参数
        :param kwargs: 字典，放你想要传给command的参数
        """
        super().__init__(text, center, font, font_size, color, background, group)
        self.command = command
        self.args = args
        self.kwargs = kwargs

    def push(self):
        self.command(*self.args, self.kwargs)

    def update(self, dt=None):
        if pygame.mouse.get_pressed(3)[0]:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.push()


class ImageButton(pygame.sprite.Sprite):
    """
    图片按钮组件，在鼠标左键按下时触发命令
    """
    def __init__(self, center, image: pygame.Surface, command, group=None, *args, **kwargs):
        super().__init__(*group)
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.command = command
        self.args = args
        self.kwargs = kwargs

    def push(self):
        self.command(*self.args, self.kwargs)

    def update(self, dt=None):
        if pygame.mouse.get_pressed(3)[0]:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.push()