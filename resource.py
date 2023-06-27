import pygame


if not pygame.get_init():
    pygame.init()


IMAGE_SUFFIX = ["bmp"] if not pygame.image.get_extended()\
    else ["bmp", "png", "jpg", "jpeg", "gif", "lbm", "pcx", "pnm", "svg", "tga", "tiff",
          "webp", "xpm"]
AUDIO_SUFFIX = ['wav', 'mp3', 'ogg', 'midi']
FONT_SUFFIX = ['ttf']


def load_image(file, crucial: bool = 1, default=None) -> pygame.surface.Surface:
    """
    加载一张图片，在失败时返回默认值

    :param file: a file (or file-like) object. 该参数会被传递到 pygame.image.load
    :param crucial: 表示该文件是否必须。是：该文件打开失败会引发异常 否：该文件打开失败只会产生警告，不引发异常并返回default
    :param default: 在crucial为否且文件打开失败时返回
    :return: 图片创建后的surface对象
    """
    try:
        result = pygame.image.load(file)
    except (pygame.error, FileNotFoundError) as error:
        if crucial:
            raise
        else:
            print(f"缺失图片{file}: {str(error)}")
            return default
    return result


def load_sound(file, crucial: bool = 1, default=None) -> pygame.mixer.Sound:
    """
    加载一段声音，在失败时返回默认值

    :param file: a file (or file-like) object. 该参数会被传递到 pygame.mixer.Sound.__init__
    :param crucial: 表示该文件是否必须。是：该文件打开失败会引发异常 否：该文件打开失败只会产生警告，不引发异常并返回default
    :param default: 在crucial为否且文件打开失败时返回
    :return: pygame.mixer.Sound对象
    """
    try:
        result = pygame.mixer.Sound(file)
    except (pygame.error, FileNotFoundError) as error:
        if crucial:
            raise
        else:
            print(f"缺失音效{file}: {str(error)}")
            return default
    return result


def load_font(file, crucial: bool = 1, font_size=30, default=None) -> pygame.font.Font:
    """
    加载文件中的字体文件，失败时返回默认值
    :param font_size: 添加字体时字体大小
    :param file: 字体文件路径或文件对象
    :param crucial: 表示该文件是否必须。是：该文件打开失败会引发异常 否：该文件打开失败只会产生警告，不引发异常并返回default
    :param default: 在crucial为否且文件打开失败时返回
    :return: font.Font对象
    """
    try:
        result = pygame.font.Font(file, font_size)
    except (FileNotFoundError, pygame.error) as error:
        if crucial:
            raise
        else:
            print(f"缺失字体{file}: {str(error)}")
            return default
    return result


def load_bgm(file, crucial: bool = 1) -> None:
    """
    将一段音乐加载到pygame.mixer.music中

    :param file: a file (or file-like) object. 该参数会被传递到 pygame.mixer.music.load
    :param crucial: 表示该文件是否必须。是：该文件打开失败会引发异常 否：该文件打开失败只会产生警告，不引发异常
    :return: 无
    """
    try:
        pygame.mixer.music.load(file)
    except (pygame.error, FileNotFoundError) as error:
        if crucial:
            raise
        else:
            print(f"缺失背景音乐{file}: {str(error)}")


def load(file, crucial: bool = 1, default=None, font_size=30):
    """
    通过扩展名判断file的类型，并自动调用pygame相应加载函数加载文件。在失败时返回默认值
    对不支持的资源：返回default

    :param font_size: 添加字体时可选参数，指定字体大小
    :param file: 待加载的文件，必须为文件名
    :param crucial: 表示该文件是否必须。是：该文件打开失败会引发异常 否：该文件打开失败只会产生警告，不引发异常并返回default
    :param default: 在crucial为否且文件打开失败时返回
    :return: 加载后的资源，类型不确定
    """
    if not isinstance(file, str):
        raise ValueError(f"{file} 不是文件名")
    if file.split(".")[-1] in IMAGE_SUFFIX:
        return load_image(file, crucial, default)
    if file.split(".")[-1] in AUDIO_SUFFIX:
        return load_sound(file, crucial, default)
    if file.split('.')[-1] in FONT_SUFFIX:
        return load_font(file, crucial, font_size, default)
    return default
