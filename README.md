# 捂嘴小猫终端动画

一个把 `cat_pixel_animation.gif` 渲染到终端里的小项目。运行后会在同一个终端窗口中显示 4 只对齐排布的小猫，保留像素风格，并对小猫周围的白底和浅色底板做抠图处理。

## 效果特点

- 读取原始 GIF 帧并循环播放动画
- 自动抠除外围白色背景和小猫周围的浅色方块
- 使用 ANSI True Color 在普通终端中渲染像素风画面
- 当前默认布局为 `2 x 2`，也就是一个终端里同时播放 4 只同步小猫
- 会根据终端窗口大小自动缩放，尽量保持原始比例不变形

## 项目结构

```text
.
├── animation.py
├── cat_pixel_animation.gif
├── requirements.txt
└── 小猫.mp4
```

文件说明:

- `animation.py`: 主程序，负责抠图、裁剪、缩放和终端动画播放
- `cat_pixel_animation.gif`: 动画源文件
- `requirements.txt`: Python 依赖列表
- `小猫.mp4`: 原始素材文件

## 环境要求

- Python 3.10+
- 支持 ANSI 转义序列和 True Color 的终端

常见可用终端:

- macOS Terminal
- iTerm2
- Windows Terminal
- 支持 `24-bit color` 的 Linux/macOS 终端

## 安装依赖

```bash
python -m pip install -r requirements.txt
```

或者手动安装:

```bash
python -m pip install pillow opencv-python numpy
```

## 运行方式

在项目目录下执行:

```bash
python animation.py
```

如果你的环境默认命令是 `python3`，可以改用:

```bash
python3 animation.py
```

退出播放:

```text
Ctrl + C
```

## 实现思路

`animation.py` 的处理流程大致如下:

1. 读取 `cat_pixel_animation.gif` 的每一帧
2. 识别接近白色的区域并构建前景遮罩
3. 裁出小猫主体的联合边界框
4. 按终端大小等比缩放图像
5. 将 RGBA 像素转换为 ANSI 彩色半块字符
6. 把单只猫拼成 `2 x 2` 网格后循环播放

## 可调整项

如果你想自己改显示效果，可以看 `animation.py` 里的这些常量:

- `DEFAULT_RENDER_WIDTH`: 默认渲染宽度
- `MIN_RENDER_WIDTH`: 最小渲染宽度
- `CAT_GAP`: 小猫之间的水平间距
- `WHITE_DISTANCE_THRESHOLD`: 白底识别阈值
- `WHITE_SPREAD_THRESHOLD`: 白色通道扩散阈值

## 常见问题

### 动画颜色不对或者没有颜色

说明当前终端可能不支持 True Color，建议换到支持 `24-bit color` 的终端里运行。

### 画面太大或太小

可以调整终端窗口大小，或者直接修改 `animation.py` 里的 `DEFAULT_RENDER_WIDTH`。

### 动画看起来闪烁

终端逐帧刷新本身会有一定闪烁感，这属于文本终端动画的正常现象。

## License

仅供学习和演示使用。
