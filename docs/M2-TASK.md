# Weaveverse OS · M2 任务书

> 承接 M0、M1。M1 交付：SQLite + 导航 CRUD + Alembic + 启动迁移。
> 读 `docs/VERSIONS.md`（M0、M1 段）、`docs/FEATURES.md`（页面系统章节）、
> `docs/M1-TASK.md`（了解任务书格式）。
>
> M2 是 Weaveverse OS 从"空壳"变成"可用"的转折点：
> 导航项不再只是标题，每个页面有类型、有内容、有区块。
> 结构错了，M3 以后的成长模板全要返工。

---

## 0. 执行指令

1. 执行前先检查本任务书有无错误前提、逻辑跳跃或信息缺失，有则先列出再问。
2. 不要一味迎合。区分事实、预测和主观观点。
3. 涉及数字、人物、结论时，尽可能核实来源。
4. 发现任务书说得不对，直接指出，说明依据、风险和更合适的解释。
5. 主动提醒可能被忽略的变量、成本、偏差。
6. 代码要有可读性。每个模块开头说明用途，代码块简短概括作用。
7. 任务完成后**追加** `docs/VERSIONS.md`（不覆盖 M0、M1）。
8. **不确定时先列计划或提问，不要直接改代码。**

---

## 1. 目标

**要做什么**：把导航项从"只有标题"升级为"有类型的页面"，页面内由多个区块组成，支持 Markdown、待办、链接、图片四种区块。同时修 M1 遗留的拖拽排序和若干小问题。

**为什么**：M2 定义 Weaveverse OS 的核心数据模型——**页面 = 导航项 + 类型 + 若干区块**。M3 的健身、学习、音乐模块全部是"预设好的区块组合"。M2 的模型设计错了，M3 直接崩。

**M2 不追求**：富文本编辑器、Markdown 实时预览的高级功能、拖拽区块、AI、搜索、云同步、加密。

---

## 2. 范围

### 必须做

**数据模型**
- `NavItem` 新增 `page_type` 字段（字符串，默认 `"markdown"`）
- 新增 `Block` 模型：`id / nav_item_id / block_type / content / sort_order / created_at / updated_at`
- Alembic 迁移：保留现有数据，新增字段/表
- 删除 `NavItem` 时级联删除其 Block

**页面类型注册表**
- 后端定义"页面类型"注册表，注册项含：`type`、`label`（中文名）、`multi_instance`（bool）、`default_blocks`（创建时默认插入的区块列表）
- M2 注册的类型：
  | type       | label | multi_instance | default_blocks     |
  | ---------- | ----- | -------------- | ------------------ |
  | markdown   | 文档  | ✅              | 1 个 markdown 区块 |
  | todo       | 待办  | ✅              | 1 个 todo 区块     |
  | gallery    | 画廊  | ✅              | 1 个 gallery 区块  |
  | collection | 收藏  | ✅              | 1 个 link 区块     |
- 预留单实例类型（只注册，M2 不实现添加入口）：`bookshelf`、`idea_box`、`vault`、`future_plan`、`habit_tracker`
- 提供 `GET /api/page-types` 返回所有已注册类型

**区块系统（Block）**
- 支持 4 种区块类型：
  | block_type | content 结构                                          | 渲染                   |
  | ---------- | ----------------------------------------------------- | ---------------------- |
  | markdown   | `{"text": "..."}`                                     | 渲染 Markdown          |
  | todo       | `{"items": [{"text": "...", "done": false}]}`         | 待办清单，可勾选       |
  | link       | `{"links": [{"title": "...", "url": "..."}]}`         | 链接列表，点击打开外链 |
  | gallery    | `{"images": [{"filename": "...", "caption": "..."}]}` | 图片网格               |
- `content` 字段：SQLite 中用 `TEXT` 存 JSON 字符串，Python 侧用 Pydantic 校验
- Block CRUD API + 排序（`sort_order`）

**前端页面渲染**
- `WorkspacePanel.vue` 改为"根据 page_type 渲染页面 + 遍历 blocks 渲染区块"
- 前端区块组件注册表（和页面类型注册表同理）
- 4 个区块组件：`MarkdownBlock.vue` / `TodoBlock.vue` / `LinkBlock.vue` / `GalleryBlock.vue`
- 区块组件支持：编辑内容、保存、删除
- 页面底部有"+ 添加区块"按钮，弹出区块类型选择

**图片上传**
- 后端 `POST /api/blocks/{id}/images`：接收图片文件，存到 `backend/data/attachments/`，返回文件名
- 前端 gallery 区块支持上传、显示、删除图片

**导航拖拽排序**
- 前端支持拖拽导航项重新排序
- 后端 `PUT /api/nav/reorder`：接收 id 数组，批量更新 `sort_order`

**顺手修的小问题**
- `datetime.utcnow()` → `datetime.now(timezone.utc)`（Python 3.12+ 已弃用）
- emoji `max_length=8` → 20（兼容复合 emoji）
- 参数校验错误 → 返回具体的字段名和原因，不是笼统的"请求参数错误"
- SPA fallback 排除 `/api/*`：`GET /api/nav/{不存在的id}` 应返回 API 404，不应回退到 index.html

### 不要做

- 不做富文本编辑器（Markdown 编辑用 `<textarea>` 即可）
- 不做区块拖拽排序（M2 只做导航项拖拽）
- 不做实时协作 / 实时预览
- 不做图片裁剪 / 压缩
- 不做全文搜索
- 不引入 UI 组件库（Element Plus / Ant Design / Vuetify 等）
- 不引入 TypeScript
- 不改 M0 的 pywebview / uvicorn 线程模型
- 不改 M0 的开屏动画
- 不做单实例类型的具体实现（只注册元数据）

---

## 3. 技术栈（在 M1 基础上新增）

| 层面                  | 选择                            | 备注                   |
| --------------------- | ------------------------------- | ---------------------- |
| Markdown 渲染（前端） | `marked` 或 `markdown-it`       | 二选一，不要都装       |
| Markdown 安全         | `DOMPurify`                     | 必须，防止 XSS         |
| 拖拽排序              | `vuedraggable` 或原生 HTML5 DnD | 优先原生，避免依赖膨胀 |
| 图片上传              | FastAPI `UploadFile`            | 不需要额外库           |

其余不变。

---

## 4. 数据模型

### 表 `nav_items`（修改）

| 字段          | 类型     | 约束                    | 变化                      |
| ------------- | -------- | ----------------------- | ------------------------- |
| id            | int      | 主键，自增              | 不变                      |
| title         | str      | 非空，1-50              | 不变                      |
| icon          | str      | 非空，1-20              | **改：max_length 8 → 20** |
| sort_order    | int      | 非空，默认 0            | 不变                      |
| **page_type** | str      | 非空，默认 `"markdown"` | **新增**                  |
| created_at    | datetime | 非空，UTC               | **改：utcnow → now(utc)** |
| updated_at    | datetime | 非空，UTC，更新时刷新   | **改：同上**              |

### 表 `blocks`（新增）

| 字段        | 类型     | 约束                                                     |
| ----------- | -------- | -------------------------------------------------------- |
| id          | int      | 主键，自增                                               |
| nav_item_id | int      | 外键 → nav_items.id，级联删除                            |
| block_type  | str      | 非空，取值范围：`markdown` / `todo` / `link` / `gallery` |
| content     | TEXT     | 非空，JSON 字符串，默认 `"{}"`                           |
| sort_order  | int      | 非空，默认 0                                             |
| created_at  | datetime | 非空，UTC                                                |
| updated_at  | datetime | 非空，UTC                                                |

**索引**：`blocks.nav_item_id`

### 迁移策略

- Alembic 自动生成迁移，但**必须手动检查**：
  - `page_type` 加默认值 `"markdown"`，现有行自动填
  - `blocks` 表新建
  - `blocks.nav_item_id` 外键带 `ondelete="CASCADE"`
- 迁移后现有 6 条导航数据必须完整保留
- **不要**因为迁表而 drop 数据库

---

## 5. 接口契约

### 新增 / 修改的接口

#### `GET /api/page-types`

**返回**：
```json
[
  {"type": "markdown", "label": "文档", "multi_instance": true},
  {"type": "todo", "label": "待办", "multi_instance": true},
  {"type": "gallery", "label": "画廊", "multi_instance": true},
  {"type": "collection", "label": "收藏", "multi_instance": true},
  {"type": "bookshelf", "label": "书架", "multi_instance": false},
  ...
]
```

#### `POST /api/nav`（修改）

**请求体**：
```json
{"title": "阅读", "icon": "📖", "page_type": "collection"}
```

**行为**：
- `page_type` 缺省为 `"markdown"`
- 校验 `page_type` 是否在注册表中
- 创建后**自动插入该类型的 default_blocks**
- 返回创建后的对象 + blocks 列表

#### `GET /api/nav/{id}`（新增）

**返回**：单个导航项 + 其所有 blocks（按 sort_order 升序）。

**注意**：此接口存在后，SPA fallback 不能再吞掉它的 404。

#### `POST /api/nav/reorder`（新增）

**请求体**：
```json
{"ids": [3, 1, 2]}
```

**行为**：按数组顺序批量更新 `sort_order`（0, 1, 2...）。返回更新后的列表。

#### `GET /api/nav/{id}/blocks`（新增）

**返回**：该导航项的所有 blocks。

#### `POST /api/nav/{id}/blocks`（新增）

**请求体**：
```json
{"block_type": "todo", "content": {"items": []}}
```

**行为**：创建区块，`sort_order` 取当前最大值 +1。

#### `PUT /api/blocks/{id}`（新增）

**请求体**：
```json
{"content": {"items": [{"text": "晨跑", "done": false}]}}
```

**行为**：更新 content。`updated_at` 刷新。

#### `DELETE /api/blocks/{id}`（新增）

**返回**：`{"status": "ok"}`。

#### `POST /api/blocks/{id}/images`（新增）

**请求**：`multipart/form-data`，字段 `file`。

**行为**：接收图片，存到 `backend/data/attachments/`，返回 `{"filename": "..."}`。不直接改 content，由前端决定是否加入 gallery。

#### `DELETE /api/attachments/{filename}`（新增）

**行为**：删除附件文件。文件名做路径安全检查，禁止 `../`。

### 错误响应格式（统一）

```json
{"detail": {"field": "title", "message": "长度必须在 1-50 之间"}}
```

**说明**：M2 起，校验错误要具体到字段和原因。

### 前端 `api/client.js` 新增

- `getPageTypes()`
- `getNavItem(id)` → 单个 nav + blocks
- `reorderNav(ids)`
- `createBlock(navId, payload)`
- `updateBlock(blockId, payload)`
- `deleteBlock(blockId)`
- `uploadImage(blockId, file)`
- `deleteAttachment(filename)`

---

## 6. 行为细节

### 6.1 页面类型注册表（后端）

位置：`backend/app/page_types.py`

结构：
```python
PAGE_TYPES = {
    "markdown": {
        "label": "文档",
        "multi_instance": True,
        "default_blocks": [
            {"block_type": "markdown", "content": {"text": ""}},
        ],
    },
    "todo": {
        "label": "待办",
        "multi_instance": True,
        "default_blocks": [
            {"block_type": "todo", "content": {"items": []}},
        ],
    },
    "gallery": {
        "label": "画廊",
        "multi_instance": True,
        "default_blocks": [
            {"block_type": "gallery", "content": {"images": []}},
        ],
    },
    "collection": {
        "label": "收藏",
        "multi_instance": True,
        "default_blocks": [
            {"block_type": "link", "content": {"links": []}},
        ],
    },
    # 单实例类型，只注册，M2 不提供创建入口
    "bookshelf": {"label": "书架", "multi_instance": False, "default_blocks": []},
    "idea_box": {"label": "IDEA 栏", "multi_instance": False, "default_blocks": []},
    "vault": {"label": "密码箱", "multi_instance": False, "default_blocks": []},
    "future_plan": {"label": "未来规划", "multi_instance": False, "default_blocks": []},
    "habit_tracker": {"label": "习惯追踪", "multi_instance": False, "default_blocks": []},
}
```

**关键**：加新页面类型只改这个文件，不改路由。

### 6.2 区块类型注册表（前端）

位置：`frontend/src/blocks/registry.js`

```js
import MarkdownBlock from './MarkdownBlock.vue'
import TodoBlock from './TodoBlock.vue'
import LinkBlock from './LinkBlock.vue'
import GalleryBlock from './GalleryBlock.vue'

export const blockComponents = {
  markdown: MarkdownBlock,
  todo: TodoBlock,
  link: LinkBlock,
  gallery: GalleryBlock,
}
```

**关键**：加新区块类型只改这个文件。

### 6.3 WorkspacePanel 渲染逻辑

```
WorkspacePanel
  ↓ 接收当前 NavItem（含 blocks）
  ↓ 遍历 blocks
  ↓ 根据 block_type 从 blockComponents 取组件
  ↓ 渲染每个区块，传入 block + 保存回调
  ↓ 底部渲染"+ 添加区块"
```

### 6.4 区块组件行为

**通用**：
- 展示态 / 编辑态切换（点击进入编辑，失焦或点保存退出）
- 每个区块右上角：编辑、删除
- 删除带确认

**MarkdownBlock**：
- 编辑态：`<textarea>`
- 展示态：`marked` 解析 + `DOMPurify` 消毒后 `v-html`

**TodoBlock**：
- 每项：checkbox + 文本
- 底部"+ 添加待办"
- 勾选立即保存

**LinkBlock**：
- 每项：标题 + URL
- 点击在新标签打开（pywebview 需配置支持外链）
- "+ 添加链接"

**GalleryBlock**：
- 网格显示图片
- "+ 上传图片" 按钮
- 每张图悬停显示删除

### 6.5 添加区块流程

页面底部"+ 添加区块" → 弹出选择（4 种类型） → 调 `POST /api/nav/{id}/blocks` → 刷新页面 blocks。

### 6.6 添加导航项流程（修改）

点击侧边栏"+" → 弹窗：
- 字段：title、icon、page_type（下拉，只显示 `multi_instance: true` 的类型）
- 确定后创建

### 6.7 导航拖拽排序

用原生 HTML5 DnD 或 `vuedraggable`（优先原生）。拖完调 `POST /api/nav/reorder`。

### 6.8 SPA fallback 修正

`static.py` 中：`/api/*` 路径不参与 SPA fallback。FastAPI 找不到路由就返回 API 404。

### 6.9 外链处理

pywebview 默认不能打开浏览器外链。需要：
- 后端配置 pywebview 的 `on_link_click` 回调，用系统浏览器打开
- 或前端用 `<a target="_blank">` + pywebview 配置允许

**优先方案**：pywebview 启动时设置 `webview.create_window(..., js_api=...)` 并在后端提供打开链接的接口。如果太复杂，可暂用 `window.open` + 系统默认，在 VERSIONS.md 记录为已知问题。

---

## 7. 验收标准

### 7.1 环境

```bash
cd backend && source .venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install
```

### 7.2 迁移验收

```bash
cd backend
alembic upgrade head
alembic current            # 应为最新 revision
```

期望：
- [ ] `nav_items` 表有 `page_type` 字段
- [ ] `blocks` 表存在
- [ ] 现有 6 条导航数据完整（未被清空）

### 7.3 页面类型验收

```bash
curl http://127.0.0.1:8765/api/page-types
# 返回 9 种类型（4 个 multi + 5 个单实例）

curl -X POST http://127.0.0.1:8765/api/nav \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","icon":"🧪","page_type":"todo"}'
# 返回带 id + blocks 数组（应有 1 个 todo 区块）
```

### 7.4 区块验收

```bash
curl http://127.0.0.1:8765/api/nav/1/blocks
# 返回 blocks 列表

curl -X POST http://127.0.0.1:8765/api/nav/1/blocks \
  -H "Content-Type: application/json" \
  -d '{"block_type":"todo","content":{"items":[{"text":"晨跑","done":false}]}}'
# 返回新 block
```

### 7.5 图片上传验收

```bash
curl -X POST http://127.0.0.1:8765/api/blocks/1/images \
  -F "file=@test.png"
# 返回 {"filename": "..."}
# 文件应在 backend/data/attachments/ 下
```

### 7.6 前端 GUI 验收

**你手动跑一遍 `python main.py`，验证：**

- [ ] 左侧导航项可拖拽排序，重启后顺序保留
- [ ] 点击"+"，弹窗可选页面类型（只显示多实例类型）
- [ ] 选"文档"，创建后右侧显示空 Markdown 区块
- [ ] Markdown 区块编辑、保存、刷新页面后内容还在
- [ ] 选"待办"，创建后有 1 个 todo 区块，能加待办、勾选
- [ ] 选"画廊"，上传 2 张图，能显示，刷新后还在
- [ ] 选"收藏"，加 2 条链接，能点击打开
- [ ] 删除一个区块，刷新后不复活
- [ ] 删除一个导航项，其所有区块也删（查数据库确认）
- [ ] 关窗口重启，所有数据和布局保留

### 7.7 顺手修的问题验收

- [ ] emoji 复合表情（如 👨‍👩‍👧）能存能显示
- [ ] 校验错误返回具体字段名（curl 发空 title，返回带 `field` 的 detail）
- [ ] `GET /api/nav/99999` 返回 404 JSON，不是 HTML

### 7.8 代码结构验收

- [ ] `page_types.py` 只有注册表，无业务逻辑
- [ ] `blocks/registry.js` 只有映射，无业务逻辑
- [ ] 加新页面类型：只改 `page_types.py`
- [ ] 加新区块类型：只改 `blocks/registry.js` + 一个 Vue 文件
- [ ] `backend/data/attachments/` 加入 `.gitignore`

---

## 8. 输出要求

### 8.1 对话末尾输出

1. 文件树（变化部分）
2. 运行命令
3. 已实现功能清单
4. 验收步骤
5. 执行指令 1-5 条的发现
6. M1 → M2 的破坏性变更（数据库 schema、接口签名、前端结构）
7. M1 遗留问题的修复清单

### 8.2 追加 `docs/VERSIONS.md`

```markdown
## M2 · <YYYY-MM-DD>
- **任务**：页面系统 + 区块系统 + Markdown/待办/链接/图片 + 导航拖拽
- **实现**：
  - 数据模型：NavItem 加 page_type，新增 Block 表，级联删除
  - 页面类型注册表（backend/app/page_types.py）
  - 区块组件注册表（frontend/src/blocks/registry.js）
  - 4 种区块类型
  - 图片上传到 backend/data/attachments/
  - 导航拖拽排序
  - 修复 M1 遗留：datetime.utcnow、emoji max_length、校验错误、SPA fallback
- **技术架构**：<实际架构说明>
- **与 M1 相比的变化**：
  - `nav_items` 新增 page_type 字段
  - 新增 `blocks` 表
  - 新增 API：/api/page-types, /api/nav/{id}, /api/nav/reorder, /api/nav/{id}/blocks, /api/blocks/{id}, /api/blocks/{id}/images, /api/attachments/{filename}
  - 前端新增 4 个区块组件
  - 错误响应格式：detail 从字符串改为对象
- **已知问题**：<列表>
- **文件变更**：<新增/修改/删除清单>
```

---

## 9. 不确定时的处理

- 遇到本任务书未覆盖的决策点，**先列 2-3 个方案 + 优缺点 + 推荐，停下问**。
- 如果发现本任务书有矛盾或遗漏，先指出再问怎么处理。

---

**M2 完成后，等人类反馈再进 M3。不要提前做 M3 的任何事。**