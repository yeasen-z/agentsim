"""
浏览器任务主体 - 模拟网页浏览器功能
包含：标签页管理、书签、历史记录、导航等功能
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent_sim.core import ToolCall, ToolDefinition, ToolExecutor, ToolRiskLevel


@dataclass
class Bookmark:
    """书签对象"""

    id: str
    title: str
    url: str
    folder: str = "未分类"
    created_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "folder": self.folder,
            "created_date": self.created_date,
        }


@dataclass
class HistoryEntry:
    """历史记录对象"""

    id: str
    title: str
    url: str
    visited_date: str = ""
    visit_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "visited_date": self.visited_date,
            "visit_count": self.visit_count,
        }


@dataclass
class Tab:
    """标签页对象"""

    id: str
    title: str
    url: str
    is_active: bool = False
    favicon: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "is_active": self.is_active,
            "favicon": self.favicon,
        }


@dataclass
class BrowserState:
    """浏览器隐藏状态"""

    tabs: Dict[str, Tab] = field(default_factory=dict)
    active_tab_id: Optional[str] = None
    bookmarks: Dict[str, Bookmark] = field(default_factory=dict)
    history: Dict[str, HistoryEntry] = field(default_factory=dict)
    bookmark_folders: List[str] = field(default_factory=lambda: ["未分类", "工作", "娱乐", "学习"])

    def __post_init__(self):
        if not self.tabs:
            self._init_default_tab()
        if not self.bookmarks:
            self._init_sample_bookmarks()
        if not self.history:
            self._init_sample_history()

    def _init_default_tab(self):
        tab = Tab(id="tab_1", title="新标签页", url="about:blank", is_active=True)
        self.tabs[tab.id] = tab
        self.active_tab_id = tab.id

    def _init_sample_bookmarks(self):
        now = datetime.now().strftime("%Y-%m-%d")
        sample_bookmarks = [
            Bookmark(
                id="bm_1",
                title="Google",
                url="https://www.google.com",
                folder="工作",
                created_date=now,
            ),
            Bookmark(
                id="bm_2", title="GitHub", url="https://github.com", folder="工作", created_date=now
            ),
            Bookmark(
                id="bm_3",
                title="YouTube",
                url="https://www.youtube.com",
                folder="娱乐",
                created_date=now,
            ),
            Bookmark(
                id="bm_4",
                title="Wikipedia",
                url="https://en.wikipedia.org",
                folder="学习",
                created_date=now,
            ),
        ]
        for bm in sample_bookmarks:
            self.bookmarks[bm.id] = bm

    def _init_sample_history(self):
        now = datetime.now()
        sample_history = [
            HistoryEntry(
                id="h_1",
                title="Python 教程",
                url="https://docs.python.org",
                visited_date=(now.replace(hour=10)).strftime("%Y-%m-%d %H:%M"),
                visit_count=3,
            ),
            HistoryEntry(
                id="h_2",
                title="Stack Overflow",
                url="https://stackoverflow.com",
                visited_date=(now.replace(hour=11)).strftime("%Y-%m-%d %H:%M"),
                visit_count=5,
            ),
            HistoryEntry(
                id="h_3",
                title="新闻网站",
                url="https://news.example.com",
                visited_date=(now.replace(hour=14)).strftime("%Y-%m-%d %H:%M"),
                visit_count=1,
            ),
        ]
        for h in sample_history:
            self.history[h.id] = h


def register_browser_tools(executor: ToolExecutor):
    """注册所有浏览器工具"""

    def get_active_tab(state: BrowserState) -> Optional[Dict[str, Any]]:
        if not state.active_tab_id or state.active_tab_id not in state.tabs:
            return None
        return state.tabs[state.active_tab_id].to_dict()

    executor.register_tool(
        name="get_active_tab",
        func=get_active_tab,
        definition=ToolDefinition(
            name="get_active_tab",
            description="获取当前活动标签页信息",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def list_tabs(state: BrowserState) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in state.tabs.values()]

    executor.register_tool(
        name="list_tabs",
        func=list_tabs,
        definition=ToolDefinition(
            name="list_tabs",
            description="列出所有打开的标签页",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def navigate_to(state: BrowserState, url: str) -> Dict[str, Any]:
        if not state.active_tab_id:
            return {"success": False, "error": "没有活动的标签页"}
        tab = state.tabs[state.active_tab_id]
        old_url = tab.url
        tab.url = url
        tab.title = f"浏览：{url}"

        entry_id = f"h_{len(state.history) + 1}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if url in [h.url for h in state.history.values()]:
            for h in state.history.values():
                if h.url == url:
                    h.visit_count += 1
                    h.visited_date = now
        else:
            state.history[entry_id] = HistoryEntry(
                id=entry_id, title=tab.title, url=url, visited_date=now
            )

        return {"success": True, "previous_url": old_url, "current_url": url}

    executor.register_tool(
        name="navigate_to",
        func=navigate_to,
        definition=ToolDefinition(
            name="navigate_to",
            description="在当前标签页导航到指定 URL",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def new_tab(state: BrowserState, url: str = "about:blank") -> Dict[str, Any]:
        tab_id = f"tab_{len(state.tabs) + 1}"
        for tab in state.tabs.values():
            tab.is_active = False
        new_tab_obj = Tab(id=tab_id, title="新标签页", url=url, is_active=True)
        state.tabs[tab_id] = new_tab_obj
        state.active_tab_id = tab_id
        return {"success": True, "tab": new_tab_obj.to_dict()}

    executor.register_tool(
        name="new_tab",
        func=new_tab,
        definition=ToolDefinition(
            name="new_tab",
            description="打开新标签页",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string", "default": "about:blank"}},
                "required": [],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def close_tab(state: BrowserState, tab_id: Optional[str] = None) -> Dict[str, Any]:
        target_id = tab_id or state.active_tab_id
        if not target_id or target_id not in state.tabs:
            return {"success": False, "error": "标签页不存在"}
        if len(state.tabs) == 1:
            return {"success": False, "error": "不能关闭最后一个标签页"}

        del state.tabs[target_id]
        remaining_tabs = list(state.tabs.keys())
        state.active_tab_id = remaining_tabs[-1]
        state.tabs[state.active_tab_id].is_active = True
        return {"success": True, "closed_tab_id": target_id}

    executor.register_tool(
        name="close_tab",
        func=close_tab,
        definition=ToolDefinition(
            name="close_tab",
            description="关闭指定标签页或当前标签页",
            parameters={
                "type": "object",
                "properties": {"tab_id": {"type": "string"}},
                "required": [],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def switch_tab(state: BrowserState, tab_id: str) -> Dict[str, Any]:
        if tab_id not in state.tabs:
            return {"success": False, "error": "标签页不存在"}
        for tab in state.tabs.values():
            tab.is_active = False
        state.tabs[tab_id].is_active = True
        state.active_tab_id = tab_id
        return {"success": True, "active_tab": state.tabs[tab_id].to_dict()}

    executor.register_tool(
        name="switch_tab",
        func=switch_tab,
        definition=ToolDefinition(
            name="switch_tab",
            description="切换到指定标签页",
            parameters={
                "type": "object",
                "properties": {"tab_id": {"type": "string"}},
                "required": ["tab_id"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def add_bookmark(
        state: BrowserState, title: str, url: Optional[str] = None, folder: str = "未分类"
    ) -> Dict[str, Any]:
        if url is None:
            if not state.active_tab_id:
                return {"success": False, "error": "没有活动的标签页"}
            url = state.tabs[state.active_tab_id].url
            if not title:
                title = state.tabs[state.active_tab_id].title

        if folder not in state.bookmark_folders:
            state.bookmark_folders.append(folder)

        bm_id = f"bm_{len(state.bookmarks) + 1}"
        new_bm = Bookmark(
            id=bm_id,
            title=title,
            url=url,
            folder=folder,
            created_date=datetime.now().strftime("%Y-%m-%d"),
        )
        state.bookmarks[bm_id] = new_bm
        return {"success": True, "bookmark": new_bm.to_dict()}

    executor.register_tool(
        name="add_bookmark",
        func=add_bookmark,
        definition=ToolDefinition(
            name="add_bookmark",
            description="添加书签",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "folder": {"type": "string", "default": "未分类"},
                },
                "required": ["title"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def list_bookmarks(state: BrowserState, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        if folder:
            return [b.to_dict() for b in state.bookmarks.values() if b.folder == folder]
        return [b.to_dict() for b in state.bookmarks.values()]

    executor.register_tool(
        name="list_bookmarks",
        func=list_bookmarks,
        definition=ToolDefinition(
            name="list_bookmarks",
            description="列出书签，可按文件夹筛选",
            parameters={
                "type": "object",
                "properties": {"folder": {"type": "string"}},
                "required": [],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def delete_bookmark(state: BrowserState, bookmark_id: str) -> Dict[str, Any]:
        if bookmark_id not in state.bookmarks:
            return {"success": False, "error": "书签不存在"}
        del state.bookmarks[bookmark_id]
        return {"success": True}

    executor.register_tool(
        name="delete_bookmark",
        func=delete_bookmark,
        definition=ToolDefinition(
            name="delete_bookmark",
            description="删除书签",
            parameters={
                "type": "object",
                "properties": {"bookmark_id": {"type": "string"}},
                "required": ["bookmark_id"],
            },
            risk_level=ToolRiskLevel.RISKY,
        ),
    )

    def get_history(state: BrowserState, limit: int = 20) -> List[Dict[str, Any]]:
        sorted_history = sorted(state.history.values(), key=lambda x: x.visited_date, reverse=True)
        return [h.to_dict() for h in sorted_history[:limit]]

    executor.register_tool(
        name="get_history",
        func=get_history,
        definition=ToolDefinition(
            name="get_history",
            description="获取浏览历史记录",
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
                "required": [],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def clear_history(state: BrowserState) -> Dict[str, Any]:
        count = len(state.history)
        state.history.clear()
        return {"success": True, "cleared_count": count}

    executor.register_tool(
        name="clear_history",
        func=clear_history,
        definition=ToolDefinition(
            name="clear_history",
            description="清除所有浏览历史",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.RISKY,
        ),
    )

    def search_history(state: BrowserState, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for h in state.history.values():
            if query_lower in h.title.lower() or query_lower in h.url.lower():
                results.append(h.to_dict())
        return sorted(results, key=lambda x: x["visited_date"], reverse=True)

    executor.register_tool(
        name="search_history",
        func=search_history,
        definition=ToolDefinition(
            name="search_history",
            description="搜索浏览历史",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_stats(state: BrowserState) -> Dict[str, Any]:
        return {
            "total_tabs": len(state.tabs),
            "total_bookmarks": len(state.bookmarks),
            "total_history_entries": len(state.history),
            "bookmark_folders": state.bookmark_folders,
        }

    executor.register_tool(
        name="get_stats",
        func=get_stats,
        definition=ToolDefinition(
            name="get_stats",
            description="获取浏览器统计信息",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )


def create_browser_executor() -> ToolExecutor:
    executor = ToolExecutor()
    register_browser_tools(executor)
    return executor


if __name__ == "__main__":
    executor = create_browser_executor()
    state = BrowserState()

    print("=== 浏览器工具测试 ===\n")

    result = executor.execute(state, ToolCall(tool_name="get_stats", arguments={}))
    print(f"1. 获取统计：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="get_active_tab", arguments={}))
    print(f"2. 获取当前标签页：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="navigate_to", arguments={"url": "https://www.example.com"})
    )
    print(f"3. 导航到网址：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="new_tab", arguments={"url": "https://www.google.com"})
    )
    print(f"4. 打开新标签页：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="list_tabs", arguments={}))
    print(f"5. 列出所有标签页：success={result.success}, count={len(result.result)}\n")

    result = executor.execute(
        state, ToolCall(tool_name="switch_tab", arguments={"tab_id": "tab_1"})
    )
    print(f"6. 切换标签页：success={result.success}\n")

    result = executor.execute(
        state, ToolCall(tool_name="add_bookmark", arguments={"title": "示例网站", "folder": "工作"})
    )
    print(f"7. 添加书签：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="list_bookmarks", arguments={"folder": "工作"})
    )
    print(f"8. 列出工作书签：success={result.success}, count={len(result.result)}\n")

    result = executor.execute(state, ToolCall(tool_name="get_history", arguments={"limit": 5}))
    print(f"9. 获取历史记录：success={result.success}, count={len(result.result)}\n")

    result = executor.execute(
        state, ToolCall(tool_name="search_history", arguments={"query": "python"})
    )
    print(f"10. 搜索历史：success={result.success}, count={len(result.result)}\n")

    print("=== 所有测试完成 ===")
