"""
日历/日程任务主体 (Calendar/Schedule Task Subject)

提供手机日历管理功能，包括创建、查看、编辑、删除日程等操作。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class CalendarEvent:
    """日程事件数据结构"""

    id: str
    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    attendees: List[str] = field(default_factory=list)
    is_all_day: bool = False
    reminder_minutes: int = 0  # 提前多少分钟提醒
    status: str = "confirmed"  # "confirmed", "cancelled", "tentative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "attendees": self.attendees,
            "is_all_day": self.is_all_day,
            "reminder_minutes": self.reminder_minutes,
            "status": self.status,
        }


@dataclass
class CalendarState:
    """日历状态"""

    events: Dict[str, CalendarEvent] = field(default_factory=dict)
    calendars: Dict[str, List[str]] = field(default_factory=dict)  # calendar_name -> [event_ids]
    _next_id: int = 1

    def get_event_count(self) -> int:
        return len(self.events)

    def get_calendar_count(self) -> int:
        return len(self.calendars)


class CalendarTools:
    """日历工具集"""

    def __init__(self):
        self.state = CalendarState()
        # 默认创建一个主日历
        self.state.calendars["primary"] = []

    def _generate_id(self) -> str:
        event_id = f"event_{self.state._next_id}"
        self.state._next_id += 1
        return event_id

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        calendar_name: str = "primary",
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出日程事件

        Args:
            start_date: 开始日期（ISO 格式字符串，如 "2024-01-01"）
            end_date: 结束日期（ISO 格式字符串）
            calendar_name: 日历名称
            status: 状态过滤（"confirmed", "cancelled", "tentative"）

        Returns:
            事件列表
        """
        results = []

        event_ids = self.state.calendars.get(calendar_name, [])

        for event_id in event_ids:
            if event_id not in self.state.events:
                continue

            event = self.state.events[event_id]

            # 按状态过滤
            if status and event.status != status:
                continue

            # 按日期范围过滤
            if start_date or end_date:
                if not event.start_time:
                    continue

                start_dt = datetime.fromisoformat(start_date) if start_date else None
                end_dt = datetime.fromisoformat(end_date) if end_date else None

                if start_dt and event.start_time < start_dt:
                    continue
                if end_dt and event.start_time > end_dt:
                    continue

            results.append(event.to_dict())

        # 按开始时间排序
        results.sort(key=lambda e: e["start_time"] or "")

        return results

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个事件详情

        Args:
            event_id: 事件 ID

        Returns:
            事件详情，如果不存在则返回 None
        """
        event = self.state.events.get(event_id)
        return event.to_dict() if event else None

    def create_event(
        self,
        title: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
        reminder_minutes: int = 0,
        calendar_name: str = "primary",
    ) -> Dict[str, Any]:
        """
        创建新事件

        Args:
            title: 事件标题（必需）
            start_time: 开始时间（ISO 格式字符串）
            end_time: 结束时间（ISO 格式字符串）
            description: 描述
            location: 地点
            attendees: 参与者列表
            is_all_day: 是否全天事件
            reminder_minutes: 提前提醒分钟数
            calendar_name: 日历名称

        Returns:
            创建的事件信息
        """
        if not title or not title.strip():
            raise ValueError("事件标题不能为空")

        event_id = self._generate_id()

        # 解析时间
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError as exc:
                raise ValueError(f"无效的开始时间格式：{start_time}") from exc

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError as exc:
                raise ValueError(f"无效的结束时间格式：{end_time}") from exc

        event = CalendarEvent(
            id=event_id,
            title=title.strip(),
            description=description.strip() if description else None,
            start_time=start_dt,
            end_time=end_dt,
            location=location.strip() if location else None,
            attendees=attendees or [],
            is_all_day=is_all_day,
            reminder_minutes=reminder_minutes,
        )

        self.state.events[event_id] = event

        # 添加到日历
        if calendar_name not in self.state.calendars:
            self.state.calendars[calendar_name] = []
        self.state.calendars[calendar_name].append(event_id)

        return event.to_dict()

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: Optional[bool] = None,
        reminder_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        更新事件信息

        Args:
            event_id: 事件 ID
            title: 新标题
            start_time: 新开始时间
            end_time: 新结束时间
            description: 新描述
            location: 新地点
            attendees: 新参与者列表
            is_all_day: 是否全天事件
            reminder_minutes: 提前提醒分钟数

        Returns:
            更新后的事件信息
        """
        if event_id not in self.state.events:
            raise ValueError(f"事件 {event_id} 不存在")

        event = self.state.events[event_id]

        if title is not None:
            if not title.strip():
                raise ValueError("事件标题不能为空")
            event.title = title.strip()

        if start_time is not None:
            try:
                event.start_time = datetime.fromisoformat(start_time) if start_time else None
            except ValueError as exc:
                raise ValueError(f"无效的开始时间格式：{start_time}") from exc

        if end_time is not None:
            try:
                event.end_time = datetime.fromisoformat(end_time) if end_time else None
            except ValueError as exc:
                raise ValueError(f"无效的结束时间格式：{end_time}") from exc

        if description is not None:
            event.description = description.strip() if description.strip() else None

        if location is not None:
            event.location = location.strip() if location.strip() else None

        if attendees is not None:
            event.attendees = attendees

        if is_all_day is not None:
            event.is_all_day = is_all_day

        if reminder_minutes is not None:
            event.reminder_minutes = reminder_minutes

        return event.to_dict()

    def delete_event(self, event_id: str) -> bool:
        """
        删除事件

        Args:
            event_id: 事件 ID

        Returns:
            是否删除成功
        """
        if event_id not in self.state.events:
            raise ValueError(f"事件 {event_id} 不存在")

        self.state.events[event_id]

        # 从所有日历中移除
        for calendar_name in self.state.calendars:
            if event_id in self.state.calendars[calendar_name]:
                self.state.calendars[calendar_name].remove(event_id)

        del self.state.events[event_id]
        return True

    def cancel_event(self, event_id: str) -> Dict[str, Any]:
        """
        取消事件

        Args:
            event_id: 事件 ID

        Returns:
            更新后的事件信息
        """
        if event_id not in self.state.events:
            raise ValueError(f"事件 {event_id} 不存在")

        event = self.state.events[event_id]
        event.status = "cancelled"

        return event.to_dict()

    def create_calendar(self, calendar_name: str) -> Dict[str, Any]:
        """
        创建新日历

        Args:
            calendar_name: 日历名称

        Returns:
            创建的日历信息
        """
        if not calendar_name or not calendar_name.strip():
            raise ValueError("日历名称不能为空")

        if calendar_name in self.state.calendars:
            raise ValueError(f"日历 {calendar_name} 已存在")

        self.state.calendars[calendar_name] = []
        return {"name": calendar_name, "event_count": 0}

    def list_calendars(self) -> List[Dict[str, Any]]:
        """
        列出所有日历

        Returns:
            日历列表
        """
        return [
            {"name": name, "event_count": len(event_ids)}
            for name, event_ids in self.state.calendars.items()
        ]

    def get_events_today(self) -> List[Dict[str, Any]]:
        """
        获取今天的日程

        Returns:
            今天的事件列表
        """
        today = datetime.now().date()
        start_str = today.isoformat() + "T00:00:00"
        end_str = today.isoformat() + "T23:59:59"

        return self.list_events(start_date=start_str, end_date=end_str)

    def get_upcoming_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取即将到来的日程

        Args:
            hours: 未来多少小时内的事件

        Returns:
            即将到来的事件列表
        """
        now = datetime.now()
        end_time = now + timedelta(hours=hours)

        return self.list_events(start_date=now.isoformat(), end_date=end_time.isoformat())


# 定义工具描述（用于注册到 ToolExecutor）
CALENDAR_TOOLS = [
    {
        "name": "list_events",
        "description": "列出日程事件，支持按日期范围和日历过滤",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期（ISO 格式）"},
                "end_date": {"type": "string", "description": "结束日期（ISO 格式）"},
                "calendar_name": {
                    "type": "string",
                    "description": "日历名称",
                    "default": "primary",
                },
                "status": {"type": "string", "description": "状态过滤"},
            },
        },
    },
    {
        "name": "get_event",
        "description": "获取单个事件详情",
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "事件 ID"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "create_event",
        "description": "创建新事件",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "事件标题"},
                "start_time": {"type": "string", "description": "开始时间（ISO 格式）"},
                "end_time": {"type": "string", "description": "结束时间（ISO 格式）"},
                "description": {"type": "string", "description": "描述"},
                "location": {"type": "string", "description": "地点"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "参与者列表",
                },
                "is_all_day": {"type": "boolean", "description": "是否全天事件"},
                "reminder_minutes": {"type": "integer", "description": "提前提醒分钟数"},
                "calendar_name": {"type": "string", "description": "日历名称"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "update_event",
        "description": "更新事件信息",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "事件 ID"},
                "title": {"type": "string", "description": "新标题"},
                "start_time": {"type": "string", "description": "新开始时间"},
                "end_time": {"type": "string", "description": "新结束时间"},
                "description": {"type": "string", "description": "新描述"},
                "location": {"type": "string", "description": "新地点"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "新参与者列表",
                },
                "is_all_day": {"type": "boolean", "description": "是否全天事件"},
                "reminder_minutes": {"type": "integer", "description": "提前提醒分钟数"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "delete_event",
        "description": "删除事件",
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "事件 ID"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "cancel_event",
        "description": "取消事件",
        "parameters": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "description": "事件 ID"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "create_calendar",
        "description": "创建新日历",
        "parameters": {
            "type": "object",
            "properties": {"calendar_name": {"type": "string", "description": "日历名称"}},
            "required": ["calendar_name"],
        },
    },
    {
        "name": "list_calendars",
        "description": "列出所有日历",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_events_today",
        "description": "获取今天的日程",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_upcoming_events",
        "description": "获取即将到来的日程",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "未来多少小时内", "default": 24}
            },
        },
    },
]


def create_calendar_executor() -> CalendarTools:
    """创建日历工具执行器实例"""
    return CalendarTools()
