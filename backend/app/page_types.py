"""Page type registry for Weaveverse OS.

Add a new page type by inserting one entry here. Do not change routes.
"""

# 分组导览的类型名。每个分组一条，只能由分组接口创建。
# Page type for the per-group overview. Group routes create it; users cannot.
OVERVIEW_PAGE_TYPE = "group_overview"


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
    # multi_instance 为 False 只表示新建菜单不能选它。
    # 每个分组仍有自己的一条导览页，不走全局「只能有一个」校验。
    "group_overview": {
        "layer": "core",
        "label": "分组导览",
        "multi_instance": False,
        "default_blocks": [],
    },
}
