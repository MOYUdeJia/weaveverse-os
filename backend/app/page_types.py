"""Page type registry for Weaveverse OS.

Add a new page type by inserting one entry here. Do not change routes.
"""

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
    "bookshelf": {"label": "书架", "multi_instance": False, "default_blocks": []},
    "idea_box": {"label": "IDEA 栏", "multi_instance": False, "default_blocks": []},
    "vault": {"label": "密码箱", "multi_instance": False, "default_blocks": []},
    "future_plan": {"label": "未来规划", "multi_instance": False, "default_blocks": []},
    "habit_tracker": {"label": "习惯追踪", "multi_instance": False, "default_blocks": []},
}
