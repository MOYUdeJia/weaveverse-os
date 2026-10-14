# Weaveverse 主题文件（`.wvtheme`）

主题是一份 JSON。扩展名用 `.wvtheme` 或 `.json` 都可以。

## 字段

| 字段 | 必填 | 说明 |
| ---- | ---- | ---- |
| `format` | 建议 | 固定 `weaveverse-theme` |
| `spec` | 建议 | 目前为 `1` |
| `id` | 否 | 小写字母、数字、短横线；不要和预设 id 冲突 |
| `name` | 是 | 显示名 |
| `author` | 否 | 作者 |
| `version` | 否 | 如 `1.0.0` |
| `vars` | 是 | CSS 颜色 |

`vars` 键：

| 键 | 必填 | 用途 |
| -- | ---- | ---- |
| `dawn` | 是 | 窗口底色 |
| `group` | 是 | 分组栏 |
| `nav` | 是 | 导航栏 |
| `work` | 是 | 工作区 |
| `orb` | 否 | 悬浮球 |
| `progress` | 否 | 进度条 |

颜色只接受 `#RRGGBB`、`#RRGGBBAA`、`rgb()`、`rgba()`。

## 示例

```json
{
  "format": "weaveverse-theme",
  "spec": 1,
  "id": "mist-blue",
  "name": "雾蓝",
  "author": "example",
  "version": "1.0.0",
  "vars": {
    "dawn": "#e7f1fb",
    "group": "#d5e6f6",
    "nav": "rgba(238, 246, 252, 0.92)",
    "work": "rgba(246, 250, 253, 0.94)",
    "orb": "#e7f1fb",
    "progress": "#3f6f57"
  }
}
```

预设五套（暖白 / 薄荷 / 天蓝 / 樱粉 / 灰调）不能删除。导入的主题存在 `appearance.json` 的 `custom_themes` 里。
