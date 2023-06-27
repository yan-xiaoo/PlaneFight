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
        """
        创建一个带有文字的标签
        :param text: 初始的文字，可以为空字符串
        :param center: 该组件的中心坐标
        :param font: 组件的字体，可以是加载过的字体文件或系统字体名
        :param font_size: 组件的字体大小，仅在font为系统字体名时生效
        :param color: 组件的字体颜色，可以是元组或pygame预设的颜色名
        :param background: 组件的背景颜色，为None时表示透明
        :param group: 该组件要添加的组
        """
        # 为了方便，这里允许font参数为pygame.font.Font对象或字体名
        if not isinstance(font, pygame.font.Font):
            # 如果font不是pygame.font.Font对象，那么就认为它是字体名，手动构造字体对象
            self.font = pygame.font.SysFont(name=font, size=font_size)
        else:
            self.font = font
        self._text = ''
        # 先根据text渲染出一次图片
        self.image = self.font.render(text, True, color, background)

        self.color = color
        self.background = background
        self.text = text
        if group is None:
            group = []
        super().__init__(*group)
        self.rect = self.image.get_rect()
        self.rect.center = center

    # text为一个属性，更改text会立刻触发重新渲染
    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text: str):
        self._text = text
        # 重新渲染
        self.image = self.font.render(text, True, self.color, self.background)

    def render(self) -> None:
        """
        立刻以目前的设置进行一次渲染
        :return: 无
        """
        self.image = self.font.render(self.text, True, self.color, self.background)


class Button(Text):
    """
    按钮组件，在鼠标左键按下时触发命令，本身是个文本
    """

    def __init__(self, command, text: str, center, font: str = 'arial',
                 font_size: int = 20, color: tuple[int] = (255, 0, 0),
                 background: tuple[int] = None, group=None, *args, **kwargs):
        """
        创建一个按钮组件，该按钮相当于一个会响应点击的文本标签
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
        # 存储回调函数与参数，以便回调
        self.command = command
        self.args = args
        self.kwargs = kwargs

    def push(self):
        # 按钮被按下时，调用回调函数
        self.command(*self.args, self.kwargs)

    def update(self, dt=None):
        # 每帧都检查鼠标是否按下，如果鼠标左键被按下且鼠标指针在按钮上，就触发回调
        for event in pygame.event.get(pygame.MOUSEBUTTONUP):
            if event.button == pygame.BUTTON_LEFT and self.rect.collidepoint(event.pos):
                self.push()


class ImageButton(pygame.sprite.Sprite):
    """
    图片按钮组件，在鼠标左键按下时触发命令
    """
    def __init__(self, center, image: pygame.Surface, command, group=None, *args, **kwargs):
        """
        创建一个图片按钮组件，该按钮相当于一个会响应点击的图片
        :param center: 按钮中心坐标
        :param image: 按钮图片
        :param command: 回调函数，在按钮被按下时会用args, kwargs调用该函数
        :param group: pygame.sprite.Group，要添加到的精灵组
        :param args: 位置参数，放你想要传给command的参数
        :param kwargs: 字典，放你想要传给command的参数
        """
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
        for event in pygame.event.get(pygame.MOUSEBUTTONUP):
            if event.button == pygame.BUTTON_LEFT and self.rect.collidepoint(event.pos):
                self.push()
