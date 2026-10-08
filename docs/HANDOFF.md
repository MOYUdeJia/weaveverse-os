# Weaveverse OS · 交接说明

> 新 agent 接手前先读本文。本文只负责导航，不重复其他文件的内容。

## 第一步：读文件

按顺序读：

1. `docs/HANDOFF.md`（你正在读的）
2. `docs/<当前版本>-TASK.md`（本次任务书）

**不要主动读 `VERSIONS.md`、`FEATURES.md`、历史任务书。**
任务书里会写明必要的历史上下文。如果执行中确实需要查历史，
按需查阅特定段落，不要全文读。

---

## 工作约定

- 不确定时先列 2-3 个方案 + 优缺点 + 推荐，停下问，不要自己拍板
- 改多个文件前，先在对话里列文件清单
- 不做任务书之外的事，不提前做下一个阶段
- 完成后**追加** `docs/VERSIONS.md`（不覆盖旧段落）
- 每个模块开头说明用途，代码块简短概括作用
- 涉及关键决策时，区分事实、预测、主观观点
- **留出创新空间**：任务书里如果没锁死实现，允许你提出更好的方案
  （比如更舒服的交互、更优雅的数据结构）。提出时说明理由和取舍，
  被采纳会加到版本记录里。
- **优先用现成库**：加新功能时，先搜有没有成熟的第三方库，
  不从 0 写。选库时说明理由（维护活跃度、与 Vue 3 兼容、体积）。
  选库后要给出"为什么不用其他替代方案"。

---

## 执行节奏

任务书一般会拆成 2 个阶段：

- **阶段 1**：数据层 / 架构层（迁移、模型、注册表）。做完停下汇报，等确认。
- **阶段 2**：功能层（API、前端、交互）。一路做完再汇报。

数据层错了全盘崩，功能层错了局部修。所以阶段 1 必须停下确认。

---

## 环境

| 项        | 位置                                            |
| --------- | ----------------------------------------------- |
| 项目根    | `D:\weaveverse-os`                              |
| 后端 venv | `backend/.venv`                                 |
| 数据库    | `backend/data/weaveverse.db`（已在 .gitignore） |
| 附件目录  | `backend/data/attachments/`                     |
| 前端源码  | `frontend/src/`                                 |

**常用命令**：

```powershell
# 启动（生产模式）
cd D:\weaveverse-os\frontend && npm run build
cd ..\backend && .venv\Scripts\activate
python main.py

# 开发模式
# 终端 1
cd backend && .venv\Scripts\activate
$env:WEAVEVERSE_DEV="1"; python main.py
# 终端 2
cd frontend && npm run dev

# 迁移
python -m alembic upgrade head
python -m alembic current
```

---

## 技术栈速查

| 层面   | 技术                                          |
| ------ | --------------------------------------------- |
| 后端   | Python 3.11+ / FastAPI / uvicorn              |
| 数据   | SQLModel / SQLite / Alembic                   |
| 前端   | Vue 3 / Vite 7 / Tailwind 3 / JavaScript      |
| 桌面壳 | pywebview                                     |
| 通信   | REST API（`/api/`，不带版本号） + SSE（未来） |

**禁忌**：
- 不引入 UI 组件库（Element Plus / Ant Design / Vuetify）
- 不引入 TypeScript
- 不改 pywebview / uvicorn 的线程模型
- 不 drop 数据库来"重来"

---

## 目录约定

```
backend/app/
├── models.py        # 数据库模型（只有字段定义）
├── schemas.py       # API 输入输出格式（Pydantic）
├── crud.py          # 数据库操作
├── db.py            # 连接管理
├── seed.py          # 首次启动数据
├── page_types.py    # 页面类型注册表
├── errors.py        # 统一错误格式
└── routes/          # HTTP 层（只做收请求、调 crud、返回）

frontend/src/
├── api/client.js    # 封装所有后端请求
├── blocks/          # 区块组件 + registry.js（区块类型注册表）
├── components/      # 通用组件（侧边栏、工作区、弹窗等）
└── App.vue          # 根组件
```

**分层原则**：routes 只做 HTTP，crud 只做数据，models 只定义结构。加新功能时，加新文件而不是改老文件。

---

## 遇到问题时

1. 先检查是不是文档里已经写过（`VERSIONS.md` 的"已知问题"段）
2. 如果是任务书遗漏，先指出，再问
3. 如果涉及架构决策，列方案而不是直接选