# Weaveverse 主题包（`.wvpack`）

`.wvpack` 是一个 zip。扩展名只是为了和只换颜色的 `.wvtheme` 分开。`.wvtheme` / `.json` 仍然只换颜色。

安装后解压到用户数据目录的 `themes/<id>/`（开发时是 `backend/data/themes/<id>/`）。

## 目录

```
mytheme.wvpack
├── manifest.json
├── colors.json
├── preview.png          可选，主题列表里的图
├── splash/              可选，开屏
├── background/          可选，壁纸
├── decorations/         可选，角标
└── sounds/              可选，启动音
```

只接受图片、视频、Lottie、svg、mp3/wav/ogg 和 json。压缩包上限 80MB。

## manifest.json

| 字段 | 必填 | 说明 |
| ---- | ---- | ---- |
| `id` | 是 | 小写字母、数字、短横线，不能和五套预设重名 |
| `name` | 是 | 列表里的名字 |
| `author` | 否 | |
| `version` | 否 | |
| `description` | 否 | |
| `caption` | 否 | 开屏底部那一行 |
| `preview` | 否 | 相对路径 |
| `colors` | 是 | 默认 `colors.json` |
| `splash` | 否 | `type` 为 image / video / lottie，`path`，`duration`（2/3/5/10/14），`loop` |
| `background` | 否 | `type` 为 image / video，`path`，`opacity`（0 到 1） |
| `decorations` | 否 | 最多 6 个相对路径，画在窗口角上 |
| `sounds.startup` | 否 | 开屏时播放一次 |

`colors.json` 用和 `.wvtheme` 一样的 `vars`（`dawn` / `group` / `nav` / `work`，可选 `orb` / `progress`）。

## 示例

```json
{
  "id": "mist-blue",
  "name": "雾蓝",
  "author": "example",
  "version": "1.0",
  "description": "只作为格式示例",
  "preview": "preview.png",
  "colors": "colors.json",
  "caption": "正在编织你的宇宙",
  "splash": { "type": "video", "path": "splash/video.mp4", "duration": 3, "loop": false },
  "background": { "type": "image", "path": "background/image.jpg", "opacity": 0.85 },
  "decorations": ["decorations/logo.svg"],
  "sounds": { "startup": "sounds/startup.mp3" }
}
```

切换主题包时：颜色写入自定义主题，开屏、壁纸、角标和启动音指向包内文件，不另复制一份大视频。删掉主题包，或改选别的颜色主题，这些都会收回，颜色回到暖白（如果当前用的就是这个包）。
