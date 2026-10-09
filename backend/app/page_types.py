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
    # 专用页：创建时自动放一块固定区块，用户不能删，也不能再追加区块。
    # Focus pages start with one fixed block. It cannot be deleted or joined by others.
    "doc": {
        "layer": "focus",
        "label": "长文",
        "multi_instance": True,
        "default_icon": "📄",
        "fixed_block": "markdown",
        "default_blocks": [
            {"block_type": "markdown", "content": {"text": ""}},
        ],
    },
    "plain": {
        "layer": "focus",
        "label": "笔记",
        "multi_instance": True,
        "default_icon": "📝",
        "fixed_block": "plain_text",
        "default_blocks": [
            {
                "block_type": "plain_text",
                "content": {"mode": "numbered", "lines": [{"text": "", "color": ""}]},
            },
        ],
    },
    "bookmarks": {
        "layer": "focus",
        "label": "网址集",
        "multi_instance": True,
        "default_icon": "🔖",
        "fixed_block": "bookmarks",
        "default_blocks": [
            {"block_type": "bookmarks", "content": {"sections": [{"name": "收藏", "items": []}]}},
        ],
    },
    "canvas": {
        "layer": "focus",
        "label": "白板",
        "multi_instance": True,
        "default_icon": "🎨",
        "fixed_block": "canvas",
        "default_blocks": [
            {"block_type": "canvas", "content": {"objects": []}},
        ],
    },
    "inbox": {
        "layer": "focus",
        "label": "收件箱",
        "multi_instance": False,
        "default_icon": "📥",
        "fixed_block": "plain_text",
        "default_blocks": [
            {
                "block_type": "plain_text",
                "content": {"mode": "numbered", "lines": [{"text": "", "color": ""}]},
            },
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


# 页面层级。没写 layer 的类型都是积木页（flex）。
# Layer of a page type. Entries without one are flex pages.
def page_layer(page_type: str) -> str:
    spec = PAGE_TYPES.get(page_type) or {}
    return spec.get("layer") or "flex"


def is_focus_page(page_type: str) -> bool:
    return page_layer(page_type) == "focus"


# 专用页那一块不能删的区块类型。普通页返回空。
# Block type pinned to a focus page. Ordinary pages return nothing.
def fixed_block_type(page_type: str) -> str | None:
    spec = PAGE_TYPES.get(page_type) or {}
    return spec.get("fixed_block")


def default_icon_for(page_type: str) -> str:
    spec = PAGE_TYPES.get(page_type) or {}
    return spec.get("default_icon") or ""
