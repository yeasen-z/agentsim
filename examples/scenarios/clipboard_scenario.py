"""
剪贴板任务主体 (Clipboard Task Subject)
模拟手机剪贴板功能，支持文本、图片（模拟）的复制、粘贴、历史记录管理。
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentsim.core import (
    ToolCall,
    ToolDefine,
    ToolExecutor,
    ToolResult,
)

# --- 状态定义 ---


@dataclass
class ClipboardItem:
    content: str
    item_type: str  # "text", "image", "link"
    source_app: str
    timestamp: float


@dataclass
class ClipboardState:
    current_item: Optional[ClipboardItem] = None
    history: List[ClipboardItem] = field(default_factory=list)
    max_history: int = 10
    pinned_items: List[ClipboardItem] = field(default_factory=list)


# --- 工具实现 ---


def copy_text(state: ClipboardState, text: str, source_app: str = "unknown") -> Dict[str, Any]:
    """复制文本到剪贴板"""
    item = ClipboardItem(
        content=text, item_type="text", source_app=source_app, timestamp=time.time()
    )
    state.current_item = item
    state.history.insert(0, item)
    if len(state.history) > state.max_history:
        state.history = state.history[: state.max_history]
    return {
        "success": True,
        "message": f"Copied text: {text[:20]}...",
        "result": {"length": len(text)},
        "state_changed": True,
    }


def paste_text(state: ClipboardState) -> Dict[str, Any]:
    """从剪贴板粘贴文本"""
    if state.current_item is None:
        return {"success": False, "message": "Clipboard is empty"}
    if state.current_item.item_type != "text":
        return {"success": False, "message": f"Cannot paste {state.current_item.item_type} as text"}
    return {
        "success": True,
        "message": "Pasted successfully",
        "result": {"content": state.current_item.content},
    }


def get_history(state: ClipboardState, limit: int = 5) -> Dict[str, Any]:
    """获取剪贴板历史记录"""
    items = state.history[:limit]
    return {
        "success": True,
        "message": f"Retrieved {len(items)} history items",
        "result": [
            {"content": i.content[:30], "type": i.item_type, "time": i.timestamp} for i in items
        ],
    }


def clear_history(state: ClipboardState) -> Dict[str, Any]:
    """清空剪贴板历史（保留当前项）"""
    state.history = []
    return {"success": True, "message": "Clipboard history cleared", "state_changed": True}


def pin_item(state: ClipboardState, index: int = 0) -> Dict[str, Any]:
    """置顶剪贴板历史中的某一项"""
    if not state.history or index >= len(state.history):
        return {"success": False, "message": "Invalid index"}
    item = state.history[index]
    state.pinned_items.append(item)
    return {
        "success": True,
        "message": f"Pinned item: {item.content[:20]}...",
        "state_changed": True,
    }


def get_pinned(state: ClipboardState) -> Dict[str, Any]:
    """获取所有置顶项"""
    return {
        "success": True,
        "message": f"Retrieved {len(state.pinned_items)} pinned items",
        "result": [{"content": i.content, "type": i.item_type} for i in state.pinned_items],
    }


def delete_history_item(state: ClipboardState, index: int) -> Dict[str, Any]:
    """删除历史中的某一项"""
    if not state.history or index >= len(state.history):
        return {"success": False, "message": "Invalid index"}
    state.history.pop(index)
    return {"success": True, "message": f"Deleted item at index {index}", "state_changed": True}


def copy_link(state: ClipboardState, url: str, source_app: str = "browser") -> Dict[str, Any]:
    """复制链接"""
    if not url.startswith(("http://", "https://")):
        return {"success": False, "message": "Invalid URL format"}
    item = ClipboardItem(
        content=url, item_type="link", source_app=source_app, timestamp=time.time()
    )
    state.current_item = item
    state.history.insert(0, item)
    if len(state.history) > state.max_history:
        state.history = state.history[: state.max_history]
    return {
        "success": True,
        "message": f"Copied link: {url}",
        "result": {"url": url},
        "state_changed": True,
    }


def copy_image_mock(
    state: ClipboardState, image_id: str, source_app: str = "gallery"
) -> Dict[str, Any]:
    """模拟复制图片（仅记录 ID）"""
    item = ClipboardItem(
        content=f"[IMAGE:{image_id}]",
        item_type="image",
        source_app=source_app,
        timestamp=time.time(),
    )
    state.current_item = item
    state.history.insert(0, item)
    if len(state.history) > state.max_history:
        state.history = state.history[: state.max_history]
    return {
        "success": True,
        "message": f"Copied image reference: {image_id}",
        "state_changed": True,
    }


def get_clipboard_info(state: ClipboardState) -> Dict[str, Any]:
    """获取当前剪贴板信息"""
    if state.current_item is None:
        return {"success": True, "message": "Clipboard is empty", "result": {"empty": True}}
    return {
        "success": True,
        "message": "Current clipboard info retrieved",
        "result": {
            "type": state.current_item.item_type,
            "preview": state.current_item.content[:50],
            "source": state.current_item.source_app,
            "time_ago": f"{time.time() - state.current_item.timestamp:.1f}s ago",
        },
    }


# --- 执行器构建 ---


def register_clipboard_tools(executor: ToolExecutor):
    """Register all tools for the clipboard scenario."""

    def copy_text_func(
        state: ClipboardState, text: str = "", source_app: str = "unknown"
    ) -> ToolResult:
        return copy_text(state, text, source_app)

    executor.register_tool(
        name="copy_text",
        func=copy_text_func,
        definition=ToolDefine(
            name="copy_text",
            description="Copy text to clipboard",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text content to copy"},
                    "source_app": {
                        "type": "string",
                        "description": "Source application name",
                        "default": "unknown",
                    },
                },
                "required": ["text"],
            },
            category="write",
        ),
    )

    def paste_text_func(state: ClipboardState) -> ToolResult:
        return paste_text(state)

    executor.register_tool(
        name="paste_text",
        func=paste_text_func,
        definition=ToolDefine(
            name="paste_text",
            description="Paste text from clipboard",
            parameters={"type": "object", "properties": {}},
            category="read",
        ),
    )

    def get_history_func(state: ClipboardState, limit: int = 5) -> ToolResult:
        return get_history(state, limit)

    executor.register_tool(
        name="get_history",
        func=get_history_func,
        definition=ToolDefine(
            name="get_history",
            description="Get clipboard history",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of items to retrieve",
                        "default": 5,
                    }
                },
            },
            category="read",
        ),
    )

    def clear_history_func(state: ClipboardState) -> ToolResult:
        return clear_history(state)

    executor.register_tool(
        name="clear_history",
        func=clear_history_func,
        definition=ToolDefine(
            name="clear_history",
            description="Clear clipboard history",
            parameters={"type": "object", "properties": {}},
            category="write",
        ),
    )

    def pin_item_func(state: ClipboardState, index: int = 0) -> ToolResult:
        return pin_item(state, index)

    executor.register_tool(
        name="pin_item",
        func=pin_item_func,
        definition=ToolDefine(
            name="pin_item",
            description="Pin an item from history",
            parameters={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Index of item to pin",
                        "default": 0,
                    }
                },
            },
            category="write",
        ),
    )

    def get_pinned_func(state: ClipboardState) -> ToolResult:
        return get_pinned(state)

    executor.register_tool(
        name="get_pinned",
        func=get_pinned_func,
        definition=ToolDefine(
            name="get_pinned",
            description="Get all pinned items",
            parameters={"type": "object", "properties": {}},
            category="read",
        ),
    )

    def delete_history_item_func(state: ClipboardState, index: int = 0) -> ToolResult:
        return delete_history_item(state, index)

    executor.register_tool(
        name="delete_history_item",
        func=delete_history_item_func,
        definition=ToolDefine(
            name="delete_history_item",
            description="Delete a specific history item",
            parameters={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Index of item to delete",
                        "default": 0,
                    }
                },
            },
            category="write",
        ),
    )

    def copy_link_func(
        state: ClipboardState, url: str = "", source_app: str = "browser"
    ) -> ToolResult:
        return copy_link(state, url, source_app)

    executor.register_tool(
        name="copy_link",
        func=copy_link_func,
        definition=ToolDefine(
            name="copy_link",
            description="Copy a URL link",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to copy"},
                    "source_app": {
                        "type": "string",
                        "description": "Source application",
                        "default": "browser",
                    },
                },
                "required": ["url"],
            },
            category="write",
        ),
    )

    def copy_image_mock_func(
        state: ClipboardState, image_id: str = "img_001", source_app: str = "gallery"
    ) -> ToolResult:
        return copy_image_mock(state, image_id, source_app)

    executor.register_tool(
        name="copy_image_mock",
        func=copy_image_mock_func,
        definition=ToolDefine(
            name="copy_image_mock",
            description="Mock copy an image",
            parameters={
                "type": "object",
                "properties": {
                    "image_id": {
                        "type": "string",
                        "description": "Image identifier",
                        "default": "img_001",
                    },
                    "source_app": {
                        "type": "string",
                        "description": "Source application",
                        "default": "gallery",
                    },
                },
            },
            category="write",
        ),
    )

    def get_clipboard_info_func(state: ClipboardState) -> ToolResult:
        return get_clipboard_info(state)

    executor.register_tool(
        name="get_clipboard_info",
        func=get_clipboard_info_func,
        definition=ToolDefine(
            name="get_clipboard_info",
            description="Get current clipboard status",
            parameters={"type": "object", "properties": {}},
            category="read",
        ),
    )


def create_clipboard_executor() -> ToolExecutor:
    executor = ToolExecutor()
    register_clipboard_tools(executor)
    return executor


if __name__ == "__main__":
    # 简单测试
    from agentsim.core import ToolCall

    state = ClipboardState()
    executor = create_clipboard_executor()

    print("=== Testing Clipboard Scenario ===")

    # 测试复制
    res = executor.execute(
        state,
        ToolCall(tool_name="copy_text", arguments={"text": "Hello World", "source_app": "notes"}),
    )
    print(f"Copy: {res}")

    # 测试粘贴
    res = executor.execute(state, ToolCall(tool_name="paste_text", arguments={}))
    print(f"Paste: {res}")

    # 测试历史
    executor.execute(
        state, ToolCall(tool_name="copy_link", arguments={"url": "https://example.com"})
    )
    executor.execute(
        state, ToolCall(tool_name="copy_image_mock", arguments={"image_id": "photo_123"})
    )
    res = executor.execute(state, ToolCall(tool_name="get_history", arguments={"limit": 10}))
    print(f"History: {res.result}")

    print("Clipboard scenario tests passed!")
