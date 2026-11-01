# 插件开发指南

插件是放在用户数据目录 `plugins/` 里的一个文件夹。宿主启动时会扫描每个子文件夹的 `manifest.json`。点开之后，插件页面在右侧工作区的 iframe 里打开，和主界面隔开。

示例插件是 `hello-world`。第一次启动会从程序自带的副本复制到 `plugins/hello-world/`。

## 目录

```
plugins/
└── hello-world/
    ├── manifest.json
    └── index.html
```

文件夹名必须和 `manifest.json` 里的 `id` 相同。

## manifest.json

| 字段 | 说明 |
| --- | --- |
| `id` | 小写字母、数字、连字符，1–41 位，并且等于文件夹名 |
| `name` | 面板上显示的名字，最长 40 字 |
| `version` | 版本字符串，最长 20 字 |
| `icon` | 面板上的短标记，最长 4 字。用一个字母即可 |
| `entry` | 入口 HTML，相对插件目录，例如 `index.html` |

`hello-world` 的清单：

```json
{
  "id": "hello-world",
  "name": "Hello World",
  "version": "1.0.0",
  "icon": "W",
  "entry": "index.html"
}
```

## 页面里能写什么

入口是一份普通 HTML。样式和脚本写在这份文件里面。

当前隔离下，插件页面不能：

- 读取或修改宿主的 DOM
- 请求 `/api/` 或其他网络地址
- 用 `<script src>`、`<link>` 或外链图片加载文件
- 提交表单，或把整个窗口导航走

图片若需要，用 data URI 写进 HTML。

## 和宿主说话

iframe 没有宿主的同源权限。唯一的通道是 `postMessage`。宿主只认来自这块 iframe、且 `source` 为 `wv-plugin` 的消息。

插件发出：

```js
parent.postMessage({ source: "wv-plugin", type: "ready" }, "*")
parent.postMessage({ source: "wv-plugin", type: "toast", text: "一句短提示" }, "*")
```

`toast` 的文字会被截到 200 字，显示在宿主的提示条上。

页面加载完成后，宿主会发回：

```js
{ source: "wv-host", type: "hello", id: "hello-world", name: "Hello World" }
```

插件可以监听，也可以不听。不要把密钥、路径或用户数据放进这个消息。宿主现在也不会通过它下发这些东西。

## 安装、导出、删除

管理面板在主窗口右下角，插头图标，和 AI 按钮并排。

- 导入：选择一个 `.zip`。压缩包根上要有 `manifest.json`，或者只有一层文件夹、清单在那一层里。单包不超过 8MB，解压后不超过 32MB。`id` 已存在时覆盖。
- 导出：下载 `<id>.zip`。
- 删除：先点一次「删除」，再点「确认删除」。
- 市场：同一面板里的「市场」页，现在只有「敬请期待」。

接口：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/api/plugins` | 已安装列表 |
| POST | `/api/plugins/import` | 上传字段名 `file` 的 zip |
| GET | `/api/plugins/{id}/export` | 下载 zip |
| DELETE | `/api/plugins/{id}` | 删除 |
| GET | `/api/plugins/{id}/files/{path}` | iframe 读取入口和同目录文件 |

## 自己做一个

1. 新建文件夹，名字用 `id`。
2. 写入上面的 `manifest.json`，`entry` 指向 `index.html`。
3. 按 `backend/app/bundled_plugins/hello-world/index.html` 写一页，脚本保持内联。
4. 打成 zip，在插件面板里导入。或直接把文件夹放进数据目录的 `plugins/`。
5. 打开插件，确认它出现在右侧工作区，并且点按钮能在宿主弹出提示。

开发时数据目录默认是 `backend/data/`。如果在设置里迁走过数据，以那次选择的目录为准。
