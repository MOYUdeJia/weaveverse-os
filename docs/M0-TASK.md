# Weaveverse OS · M0 任务书

> 本文件是给 Agent 执行的唯一依据。执行前先读完再动手。

---

## 0. 执行指令

1. 执行前先检查本任务书有无错误前提、逻辑跳跃或信息缺失，有则先列出再问。
2. 不要一味迎合。区分事实、预测和主观观点。
3. 涉及数字、人物、结论时，尽可能核实来源。
4. 发现任务书说得不对，直接指出，说明依据、风险和更合适的解释。
5. 主动提醒可能被忽略的变量、成本、偏差。
6. 代码要有可读性。每个模块开头说明用途，代码块简短概括作用。自定义上传文件的地方放 md 说明。
7. 我已经生成 `.gitignore` 并初始化 git，版本管理上传不需要你动手。
8. 任务完成后写入 `docs/VERSIONS.md`（格式见第 9 节）。
9. **不确定时先列计划或提问，不要直接改代码。**

---

## 1. 目标

**要做什么**：搭建 Weaveverse OS 的 M0 骨架——一个能启动、有开屏动画、左侧导航 + 右侧工作区的本地桌面应用。

**为什么**：M0 是地基。后续 M1 接 SQLite、M2 接页面系统、M3 接成长模板，全部依赖 M0 的前后端解耦结构和 pywebview 外壳。M0 结构错了，后面全要返工。

**M0 不追求**：功能完整、UI 精美、数据库、联网、AI。只追求**结构正确、可运行、可验收**。

---

## 2. 范围

### 必须做

- 桌面窗口能启动（pywebview）
- 开屏动画（约 2 秒，可替换图片）
- 左侧导航列表（从 `/api/nav` 获取，不写死）
- 右侧工作区（点击导航切换标题）
- FastAPI 后端，`/api/health` 和 `/api/nav` 两个接口
- 开发模式和生产模式都能跑
- `.gitignore` + git 初始化
- `docs/VERSIONS.md` 记录本次变更

### 不要做

- 不接数据库（SQLite 留给 M1）
- 不做增删改
- 不做 Markdown / 待办 / 富文本
- 不联网
- 不做密码、插件、音乐、小游戏、AI、语音
- 不做多主题（暗色/浅色二选一或跟随系统即可）
- 不做用户登录

---

## 3. 技术栈

| 层面        | 选择         | 版本要求                            |
| ----------- | ------------ | ----------------------------------- |
| Python      | 3.11+        | 用 venv 隔离                        |
| 后端框架    | FastAPI      | 最新稳定版                          |
| ASGI 服务器 | uvicorn      | 最新稳定版                          |
| 桌面窗口    | pywebview    | 最新稳定版                          |
| 前端框架    | Vue 3        | Composition API + `<script setup>`  |
| 构建工具    | Vite         | 最新稳定版                          |
| CSS         | Tailwind CSS | **3.x**（不用 4.x，配置方式不兼容） |
| 前端语言    | JavaScript   | **不用 TypeScript**，M0 保持简单    |
| 包管理器    | npm          | Node 18+                            |

**依赖锁定**：
- Python：`backend/requirements.txt` 锁定版本
- Node：`frontend/package-lock.json` 提交到 git

---

## 4. 项目结构

```
weaveverse-os/
├── README.md
├── .gitignore
├── docs/
│   ├── VERSIONS.md
│   └── ARCHITECTURE.md          # 简要架构说明（可选，M0 可只留框架）
├── backend/
│   ├── main.py                  # 入口：启动 uvicorn 子线程 + pywebview 主线程
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── api.py               # /api/* 路由
│       ├── config.py            # 端口、路径、环境变量
│       └── static.py            # 挂载 frontend/dist + SPA 回退
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── style.css
        ├── api/client.js        # 封装 fetch，统一前缀 /api
        ├── components/
        │   ├── SplashScreen.vue
        │   ├── SidebarNav.vue
        │   └── WorkspacePanel.vue
        └── assets/splash/
            ├── splash.png       # 默认开屏图（可用占位图）
            └── README.md        # 替换说明
```

---

## 5. 相关文件 / 模块

Agent 只需关注本任务书涉及的文件。不要全库扫描。

- 后端：`backend/main.py`、`backend/app/*.py`
- 前端：`frontend/src/**`
- 配置：`frontend/vite.config.js`、`frontend/tailwind.config.js`、`frontend/postcss.config.js`
- 文档：`README.md`、`docs/VERSIONS.md`、`frontend/src/assets/splash/README.md`

---

## 6. 接口契约

### `GET /api/health`

**用途**：健康检查，前端启动时可用它确认后端就绪。

**返回**：
```json
{"status": "ok"}
```

### `GET /api/nav`

**用途**：返回左侧导航项。

**返回**：
```json
[
  {"id": "fitness", "title": "健身", "icon": "💪"},
  {"id": "study",   "title": "学习", "icon": "📚"},
  {"id": "music",   "title": "音乐", "icon": "🎵"},
  {"id": "game",    "title": "游戏", "icon": "🎮"},
  {"id": "review",  "title": "观后感", "icon": "🎬"},
  {"id": "future",  "title": "未来规划", "icon": "🧭"}
]
```

**说明**：M0 返回静态数组，写在 `backend/app/api.py` 里。M1 会改为从数据库读，所以**不要把数据写进前端**。

### 前端调用

`frontend/src/api/client.js` 封装：
- `getHealth()` → `GET /api/health`
- `getNav()` → `GET /api/nav`

所有请求前缀 `/api`。开发模式下由 Vite 代理到后端端口。

---

## 7. 行为细节

### 7.1 后端启动流程

1. 用 socket 绑定 `127.0.0.1:0` 获取系统分配的空闲端口（优先尝试 8765，被占用则用系统分配）。
2. 把实际端口写入全局变量。
3. uvicorn 在**子线程**启动（pywebview 要求主线程）。
4. 主线程启动 pywebview 窗口，加载 `http://127.0.0.1:<port>`。
5. 关闭窗口时设置 `uvicorn.Server.should_exit = True`，等子线程退出后进程结束。

**线程约束**：pywebview 必须在主线程（GUI 框架要求）。uvicorn 必须在子线程。搞反了窗口打不开。

### 7.2 开发模式 vs 生产模式

通过环境变量 `WEAVEVERSE_DEV=1` 切换。

| 模式 | 前端                                 | 后端                            | pywebview 加载            |
| ---- | ------------------------------------ | ------------------------------- | ------------------------- |
| 生产 | `npm run build` 生成 `frontend/dist` | 挂载 `frontend/dist` + SPA 回退 | `http://127.0.0.1:<port>` |
| 开发 | `npm run dev`（Vite，默认 5173）     | 只提供 `/api/*`                 | Vite dev server 地址      |

**Vite 配置**：`vite.config.js` 里配置 `/api` 代理到后端端口，端口从环境变量读。

### 7.3 SPA 回退

FastAPI 挂载静态目录后，非 `/api/*` 且非静态资源的路径回退到 `index.html`。

### 7.4 开屏动画

- `SplashScreen.vue` 只负责播放逻辑（显示、淡出、通知父组件动画结束）。
- 动画内容来自 `frontend/src/assets/splash/splash.png`。
- M0 默认实现：图片 + CSS 淡入淡出，持续约 2 秒。
- 替换方式：换 `splash.png` 即可，不用改代码。
- `splash/README.md` 说明：怎么换图、怎么改时长（在哪个文件改哪个变量）。

### 7.5 主界面

- 布局：左侧固定宽度侧边栏 + 右侧自适应工作区。
- 左侧从 `/api/nav` 加载，显示 `icon + title`。
- 点击导航项：右侧标题变为 `这里是 XX 的工作区`。
- 默认选中第一项。
- 后端未就绪时，左侧显示加载状态或错误提示，不白屏。

### 7.6 错误处理

- 后端：API 返回统一结构（M0 可简单返回对象，错误返回 `{"detail": "..."}`）。
- 前端：请求失败时在控制台打日志，UI 显示友好提示，不崩溃。

### 7.7 窗口

- 最小尺寸 1000×700。
- 启动时居中。
- 关闭窗口后进程正常退出，无残留。

---

## 8. 验收标准

### 8.1 环境验收

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

两条命令都必须无报错。

### 8.2 生产模式验收

```bash
cd frontend && npm run build       # 生成 dist/
cd ../backend && python main.py    # 启动
```

期望：
- [ ] 桌面窗口打开
- [ ] 先看到开屏动画（约 2 秒）
- [ ] 动画结束后进入主界面
- [ ] 左侧显示 6 个导航项
- [ ] 点击不同项，右侧标题变化
- [ ] 关闭窗口后进程退出（`ps` 或任务管理器无残留）

### 8.3 开发模式验收

```bash
# 终端 1
cd backend && WEAVEVERSE_DEV=1 python main.py

# 终端 2
cd frontend && npm run dev
```

期望：
- [ ] pywebview 窗口加载 Vite dev server
- [ ] 改 `App.vue` 内容，窗口自动热更新
- [ ] `/api/nav` 能正常返回

### 8.4 接口验收

```bash
curl http://127.0.0.1:<port>/api/health
# {"status":"ok"}

curl http://127.0.0.1:<port>/api/nav
# 返回 6 项数组
```

### 8.5 代码结构验收

- [ ] `frontend/src/api/client.js` 存在，封装了 API 调用
- [ ] 导航数据来自 `/api/nav`，不写死在 HTML
- [ ] 开屏动画文件独立于组件逻辑，可替换
- [ ] `.gitignore` 排除 `.venv/`、`node_modules/`、`dist/`、`__pycache__/`
- [ ] `docs/VERSIONS.md` 存在

---

## 9. 输出要求

### 9.1 对话末尾输出

1. 文件树（完整）
2. 安装和运行命令（生产模式 + 开发模式）
3. 已实现功能清单
4. 验收步骤
5. 执行指令第 1-5 条的发现（问题、提醒、偏差）

### 9.2 写入 `docs/VERSIONS.md`

```markdown
# Weaveverse OS · 版本记录

## M0 · <YYYY-MM-DD>
- **任务**：可运行骨架 + 开屏动画 + 左右布局 + 静态导航
- **实现**：
  - 后端：FastAPI + uvicorn（子线程） + pywebview（主线程），端口自动检测
  - 前端：Vue 3 + Vite + Tailwind 3，开屏动画可替换
  - 通信：`/api/health`、`/api/nav`
  - 开发/生产双模式
- **技术架构**：<实际架构说明，含端口、线程模型>
- **与上一版本相比的变化**：M0 为首版
- **已知问题**：<列表>
- **文件变更**：<新增/修改的文件列表>
```

### 9.3 README.md 至少包含

- 项目一句话简介
- 环境要求（Python 3.11+，Node 18+）
- 安装步骤（后端 venv + pip，前端 npm install）
- 开发模式启动命令
- 生产模式构建和启动命令
- 目录结构说明

---

## 10. 不确定时的处理

- 遇到本任务书未覆盖的决策点，**先列 2-3 个方案 + 优缺点 + 你的推荐，然后停下问**。
- 不要自己拍脑袋选一个然后往下做。
- 如果发现本任务书有矛盾或遗漏，先指出，再问怎么处理。

---

**M0 完成后，等人类反馈再进 M1。不要提前做 M1 的任何事。**