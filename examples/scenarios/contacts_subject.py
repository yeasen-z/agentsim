"""
联系人/通讯录任务主体 (Contacts Task Subject)

提供手机通讯录管理功能，包括查看、添加、编辑、删除联系人等操作。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Contact:
    """联系人数据结构"""

    id: str
    name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "company": self.company,
            "notes": self.notes,
            "tags": self.tags,
        }


@dataclass
class ContactsState:
    """联系人状态"""

    contacts: Dict[str, Contact] = field(default_factory=dict)
    groups: Dict[str, List[str]] = field(default_factory=dict)  # group_name -> [contact_ids]

    def get_contact_count(self) -> int:
        return len(self.contacts)

    def get_group_count(self) -> int:
        return len(self.groups)


class ContactsTools:
    """联系人工具集"""

    def __init__(self):
        self.state = ContactsState()
        self._next_id = 1

    def _generate_id(self) -> str:
        contact_id = f"contact_{self._next_id}"
        self._next_id += 1
        return contact_id

    def list_contacts(
        self, query: Optional[str] = None, group: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出联系人

        Args:
            query: 可选的搜索关键词（匹配姓名、电话、邮箱）
            group: 可选的分组名称

        Returns:
            联系人列表
        """
        results = []

        for contact in self.state.contacts.values():
            # 按分组过滤
            if group:
                if group not in self.state.groups:
                    continue
                if contact.id not in self.state.groups[group]:
                    continue

            # 按查询关键词过滤
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in contact.name.lower()
                    or query_lower in contact.phone
                    or (contact.email and query_lower in contact.email.lower())
                ):
                    continue

            results.append(contact.to_dict())

        return results

    def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个联系人详情

        Args:
            contact_id: 联系人ID

        Returns:
            联系人详情，如果不存在则返回None
        """
        contact = self.state.contacts.get(contact_id)
        return contact.to_dict() if contact else None

    def add_contact(
        self,
        name: str,
        phone: str,
        email: Optional[str] = None,
        company: Optional[str] = None,
        notes: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        添加新联系人

        Args:
            name: 姓名（必需）
            phone: 电话号码（必需）
            email: 邮箱（可选）
            company: 公司（可选）
            notes: 备注（可选）
            groups: 要加入的分组列表（可选）

        Returns:
            新创建的联系人信息
        """
        if not name or not name.strip():
            raise ValueError("姓名不能为空")
        if not phone or not phone.strip():
            raise ValueError("电话号码不能为空")

        contact_id = self._generate_id()
        contact = Contact(
            id=contact_id,
            name=name.strip(),
            phone=phone.strip(),
            email=email.strip() if email else None,
            company=company.strip() if company else None,
            notes=notes.strip() if notes else None,
        )

        self.state.contacts[contact_id] = contact

        # 添加到分组
        if groups:
            for group_name in groups:
                if group_name not in self.state.groups:
                    self.state.groups[group_name] = []
                if contact_id not in self.state.groups[group_name]:
                    self.state.groups[group_name].append(contact_id)

        return contact.to_dict()

    def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新联系人信息

        Args:
            contact_id: 联系人ID
            name: 新姓名（可选）
            phone: 新电话号码（可选）
            email: 新邮箱（可选）
            company: 新公司（可选）
            notes: 新备注（可选）

        Returns:
            更新后的联系人信息

        Raises:
            ValueError: 如果联系人不存在
        """
        if contact_id not in self.state.contacts:
            raise ValueError(f"联系人 {contact_id} 不存在")

        contact = self.state.contacts[contact_id]

        if name is not None:
            if not name.strip():
                raise ValueError("姓名不能为空")
            contact.name = name.strip()
        if phone is not None:
            if not phone.strip():
                raise ValueError("电话号码不能为空")
            contact.phone = phone.strip()
        if email is not None:
            contact.email = email.strip() if email.strip() else None
        if company is not None:
            contact.company = company.strip() if company.strip() else None
        if notes is not None:
            contact.notes = notes.strip() if notes.strip() else None

        return contact.to_dict()

    def delete_contact(self, contact_id: str) -> bool:
        """
        删除联系人

        Args:
            contact_id: 联系人ID

        Returns:
            是否删除成功

        Raises:
            ValueError: 如果联系人不存在
        """
        if contact_id not in self.state.contacts:
            raise ValueError(f"联系人 {contact_id} 不存在")

        del self.state.contacts[contact_id]

        # 从所有分组中移除
        for group_name in self.state.groups:
            if contact_id in self.state.groups[group_name]:
                self.state.groups[group_name].remove(contact_id)

        return True

    def create_group(self, group_name: str) -> Dict[str, Any]:
        """
        创建新分组

        Args:
            group_name: 分组名称

        Returns:
            分组信息
        """
        if not group_name or not group_name.strip():
            raise ValueError("分组名称不能为空")

        if group_name in self.state.groups:
            raise ValueError(f"分组 {group_name} 已存在")

        self.state.groups[group_name] = []
        return {"name": group_name, "member_count": 0}

    def add_to_group(self, contact_id: str, group_name: str) -> Dict[str, Any]:
        """
        将联系人添加到分组

        Args:
            contact_id: 联系人ID
            group_name: 分组名称

        Returns:
            分组信息
        """
        if contact_id not in self.state.contacts:
            raise ValueError(f"联系人 {contact_id} 不存在")

        if group_name not in self.state.groups:
            raise ValueError(f"分组 {group_name} 不存在")

        if contact_id not in self.state.groups[group_name]:
            self.state.groups[group_name].append(contact_id)

        return {"name": group_name, "member_count": len(self.state.groups[group_name])}

    def remove_from_group(self, contact_id: str, group_name: str) -> Dict[str, Any]:
        """
        从分组中移除联系人

        Args:
            contact_id: 联系人ID
            group_name: 分组名称

        Returns:
            分组信息
        """
        if group_name not in self.state.groups:
            raise ValueError(f"分组 {group_name} 不存在")

        if contact_id in self.state.groups[group_name]:
            self.state.groups[group_name].remove(contact_id)

        return {"name": group_name, "member_count": len(self.state.groups[group_name])}

    def list_groups(self) -> List[Dict[str, Any]]:
        """
        列出所有分组

        Returns:
            分组列表
        """
        return [
            {"name": name, "member_count": len(members)}
            for name, members in self.state.groups.items()
        ]


# 定义工具描述（用于注册到 ToolExecutor）
CONTACTS_TOOLS = [
    {
        "name": "list_contacts",
        "description": "列出联系人，支持按关键词搜索和按分组过滤",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词（匹配姓名、电话、邮箱）"},
                "group": {"type": "string", "description": "分组名称"},
            },
        },
    },
    {
        "name": "get_contact",
        "description": "获取单个联系人详情",
        "parameters": {
            "type": "object",
            "properties": {"contact_id": {"type": "string", "description": "联系人ID"}},
            "required": ["contact_id"],
        },
    },
    {
        "name": "add_contact",
        "description": "添加新联系人",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "姓名"},
                "phone": {"type": "string", "description": "电话号码"},
                "email": {"type": "string", "description": "邮箱"},
                "company": {"type": "string", "description": "公司"},
                "notes": {"type": "string", "description": "备注"},
                "groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要加入的分组列表",
                },
            },
            "required": ["name", "phone"],
        },
    },
    {
        "name": "update_contact",
        "description": "更新联系人信息",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "联系人ID"},
                "name": {"type": "string", "description": "新姓名"},
                "phone": {"type": "string", "description": "新电话号码"},
                "email": {"type": "string", "description": "新邮箱"},
                "company": {"type": "string", "description": "新公司"},
                "notes": {"type": "string", "description": "新备注"},
            },
            "required": ["contact_id"],
        },
    },
    {
        "name": "delete_contact",
        "description": "删除联系人",
        "parameters": {
            "type": "object",
            "properties": {"contact_id": {"type": "string", "description": "联系人ID"}},
            "required": ["contact_id"],
        },
    },
    {
        "name": "create_group",
        "description": "创建新分组",
        "parameters": {
            "type": "object",
            "properties": {"group_name": {"type": "string", "description": "分组名称"}},
            "required": ["group_name"],
        },
    },
    {
        "name": "add_to_group",
        "description": "将联系人添加到分组",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "联系人ID"},
                "group_name": {"type": "string", "description": "分组名称"},
            },
            "required": ["contact_id", "group_name"],
        },
    },
    {
        "name": "remove_from_group",
        "description": "从分组中移除联系人",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "联系人ID"},
                "group_name": {"type": "string", "description": "分组名称"},
            },
            "required": ["contact_id", "group_name"],
        },
    },
    {
        "name": "list_groups",
        "description": "列出所有分组",
        "parameters": {"type": "object", "properties": {}},
    },
]


def create_contacts_executor() -> ContactsTools:
    """创建联系人工具执行器实例"""
    return ContactsTools()
