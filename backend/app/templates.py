"""Page templates for Weaveverse OS.

A template is a page type plus a preset list of blocks. Add a template by
inserting one entry in TEMPLATES. Routes only read this registry.
"""

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


# 列出模板元信息，不带默认区块内容。
# List template metadata without the preset block payloads.
def list_template_summaries() -> list[dict]:
    return [
        {
            "id": key,
            "label": spec["label"],
            "description": spec["description"],
            "icon": spec["icon"],
            "page_type": spec["page_type"],
            "block_count": len(spec["default_blocks"]),
        }
        for key, spec in TEMPLATES.items()
    ]


# 按 id 取出完整模板；未知 id 返回 None。
# Return one full template, or None when the id is unknown.
def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)
