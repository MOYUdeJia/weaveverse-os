# Weaveverse OS · M1 任务书

> 本文件是给 Agent 执行的唯一依据。执行前先读完再动手。
> 承接 M0。M0 交付：桌面窗口 + 开屏动画 + 左右布局 + 静态导航（`/api/nav` 硬编码）。
> 读 `docs/VERSIONS.md` 了解 M0 架构，读 `docs/M0-TASK.md` 了解上一版任务范围。

---

## 0. 执行指令

1. 执行前先检查本任务书有无错误前提、逻辑跳跃或信息缺失，有则先列出再问。
2. 不要一味迎合。区分事实、预测和主观观点。
3. 涉及数字、人物、结论时，尽可能核实来源。
4. 发现任务书说得不对，直接指出，说明依据、风险和更合适的解释。
5. 主动提醒可能被忽略的变量、成本、偏差。
6. 代码要有可读性。每个模块开头说明用途，代码块简短概括作用。
7. 生成 `.gitignore` 时若有更新需求，在对话末尾说明，不要静默修改。
8. 任务完成后**更新** `docs/VERSIONS.md`（追加 M1 段落，不覆盖 M0）。
9. **不确定时先列计划或提问，不要直接改代码。**

---

## 1. 目标

**要做什么**：把 M0 的硬编码导航替换为 SQLite 数据库存储，加上 Alembic 迁移，前端支持导航项的增 / 删 / 改。

**为什么**：M1 是数据结构的地基。所有后续功能（页面、区块、内容）都挂在这个数据库上。M1 结构错了，后面全返工。

**M1 不追求**：页面内容编辑、Markdown、待办、图片、排序拖拽、多主题、AI。

---

## 2. 范围

### 必须做

- 接入 SQLite + SQLModel
- 接入 Alembic，生成初始迁移
- `NavItem` 模型：id / title / icon / sort_order / created_at / updated_at
- `/api/nav` 从数据库读（M0 是硬编码）
- 新增接口：创建 / 更新 / 删除导航项
- 首次启动：数据库为空时自动种入 M0 的 6 条数据
- 启动时自动执行 Alembic 迁移（不丢数据）
- 前端：侧边栏底部加"+"按钮；每项悬停显示编辑 / 删除
- 编辑弹窗：改 title、改 icon（emoji 文本输入，不引入 picker 库）
- 删除带确认提示
- 更新 `docs/VERSIONS.md`

### 不要做

- 不做页面内容（工作区仍是占位）
- 不做拖拽排序（放到 M2）
- 不做导航项分组 / 嵌套
- 不做导入导出
- 不联网、不做密码、插件、AI
- 不引入 UI 组件库（Element Plus、Ant Design 等）
- 不引入 TypeScript
- 不改 M0 的 pywebview / uvicorn 线程模型
- 不改 M0 的开屏动画

---

## 3. 技术栈（在 M0 基础上新增）

| 层面     | 选择               | 版本要求           |
| -------- | ------------------ | ------------------ |
| ORM      | SQLModel           | 最新稳定版         |
| 数据库   | SQLite             | 单文件，路径见 6.3 |
| 迁移     | Alembic            | 最新稳定版         |
| Pydantic | 跟随 SQLModel 版本 | 不单独锁定         |

其余保持 M0 不变。

---

## 4. 项目结构变化

```
backend/
├── main.py                  # 改：启动时先跑迁移
├── alembic.ini              # 新增
├── alembic/                 # 新增
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── xxxx_initial.py
├── requirements.txt         # 改：加 sqlmodel、alembic
└── app/
    ├── __init__.py
    ├── api.py               # 改：只做路由聚合
    ├── config.py            # 改：加数据库路径
    ├── static.py            # 不变
    ├── db.py                # 新增：engine + session
    ├── models.py            # 新增：NavItem
    ├── schemas.py           # 新增：输入输出 Pydantic
    ├── crud.py              # 新增：数据库操作
    ├── seed.py              # 新增：初始数据
    └── routes/
        └── nav.py           # 新增：/api/nav 路由

backend/data/                # 新增
├── README.md                # 数据库文件位置、备份说明
└── .gitkeep

frontend/src/
├── api/client.js            # 改：加 createNav / updateNav / deleteNav
└── components/
    ├── SidebarNav.vue       # 改：加增删改 UI
    └── NavEditDialog.vue    # 新增：编辑弹窗
```

---

## 5. 数据模型

### 表 `nav_items`

| 字段       | 类型     | 约束                               |
| ---------- | -------- | ---------------------------------- |
| id         | int      | 主键，自增                         |
| title      | str      | 非空，长度 1-50                    |
| icon       | str      | 非空，长度 1-8（emoji 可能多字节） |
| sort_order | int      | 非空，默认 0，越小越靠前           |
| created_at | datetime | 非空，默认当前时间                 |
| updated_at | datetime | 非空，默认当前时间，更新时自动刷新 |

**说明**：M0 用字符串 id（如 "fitness"）作为前端 key。M1 改用自增 int id。前端需从字符串 key 切换到 int id。

---

## 6. 接口契约

所有接口保持 `/api/` 前缀，不加版本号。

### `GET /api/nav`

**返回**：按 `sort_order` 升序的数组。

```json
[
  {"id": 1, "title": "健身", "icon": "💪", "sort_order": 0},
  {"id": 2, "title": "学习", "icon": "📚", "sort_order": 1}
]
```

### `POST /api/nav`

**请求体**：
```json
{"title": "阅读", "icon": "📖"}
```

**返回**：创建后的完整对象（含 id、sort_order、created_at、updated_at）。

**行为**：`sort_order` 自动取当前最大值 +1。

### `PUT /api/nav/{id}`

**请求体**：
```json
{"title": "阅读", "icon": "📖"}
```

**返回**：更新后的完整对象。

**行为**：`updated_at` 自动刷新。id 不存在返回 404。

### `DELETE /api/nav/{id}`

**返回**：`{"status": "ok"}`。

**行为**：id 不存在返回 404。

### 错误响应格式

所有接口错误统一返回：

```json
{"detail": "错误说明"}
```

HTTP 状态码语义化：400 参数错误、404 不存在、500 服务端错误。

### 前端 `api/client.js` 新增

- `createNav({title, icon})` → POST
- `updateNav(id, {title, icon})` → PUT
- `deleteNav(id)` → DELETE

---

## 7. 行为细节

### 7.1 Alembic 初始化

- `alembic init alembic` 生成骨架。
- `env.py` 从 `app.models` 读取 `SQLModel.metadata`（不要手写表结构）。
- 生成第一版迁移：`alembic revision --autogenerate -m "initial nav_items"`。
- 迁移文件进 git。

### 7.2 启动时自动迁移

`main.py` 启动流程（在 M0 基础上追加）：

1. 检查数据库文件是否存在
2. 不存在 → 执行 `alembic upgrade head` 建表 → 触发 seed
3. 存在 → 直接执行 `alembic upgrade head`（幂等）→ 跳过 seed
4. 启动 uvicorn 子线程
5. 打开 pywebview

**实现方式**：推荐用 Alembic 的 Python API（`alembic.config.Config` + `command.upgrade`），不要 subprocess。避免依赖 shell 环境。

**如果遇到困难**：先用 `SQLModel.metadata.create_all()` 建表，Alembic 配置文件保留，在 `VERSIONS.md` 里记录"启动迁移暂用 create_all，Alembic 手动执行"。但优先用 Alembic API。

### 7.3 数据库文件位置

放 `backend/data/weaveverse.db`。

**为什么不用系统用户数据目录**：M1 阶段方便调试和备份。后续版本（M5 备份 / M6 私有云）再考虑迁移到 `%APPDATA%`。

`backend/data/README.md` 说明：
- 数据库文件位置
- 如何备份（直接复制 `.db` 文件）
- 如何恢复（覆盖后重启）
- 后续可能迁移到用户数据目录

`backend/data/` 下放 `.gitkeep`，`.db` 文件加进 `.gitignore`。

### 7.4 Seed 逻辑

数据库为空（`nav_items` 表 0 条）时，插入 M0 的 6 条数据，`sort_order` 按顺序 0-5：

```python
[
    {"title": "健身", "icon": "💪"},
    {"title": "学习", "icon": "📚"},
    {"title": "音乐", "icon": "🎵"},
    {"title": "游戏", "icon": "🎮"},
    {"title": "观后感", "icon": "🎬"},
    {"title": "未来规划", "icon": "🧭"},
]
```

**注意**：用户删光所有导航项后重启，不应再次 seed（否则删不干净）。判断方式：用"数据库文件是否存在"作为 seed 条件，而不是"表是否为空"。

### 7.5 前端交互

**侧边栏**：
- 每项悬停时，右侧浮现两个图标按钮：编辑（✏️）、删除（🗑️）
- 侧边栏底部固定一个"+ 添加"按钮
- 当前选中项保持高亮

**编辑弹窗**（`NavEditDialog.vue`）：
- 字段：title（文本输入）、icon（emoji 文本输入，单字符）
- 用于新增和编辑，共用一个组件
- 确定 / 取消按钮
- 空 title 禁用确定按钮

**删除**：
- 点击删除按钮弹出确认（可用 `confirm()` 简单处理，不引入库）
- 删除当前选中项后，自动选中列表第一项；列表空则右侧显示"暂无导航项，点击 + 添加"

**错误处理**：
- 请求失败 console 打日志 + UI 显示提示条（可简单用 `alert` 或自研轻提示）
- 不崩溃

### 7.6 兼容性

- M0 的 `/api/health` 保持不变。
- M0 的开屏动画、窗口尺寸、SPA fallback 全部保持。
- M0 的 `frontend/src/api/client.js` 里的 `getNav()` 保持同名，只改返回结构（id 从 string 变 int）。

---

## 8. 验收标准

### 8.1 环境

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd ../frontend
npm install
```

必须无报错。

### 8.2 首次启动（数据库不存在）

```bash
cd frontend && npm run build
cd ../backend && python main.py
```

期望：
- [ ] `backend/data/weaveverse.db` 被创建
- [ ] `nav_items` 表有 6 条数据
- [ ] 桌面窗口正常打开
- [ ] 左侧显示 6 项导航

### 8.3 增删改验收

- [ ] 点击"+"，输入"阅读"/"📖"，确定 → 列表底部新增一项
- [ ] 悬停"阅读"，点编辑，改 title 为"读书" → 列表更新
- [ ] 悬停"读书"，点删除，确认 → 列表移除该项
- [ ] 关闭窗口，重启 → 变化保留
- [ ] 数据库里有 `created_at`、`updated_at`

### 8.4 重启不丢数据

```bash
python main.py   # 添加一项
# 关闭窗口
python main.py   # 重启
```

期望：
- [ ] 上次添加的项还在
- [ ] 不会重复 seed（不会又冒出一套默认 6 项）

### 8.5 接口验收

```bash
curl http://127.0.0.1:8765/api/nav
# 返回数据库里的数组

curl -X POST http://127.0.0.1:8765/api/nav \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","icon":"🧪"}'
# 返回带 id 的新对象

curl -X PUT http://127.0.0.1:8765/api/nav/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"改名","icon":"📝"}'
# 返回更新后的对象

curl -X DELETE http://127.0.0.1:8765/api/nav/1
# {"status":"ok"}

curl http://127.0.0.1:8765/api/nav/99999
# 应返回 404（对不存在的 id 做 PUT 或 DELETE 时）
```

### 8.6 Alembic 验收

```bash
cd backend
alembic current          # 显示当前 revision
alembic history          # 显示迁移历史
```

期望：
- [ ] 显示初始迁移
- [ ] `nav_items` 表结构与模型一致

### 8.7 代码结构验收

- [ ] `app/models.py` 只有模型，无业务逻辑
- [ ] `app/crud.py` 只做数据库操作
- [ ] `app/routes/nav.py` 只做 HTTP 层（收请求、调 crud、返回）
- [ ] `app/seed.py` 只在数据库文件不存在时触发
- [ ] `backend/data/weaveverse.db` 加入 `.gitignore`
- [ ] `backend/data/.gitkeep` 存在

---

## 9. 输出要求

### 9.1 对话末尾输出

1. 文件树（变化部分）
2. 安装 / 运行命令（生产模式）
3. 已实现功能清单
4. 验收步骤
5. 执行指令第 1-5 条的发现
6. M0 → M1 的所有破坏性变更（接口签名、前端数据结构改动）

### 9.2 更新 `docs/VERSIONS.md`

在 M0 段落后追加：

```markdown
## M1 · <YYYY-MM-DD>
- **任务**：SQLite + 导航 CRUD + Alembic + 重启不丢数据
- **实现**：
  - 后端：SQLModel + SQLite + Alembic（启动自动迁移）
  - 新增 `/api/nav` POST/PUT/DELETE
  - 前端：侧边栏增删改 UI + 编辑弹窗
  - 首次启动自动 seed 6 条数据
- **技术架构**：<实际架构说明，含数据库路径、迁移触发方式>
- **与 M0 相比的变化**：
  - `/api/nav` 数据源：硬编码 → 数据库
  - 导航项 id 类型：string → int
  - 新增接口：POST / PUT / DELETE
- **已知问题**：<列表>
- **文件变更**：<新增/修改/删除清单>
```

---

## 10. 不确定时的处理

- 遇到本任务书未覆盖的决策点，**先列 2-3 个方案 + 优缺点 + 推荐，停下问**。
- 不要自己拍脑袋选一个往下做。
- 如果发现本任务书有矛盾或遗漏，先指出再问怎么处理。

---

**M1 完成后，等人类反馈再进 M2。不要提前做 M2 的任何事。**