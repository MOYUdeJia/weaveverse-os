# 桌宠系统规划（M11+，M10 只规划不实现）

目标：在 Weaveverse 窗口里放一只可拖动的桌宠，和现有音乐悬浮球共用节拍，不另开系统级透明窗。

## 需求

- 按住拖动；松手吸附到窗口边缘（左/右/底，避开分组栏与悬浮球占位）
- 播放时按节拍轻微跳动；点击桌宠播放/暂停（转调现有 MusicDock 的播放状态，不复制一套播放器）
- 形象：GIF、PNG 序列帧；Live2D 作为后期可选层
- 状态：待机、播放、暂停

## 技术选型

**事实**

- 悬浮球已经在 `MusicDock.vue` 里用 Web Audio `AnalyserNode` 取波形（`getByteTimeDomainData`）
- 应用壳是 pywebview，窗口不透明；桌宠只能画在应用 DOM 里，不是桌面精灵
- 项目约束：不引入 UI 组件库、不引入 TypeScript

**选择：HTML + CSS transform + pointer events；节拍复用 AnalyserNode**

| 方案 | 优点 | 缺点 |
| ---- | ---- | ---- |
| A. 应用内 DOM 桌宠（推荐） | 和现有 Vue 栈一致；能读同一 AnalyserNode；实现量可控 | 不能拖出应用窗口 |
| B. 独立透明 pywebview 窗 | 能放在桌面上 | 要改窗口线程模型，任务书明确禁止乱改 pywebview 线程 |
| C. Live2D Cubism SDK 先行 | 形象更丰富 | SDK 授权、包体、和 Vue 的胶水都重，不适合第一版 |

不用 PixiJS / 完整游戏引擎：第一版只有拖动和三态动画，引擎体积和心智成本不对等。序列帧用 CSS `steps()` 或 `requestAnimationFrame` 换图即可。

Live2D 放到 M11 之后的加料：等 GIF/序列帧跑通，再评估 Cubism Web SDK。

## 建议数据结构（实现时）

存在 `appearance.json` 或 `pet.json`，例如：

```json
{
  "enabled": false,
  "skin": "default",
  "x": 0.92,
  "y": 0.72,
  "edge": "right",
  "beat": true
}
```

形象文件放 `%APPDATA%/WeaveverseOS/pets/`（开发态则 `backend/data/pets/`）。不要把密钥写进皮肤文件。

## 和悬浮球的接口

- 抽出一个很小的播放总线（播放/暂停/当前 AnalyserNode），桌宠和球都订阅
- 跳动用 RMS 或低频能量映射到 `translateY`，低性能模式关掉
- 点击桌宠 = 调用同一 toggle，避免两套 audio 元素抢设备

## 排期

- M11：DOM 桌宠 + GIF/序列帧 + 吸附 + 节拍
- 更后：Live2D、多形象商店、出窗口（若那时换壳）
