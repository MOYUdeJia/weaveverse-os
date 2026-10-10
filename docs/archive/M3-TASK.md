# Weaveverse OS · M3 任务书

> 承接 M0 / M1 / M2。M2 交付：页面类型注册表 + 区块系统（markdown/todo/link/gallery）+ 导航拖拽 + 图片上传。
> 读 `docs/VERSIONS.md`（M0/M1/M2 段）、`docs/FEATURES.md`、`docs/HANDOFF.md`。
>
> M3 是 Weaveverse OS 第一次"有料"：把 M2 的通用区块组合成具体的成长模板，
> 让用户一点就有一套搭好的健身/学习/音乐/游戏/观后感/未来规划页面。
> M3 不加数据库表，全部靠 M2 的 Block.content 扩展。

---

## 0. 执行指令

1. 执行前先检查本任务书有无错误前提、逻辑跳跃或信息缺失，有则先列出再问。
2. 不要一味迎合。区分事实、预测和主观观点。
3. 涉及数字、人物、结论时，尽可能核实来源。
4. 发现任务书说得不对，直接指出，说明依据、风险和更合适的解释。
5. 主动提醒可能被忽略的变量、成本、偏差。
6. 代码要有可读性。每个模块开头说明用途，代码块简短概括作用。
7. 任务完成后**追加** `docs/VERSIONS.md`（不覆盖 M0/M1/M2）。
8. **不确定时先列计划或提问，不要直接改代码。**

---

## 1. 目标

**要做什么**：
1. 新增 3 种区块类型：`schedule`（计划表）、`progress`（进度追踪）、`chart`（简单图表）
2. 引入"页面模板"概念：模板 = page_type + 预设的区块组合
3. 定义 6 个成长模板：健身 / 学习 / 音乐 / 游戏 / 观后感 / 未来规划
4. 前端"+"按钮支持"空白页"和"从模板创建"两种入口

**为什么**：M2 给了用户一堆"积木"，但每建一个健身页面都要手动选类型、加区块。M3 把常用组合预置好，用户一点就有完整结构。

**M3 不追求**：
- 不做数据库迁移（全部靠 Block.content 扩展）
- 不做用户自定义模板（M4/M5）
- 不做数据导出（放 M4）
- 不做 AI（M6）
- 不做真实的健身统计、课程进度算法（只是展示数据）

---

## 2. 范围

### 必须做

**3 个新块类型**

| block_type | content 结构                                                 | 用途                         |
| ---------- | ------------------------------------------------------------ | ---------------------------- |
| `schedule` | `{"entries": [{"date": "YYYY-MM-DD", "title": "...", "done": false, "note": ""}]}` | 计划表：训练计划、学习计划   |
| `progress` | `{"items": [{"label": "...", "current": 0, "total": 100, "unit": "%"}]}` | 进度追踪：课程进度、练习记录 |
| `chart`    | `{"chart_type": "line", "unit": "kg", "data": [{"label": "...", "value": 0}]}` | 简单折线图：体重、训练量     |

**页面模板**

- 后端 `backend/app/templates.py`：定义模板字典
- 模板结构：
  ```python
  {
      "id": "fitness",
      "label": "健身",
      "description": "训练计划 + 体重追踪 + 待办",
      "icon": "💪",
      "page_type": "collection",
      "default_blocks": [
          {"block_type": "schedule", "content": {"entries": []}},
          {"block_type": "chart", "content": {"chart_type": "line", "unit": "kg", "data": []}},
          {"block_type": "todo", "content": {"items": []}},
      ],
  }
  ```
- 6 个模板（见第 6 节）

**API**

- `GET /api/templates` 列出所有模板
- `POST /api/nav` 支持 `template_id` 参数（和 `page_type` 二选一）

**前端**

- 3 个新块组件：`ScheduleBlock.vue` / `ProgressBlock.vue` / `ChartBlock.vue`
- 更新 `blocks/registry.js` 注册新块
- "+"按钮弹出时提供两个入口：**新建空白页** / **从模板创建**
- 从模板创建时，显示模板卡片列表（图标 + 名称 + 描述）

### 不要做

- 不做数据库迁移（M3 不加新表、不改模型）
- 不做用户自定义模板
- 不做数据导出/导入
- 不做统计图表的高级交互（缩放、tooltip 可省）
- 不引入图表库（`chart.js` / `echarts` / `d3`）——**用原生 SVG 手写简单折线图**
- 不引入 UI 组件库
- 不引入 TypeScript
- 不改 M0/M1/M2 已有架构
- 不动 M2 的 4 个块类型

---

## 3. 技术栈（在 M2 基础上）

无新增依赖。图表用原生 SVG，不装库。

**Python**：不需要新的 pip 包。
**Node**：不需要新的 npm 包。

---

## 4. 数据模型

**无变化。** M3 完全复用 M2 的 `blocks` 表，新块类型只是 `content` 字段里 JSON 结构不同。

**为什么不需要迁移**：M2 的 `Block.content` 是 `TEXT` 存 JSON，任何结构都能塞。加新块类型 = 改 Python 校验 + 改前端渲染，不动表结构。

---

## 5. 接口契约

### `GET /api/templates`（新增）

**返回**：
```json
[
  {
    "id": "fitness",
    "label": "健身",
    "description": "训练计划 + 体重追踪 + 待办",
    "icon": "💪",
    "page_type": "collection",
    "block_count": 3
  },
  ...
]
```

**说明**：只返回元信息，不返回 `default_blocks` 全部内容（省流量）。前端点"用这个模板"后再调 `POST /api/nav`。

### `POST /api/nav`（扩展）

**请求体**：
```json
{"title": "我的健身", "icon": "💪", "template_id": "fitness"}
```

**行为**：
- `template_id` 与 `page_type` 二选一，同时给报 400
- 传 `template_id` 时：从 `templates.py` 取出 `page_type` 和 `default_blocks`，按模板创建页面
- 传 `page_type` 时：保持 M2 行为
- 都不传时：默认 `page_type="markdown"`，M2 行为

**返回**：同 M2，带 `blocks` 数组。

### 块类型校验（扩展）

`schemas.py` 里为 3 个新块类型加 content 校验：

- `schedule`：`entries` 是数组，每项 `date`/`title`/`done`/`note`
- `progress`：`items` 是数组，每项 `label`/`current`/`total`/`unit`
- `chart`：`chart_type` 是 `"line"` 或 `"bar"`，`data` 是数组，每项 `label`/`value`

校验失败返回 M2 的统一错误体 `{field, message}`。

---

## 6. 行为细节

### 6.1 3 个新块类型

#### ScheduleBlock（计划表）

- 展示：按日期分组的列表
- 每条：日期 / 标题 / 勾选框 / 备注（点击展开）
- 底部"+ 添加计划"
- 编辑态：可改日期（`<input type="date">`）、标题、备注
- 勾选立即保存

#### ProgressBlock（进度追踪）

- 展示：每项一行：标签 + 进度条 + `current/total unit`
- 底部"+ 添加进度项"
- 编辑态：可改标签、current、total、unit
- 进度条用 CSS 实现（`<div>` 宽度百分比）

#### ChartBlock（图表）

- 支持 `line`（折线）和 `bar`（柱状）两种
- 用 **原生 SVG** 画，不引入图表库
- 展示：坐标轴 + 数据点 + 连线/柱
- 底部"+ 添加数据点"
- 编辑态：可改 chart_type、unit、增删数据点
- 空数据时显示"暂无数据"

**实现提示**：
- 计算 SVG viewBox 和点的坐标
- 折线：`<polyline points="...">`
- 柱状：`<rect>` 数组
- 不需要 tooltip，鼠标悬停可省略

### 6.2 模板定义（backend/app/templates.py）

```python
TEMPLATES = {
    "fitness": {
        "label": "健身",
        "description": "训练计划 + 体重追踪 + 待办",
        "icon": "💪",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "schedule", "content": {"entries": []}},
            {"block_type": "chart", "content": {"chart_type": "line", "unit": "kg", "data": []}},
            {"block_type": "todo", "content": {"items": []}},
        ],
    },
    "study": {
        "label": "学习",
        "description": "课程进度 + 笔记 + 待办",
        "icon": "📚",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "progress", "content": {"items": []}},
            {"block_type": "markdown", "content": {"text": ""}},
            {"block_type": "todo", "content": {"items": []}},
        ],
    },
    "music": {
        "label": "音乐",
        "description": "练习进度 + 乐理笔记 + 歌单",
        "icon": "🎵",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "progress", "content": {"items": []}},
            {"block_type": "markdown", "content": {"text": ""}},
            {"block_type": "link", "content": {"links": []}},
        ],
    },
    "game": {
        "label": "游戏",
        "description": "游戏库 + 攻略笔记 + 截图",
        "icon": "🎮",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "link", "content": {"links": []}},
            {"block_type": "markdown", "content": {"text": ""}},
            {"block_type": "gallery", "content": {"images": []}},
        ],
    },
    "review": {
        "label": "观后感",
        "description": "长文 + 图片 + 外链",
        "icon": "🎬",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "markdown", "content": {"text": ""}},
            {"block_type": "gallery", "content": {"images": []}},
            {"block_type": "link", "content": {"links": []}},
        ],
    },
    "future": {
        "label": "未来规划",
        "description": "目标计划 + 长文 + 待办",
        "icon": "🧭",
        "page_type": "collection",
        "default_blocks": [
            {"block_type": "schedule", "content": {"entries": []}},
            {"block_type": "markdown", "content": {"text": ""}},
            {"block_type": "todo", "content": {"items": []}},
        ],
    },
}
```

**关键**：加新模板只改这个文件。

### 6.3 前端创建流程

**"+"按钮点击后**：

弹窗第一层，两个选项：
- **新建空白页** → 进入 M2 原流程（选 page_type）
- **从模板创建** → 进入第二层

**"从模板创建"第二层**：

- 显示 6 个模板卡片（图标 + 名称 + 描述）
- 点击卡片 → 弹出输入标题和 icon（可预填模板默认值）
- 确定 → `POST /api/nav` 带 `template_id`

### 6.4 块类型注册表更新

`frontend/src/blocks/registry.js`：

```js
import MarkdownBlock from './MarkdownBlock.vue'
import TodoBlock from './TodoBlock.vue'
import LinkBlock from './LinkBlock.vue'
import GalleryBlock from './GalleryBlock.vue'
import ScheduleBlock from './ScheduleBlock.vue'
import ProgressBlock from './ProgressBlock.vue'
import ChartBlock from './ChartBlock.vue'

export const blockComponents = {
  markdown: MarkdownBlock,
  todo: TodoBlock,
  link: LinkBlock,
  gallery: GalleryBlock,
  schedule: ScheduleBlock,
  progress: ProgressBlock,
  chart: ChartBlock,
}
```

**同时**：页面类型注册表里，新建空白页时也应该能选到 3 个新块类型（作为可选区块类型），不影响已有逻辑。

### 6.5 兼容性

- M2 的 4 个块类型行为不变
- M2 创建的页面不受影响
- M1 的老导航项（无区块）行为不变
- 现有 `/api/nav`、`/api/blocks` 接口兼容

---

## 7. 验收标准

### 7.1 环境

```bash
cd backend && source .venv/bin/activate
cd ../frontend && npm install
```

### 7.2 接口验收

```bash
curl http://127.0.0.1:8765/api/templates
# 返回 6 个模板

curl -X POST http://127.0.0.1:8765/api/nav \
  -H "Content-Type: application/json" \
  -d '{"title":"我的健身","icon":"💪","template_id":"fitness"}'
# 返回带 id + blocks（3 个区块：schedule + chart + todo）

curl -X POST http://127.0.0.1:8765/api/nav \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","icon":"🧪","template_id":"fitness","page_type":"markdown"}'
# 返回 400，不能同时给 template_id 和 page_type

curl -X POST http://127.0.0.1:8765/api/blocks/1 \
  -H "Content-Type: application/json" \
  -d '{"block_type":"schedule","content":{"entries":[{"date":"2026-10-07","title":"胸推","done":false,"note":""}]}}'
# 返回 200

curl -X POST http://127.0.0.1:8765/api/blocks/1 \
  -H "Content-Type: application/json" \
  -d '{"block_type":"schedule","content":{"entries":"not an array"}}'
# 返回 400，detail.field 指向 content
```

### 7.3 GUI 验收（核心）

启动 `python main.py`，逐项点：

**新块类型**
- [ ] 建"文档"，加一个 `schedule` 区块 → 加 2 条计划 → 勾选一条 → 刷新还在
- [ ] 加一个 `progress` 区块 → 加 3 项进度 → 拖动不会，只是显示 → 刷新还在
- [ ] 加一个 `chart` 区块 → 加 3 个数据点 → 显示折线图 → 切换成柱状图 → 刷新还在

**模板创建**
- [ ] 点"+" → 显示"新建空白页"和"从模板创建"
- [ ] 点"从模板创建" → 显示 6 个模板卡片（健身/学习/音乐/游戏/观后感/未来规划）
- [ ] 选"健身" → 输入标题"我的健身" → 创建成功
- [ ] 右侧自动显示 3 个区块：计划表 + 图表 + 待办
- [ ] 每个模板都试一遍（6 个模板都能正常创建）

**兼容性**
- [ ] M2 创建的旧页面正常显示
- [ ] M1 的旧导航项（无区块）正常显示空页
- [ ] 删除模板创建的页面 → 其区块也删

### 7.4 代码结构验收

- [ ] 加新模板只改 `templates.py`
- [ ] 加新块类型只改 `blocks/registry.js` + 一个 Vue 文件 + `schemas.py` 校验
- [ ] 图表没有引入任何库（检查 `package.json` 没有新增图表依赖）

---

## 8. 输出要求

### 8.1 对话末尾输出

1. 文件树变化
2. 运行命令
3. 已实现功能清单
4. 验收步骤
5. 执行指令第 1-5 条的发现
6. M2 → M3 的破坏性变更（如有）
7. 3 个新块类型的 content schema 说明

### 8.2 追加 `docs/VERSIONS.md`

```markdown
## M3 · <YYYY-MM-DD>
- **任务**：3 个新块类型 + 页面模板 + 6 个成长模板
- **实现**：
  - 新增 schedule / progress / chart 块类型
  - 新增 templates.py（6 个模板定义）
  - 新增 GET /api/templates
  - POST /api/nav 支持 template_id
  - 前端：3 个新块组件 + 模板选择 UI
- **技术架构**：无数据库变化。模板硬编码在 templates.py。图表用原生 SVG。
- **与 M2 相比的变化**：
  - 新增 block_type：schedule / progress / chart
  - 新增接口：GET /api/templates
  - POST /api/nav 新增可选参数 template_id
  - 前端"+"按钮改为两级菜单
- **已知问题**：<列表>
- **文件变更**：<新增/修改清单>
```

---

## 9. 不确定时的处理

- 遇到本任务书未覆盖的决策点，**先列 2-3 个方案 + 优缺点 + 推荐，停下问**。
- 如果发现本任务书有矛盾或遗漏，先指出再问怎么处理。

---

**M3 完成后，等人类反馈再进 M4。不要提前做 M4 的任何事。**