"""
短信/消息任务主体 (SMS/Messaging Task Subject)

提供手机短信管理功能，包括发送、接收、查看、删除短信等操作。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class Message:
    """短信数据结构"""
    id: str
    sender: str
    receiver: str
    content: str
    timestamp: datetime
    is_read: bool = False
    direction: str = "received"  # "sent" or "received"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "is_read": self.is_read,
            "direction": self.direction
        }


@dataclass
class SMSState:
    """短信状态"""
    messages: Dict[str, Message] = field(default_factory=dict)
    conversations: Dict[str, List[str]] = field(default_factory=dict)  # phone_number -> [message_ids]
    _next_id: int = 1
    
    def get_message_count(self) -> int:
        return len(self.messages)
    
    def get_conversation_count(self) -> int:
        return len(self.conversations)


class SMSTools:
    """短信工具集"""
    
    def __init__(self):
        self.state = SMSState()
    
    def _generate_id(self) -> str:
        msg_id = f"sms_{self.state._next_id}"
        self.state._next_id += 1
        return msg_id
    
    def list_messages(self, phone_number: Optional[str] = None, 
                     unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出短信
        
        Args:
            phone_number: 可选的电话号码过滤
            unread_only: 是否只显示未读消息
            limit: 最大返回数量
            
        Returns:
            短信列表
        """
        results = []
        
        # 获取相关消息 ID
        if phone_number:
            conversation_ids = self.state.conversations.get(phone_number, [])
            messages = [self.state.messages[mid] for mid in conversation_ids if mid in self.state.messages]
        else:
            messages = list(self.state.messages.values())
        
        # 按时间排序（最新的在前）
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        
        for msg in messages:
            if unread_only and msg.is_read:
                continue
            
            results.append(msg.to_dict())
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单条短信详情
        
        Args:
            message_id: 短信 ID
            
        Returns:
            短信详情，如果不存在则返回 None
        """
        msg = self.state.messages.get(message_id)
        if msg:
            # 自动标记为已读
            msg.is_read = True
            return msg.to_dict()
        return None
    
    def send_message(self, receiver: str, content: str) -> Dict[str, Any]:
        """
        发送短信
        
        Args:
            receiver: 接收者电话号码
            content: 短信内容
            
        Returns:
            发送的短信信息
        """
        if not receiver or not receiver.strip():
            raise ValueError("接收者电话号码不能为空")
        if not content or not content.strip():
            raise ValueError("短信内容不能为空")
        
        msg_id = self._generate_id()
        now = datetime.now()
        
        msg = Message(
            id=msg_id,
            sender="me",  # 假设当前用户是"me"
            receiver=receiver.strip(),
            content=content.strip(),
            timestamp=now,
            is_read=True,  # 自己发送的消息默认为已读
            direction="sent"
        )
        
        self.state.messages[msg_id] = msg
        
        # 添加到会话
        if receiver not in self.state.conversations:
            self.state.conversations[receiver] = []
        self.state.conversations[receiver].append(msg_id)
        
        return msg.to_dict()
    
    def receive_message(self, sender: str, content: str) -> Dict[str, Any]:
        """
        接收短信（模拟收到消息）
        
        Args:
            sender: 发送者电话号码
            content: 短信内容
            
        Returns:
            接收的短信信息
        """
        if not sender or not sender.strip():
            raise ValueError("发送者电话号码不能为空")
        if not content or not content.strip():
            raise ValueError("短信内容不能为空")
        
        msg_id = self._generate_id()
        now = datetime.now()
        
        msg = Message(
            id=msg_id,
            sender=sender.strip(),
            receiver="me",  # 假设当前用户是"me"
            content=content.strip(),
            timestamp=now,
            is_read=False,  # 收到的消息默认为未读
            direction="received"
        )
        
        self.state.messages[msg_id] = msg
        
        # 添加到会话
        if sender not in self.state.conversations:
            self.state.conversations[sender] = []
        self.state.conversations[sender].append(msg_id)
        
        return msg.to_dict()
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        标记短信为已读
        
        Args:
            message_id: 短信 ID
            
        Returns:
            更新后的短信信息
            
        Raises:
            ValueError: 如果短信不存在
        """
        if message_id not in self.state.messages:
            raise ValueError(f"短信 {message_id} 不存在")
        
        msg = self.state.messages[message_id]
        msg.is_read = True
        
        return msg.to_dict()
    
    def mark_all_as_read(self, phone_number: Optional[str] = None) -> int:
        """
        批量标记短信为已读
        
        Args:
            phone_number: 可选的电话号码，如果指定则只标记该联系人的消息
            
        Returns:
            标记为已读的消息数量
        """
        count = 0
        
        if phone_number:
            conversation_ids = self.state.conversations.get(phone_number, [])
            for mid in conversation_ids:
                if mid in self.state.messages:
                    msg = self.state.messages[mid]
                    if not msg.is_read:
                        msg.is_read = True
                        count += 1
        else:
            for msg in self.state.messages.values():
                if not msg.is_read:
                    msg.is_read = True
                    count += 1
        
        return count
    
    def delete_message(self, message_id: str) -> bool:
        """
        删除短信
        
        Args:
            message_id: 短信 ID
            
        Returns:
            是否删除成功
            
        Raises:
            ValueError: 如果短信不存在
        """
        if message_id not in self.state.messages:
            raise ValueError(f"短信 {message_id} 不存在")
        
        msg = self.state.messages[message_id]
        
        # 从会话中移除
        phone_number = msg.sender if msg.direction == "received" else msg.receiver
        if phone_number in self.state.conversations:
            if message_id in self.state.conversations[phone_number]:
                self.state.conversations[phone_number].remove(message_id)
        
        del self.state.messages[message_id]
        return True
    
    def delete_conversation(self, phone_number: str) -> int:
        """
        删除整个会话
        
        Args:
            phone_number: 电话号码
            
        Returns:
            删除的消息数量
            
        Raises:
            ValueError: 如果会话不存在
        """
        if phone_number not in self.state.conversations:
            raise ValueError(f"与 {phone_number} 的会话不存在")
        
        message_ids = self.state.conversations[phone_number]
        count = 0
        
        for mid in message_ids:
            if mid in self.state.messages:
                del self.state.messages[mid]
                count += 1
        
        del self.state.conversations[phone_number]
        return count
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        列出所有会话
        
        Returns:
            会话列表，包含最新消息和时间
        """
        results = []
        
        for phone_number, message_ids in self.state.conversations.items():
            if not message_ids:
                continue
            
            # 获取最新消息
            messages = [self.state.messages[mid] for mid in message_ids if mid in self.state.messages]
            if not messages:
                continue
            
            messages.sort(key=lambda m: m.timestamp, reverse=True)
            latest_msg = messages[0]
            
            # 统计未读数量
            unread_count = sum(1 for m in messages if not m.is_read)
            
            results.append({
                "phone_number": phone_number,
                "latest_message": latest_msg.to_dict(),
                "unread_count": unread_count,
                "total_count": len(messages)
            })
        
        # 按最新时间排序
        results.sort(key=lambda c: c["latest_message"]["timestamp"], reverse=True)
        
        return results
    
    def get_unread_count(self, phone_number: Optional[str] = None) -> int:
        """
        获取未读消息数量
        
        Args:
            phone_number: 可选的电话号码，如果指定则只统计该联系人的未读数
            
        Returns:
            未读消息数量
        """
        if phone_number:
            conversation_ids = self.state.conversations.get(phone_number, [])
            return sum(1 for mid in conversation_ids 
                      if mid in self.state.messages and not self.state.messages[mid].is_read)
        else:
            return sum(1 for msg in self.state.messages.values() if not msg.is_read)


# 定义工具描述（用于注册到 ToolExecutor）
SMS_TOOLS = [
    {
        "name": "list_messages",
        "description": "列出短信，支持按电话号码过滤和只显示未读",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "电话号码"},
                "unread_only": {"type": "boolean", "description": "是否只显示未读消息"},
                "limit": {"type": "integer", "description": "最大返回数量", "default": 50}
            }
        }
    },
    {
        "name": "get_message",
        "description": "获取单条短信详情（会自动标记为已读）",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "短信 ID"}
            },
            "required": ["message_id"]
        }
    },
    {
        "name": "send_message",
        "description": "发送短信",
        "parameters": {
            "type": "object",
            "properties": {
                "receiver": {"type": "string", "description": "接收者电话号码"},
                "content": {"type": "string", "description": "短信内容"}
            },
            "required": ["receiver", "content"]
        }
    },
    {
        "name": "receive_message",
        "description": "接收短信（模拟收到消息）",
        "parameters": {
            "type": "object",
            "properties": {
                "sender": {"type": "string", "description": "发送者电话号码"},
                "content": {"type": "string", "description": "短信内容"}
            },
            "required": ["sender", "content"]
        }
    },
    {
        "name": "mark_as_read",
        "description": "标记短信为已读",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "短信 ID"}
            },
            "required": ["message_id"]
        }
    },
    {
        "name": "mark_all_as_read",
        "description": "批量标记短信为已读",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "可选的电话号码"}
            }
        }
    },
    {
        "name": "delete_message",
        "description": "删除短信",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "短信 ID"}
            },
            "required": ["message_id"]
        }
    },
    {
        "name": "delete_conversation",
        "description": "删除整个会话",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "电话号码"}
            },
            "required": ["phone_number"]
        }
    },
    {
        "name": "list_conversations",
        "description": "列出所有会话",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_unread_count",
        "description": "获取未读消息数量",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "可选的电话号码"}
            }
        }
    }
]


def create_sms_executor() -> SMSTools:
    """创建短信工具执行器实例"""
    return SMSTools()
