"""
系统设置任务主体 - 模拟手机系统设置
包含：WiFi, 蓝牙，音量，亮度，飞行模式，勿扰模式等
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentsim import ToolCall, ToolDefine, ToolExecutor, ToolRiskLevel


@dataclass
class SystemSettingsState:
    """系统设置隐藏状态"""

    wifi_enabled: bool = True
    wifi_ssid: Optional[str] = "HomeWiFi"
    bluetooth_enabled: bool = False
    brightness: int = 50
    media_volume: int = 70
    ring_volume: int = 80
    alarm_volume: int = 60
    airplane_mode: bool = False
    do_not_disturb: bool = False
    battery_saver: bool = False
    location_enabled: bool = True
    auto_rotate: bool = True
    dark_mode: bool = False
    available_wifi_networks: List[Dict[str, Any]] = field(
        default_factory=lambda: [
            {"ssid": "HomeWiFi", "security": "WPA2", "signal": 90},
            {"ssid": "OfficeWiFi", "security": "WPA2", "signal": 75},
            {"ssid": "GuestNetwork", "security": "Open", "signal": 60},
            {"ssid": "CoffeeShop", "security": "WPA2", "signal": 45},
        ]
    )
    paired_bluetooth_devices: List[Dict[str, Any]] = field(
        default_factory=lambda: [
            {"name": "AirPods Pro", "type": "audio", "connected": False},
            {"name": "Car Audio", "type": "audio", "connected": False},
            {"name": "Smart Watch", "type": "wearable", "connected": False},
        ]
    )


def register_system_settings_tools(executor: ToolExecutor):
    """注册所有系统设置工具"""

    def toggle_wifi(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        if state.airplane_mode and enabled:
            return {"success": False, "error": "无法在飞行模式下开启 WiFi"}
        state.wifi_enabled = enabled
        if not enabled:
            state.wifi_ssid = None
        return {"wifi_enabled": enabled}

    executor.register_tool(
        name="toggle_wifi",
        func=toggle_wifi,
        definition=ToolDefine(
            name="toggle_wifi",
            description="打开或关闭 WiFi",
            parameters={
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "true 为打开，false 为关闭"}
                },
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def list_wifi_networks(state: SystemSettingsState) -> Dict[str, Any]:
        if not state.wifi_enabled:
            return {"success": False, "error": "WiFi 已关闭"}
        return {"networks": state.available_wifi_networks}

    executor.register_tool(
        name="list_wifi_networks",
        func=list_wifi_networks,
        definition=ToolDefine(
            name="list_wifi_networks",
            description="列出可用的 WiFi 网络",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def connect_wifi(
        state: SystemSettingsState, ssid: str, password: Optional[str] = None
    ) -> Dict[str, Any]:
        if not state.wifi_enabled:
            return {"success": False, "error": "WiFi 已关闭"}
        network = next((n for n in state.available_wifi_networks if n["ssid"] == ssid), None)
        if not network:
            return {"success": False, "error": f"未找到网络：{ssid}"}
        if network["security"] != "Open" and not password:
            return {"success": False, "error": "需要密码"}
        state.wifi_ssid = ssid
        return {"connected_to": ssid}

    executor.register_tool(
        name="connect_wifi",
        func=connect_wifi,
        definition=ToolDefine(
            name="connect_wifi",
            description="连接到指定的 WiFi 网络",
            parameters={
                "type": "object",
                "properties": {"ssid": {"type": "string"}, "password": {"type": "string"}},
                "required": ["ssid"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_bluetooth(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        if state.airplane_mode and enabled:
            return {"success": False, "error": "无法在飞行模式下开启蓝牙"}
        state.bluetooth_enabled = enabled
        if not enabled:
            for device in state.paired_bluetooth_devices:
                device["connected"] = False
        return {"bluetooth_enabled": enabled}

    executor.register_tool(
        name="toggle_bluetooth",
        func=toggle_bluetooth,
        definition=ToolDefine(
            name="toggle_bluetooth",
            description="打开或关闭蓝牙",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def list_bluetooth_devices(state: SystemSettingsState) -> Dict[str, Any]:
        if not state.bluetooth_enabled:
            return {"success": False, "error": "蓝牙已关闭"}
        return {"devices": state.paired_bluetooth_devices}

    executor.register_tool(
        name="list_bluetooth_devices",
        func=list_bluetooth_devices,
        definition=ToolDefine(
            name="list_bluetooth_devices",
            description="列出已配对的蓝牙设备",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def connect_bluetooth(state: SystemSettingsState, device_name: str) -> Dict[str, Any]:
        if not state.bluetooth_enabled:
            return {"success": False, "error": "蓝牙已关闭"}
        device = next((d for d in state.paired_bluetooth_devices if d["name"] == device_name), None)
        if not device:
            return {"success": False, "error": f"未找到设备：{device_name}"}
        for d in state.paired_bluetooth_devices:
            d["connected"] = False
        device["connected"] = True
        return {"connected_to": device_name}

    executor.register_tool(
        name="connect_bluetooth",
        func=connect_bluetooth,
        definition=ToolDefine(
            name="connect_bluetooth",
            description="连接到指定的蓝牙设备",
            parameters={
                "type": "object",
                "properties": {"device_name": {"type": "string"}},
                "required": ["device_name"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def set_volume(state: SystemSettingsState, volume_type: str, level: int) -> Dict[str, Any]:
        if volume_type == "media":
            state.media_volume = level
        elif volume_type == "ring":
            state.ring_volume = level
        elif volume_type == "alarm":
            state.alarm_volume = level
        else:
            return {"success": False, "error": f"未知的音量类型：{volume_type}"}
        return {"volume_type": volume_type, "level": level}

    executor.register_tool(
        name="set_volume",
        func=set_volume,
        definition=ToolDefine(
            name="set_volume",
            description="设置指定类型的音量",
            parameters={
                "type": "object",
                "properties": {
                    "volume_type": {"type": "string", "enum": ["media", "ring", "alarm"]},
                    "level": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["volume_type", "level"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_volume(state: SystemSettingsState) -> Dict[str, Any]:
        return {
            "media_volume": state.media_volume,
            "ring_volume": state.ring_volume,
            "alarm_volume": state.alarm_volume,
        }

    executor.register_tool(
        name="get_volume",
        func=get_volume,
        definition=ToolDefine(
            name="get_volume",
            description="获取当前音量设置",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def set_brightness(state: SystemSettingsState, level: int) -> Dict[str, Any]:
        state.brightness = level
        return {"brightness": level}

    executor.register_tool(
        name="set_brightness",
        func=set_brightness,
        definition=ToolDefine(
            name="set_brightness",
            description="设置屏幕亮度",
            parameters={
                "type": "object",
                "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 100}},
                "required": ["level"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_airplane_mode(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.airplane_mode = enabled
        if enabled:
            state.wifi_enabled = False
            state.wifi_ssid = None
            state.bluetooth_enabled = False
            for device in state.paired_bluetooth_devices:
                device["connected"] = False
        return {"airplane_mode": enabled}

    executor.register_tool(
        name="toggle_airplane_mode",
        func=toggle_airplane_mode,
        definition=ToolDefine(
            name="toggle_airplane_mode",
            description="打开或关闭飞行模式",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.RISKY,
        ),
    )

    def toggle_do_not_disturb(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.do_not_disturb = enabled
        return {"do_not_disturb": enabled}

    executor.register_tool(
        name="toggle_do_not_disturb",
        func=toggle_do_not_disturb,
        definition=ToolDefine(
            name="toggle_do_not_disturb",
            description="打开或关闭勿扰模式",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_battery_saver(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.battery_saver = enabled
        if enabled:
            state.brightness = min(state.brightness, 30)
        return {"battery_saver": enabled}

    executor.register_tool(
        name="toggle_battery_saver",
        func=toggle_battery_saver,
        definition=ToolDefine(
            name="toggle_battery_saver",
            description="打开或关闭省电模式",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_location(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.location_enabled = enabled
        return {"location_enabled": enabled}

    executor.register_tool(
        name="toggle_location",
        func=toggle_location,
        definition=ToolDefine(
            name="toggle_location",
            description="打开或关闭位置服务",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.RISKY,
        ),
    )

    def toggle_auto_rotate(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.auto_rotate = enabled
        return {"auto_rotate": enabled}

    executor.register_tool(
        name="toggle_auto_rotate",
        func=toggle_auto_rotate,
        definition=ToolDefine(
            name="toggle_auto_rotate",
            description="打开或关闭自动旋转",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_dark_mode(state: SystemSettingsState, enabled: bool) -> Dict[str, Any]:
        state.dark_mode = enabled
        return {"dark_mode": enabled}

    executor.register_tool(
        name="toggle_dark_mode",
        func=toggle_dark_mode,
        definition=ToolDefine(
            name="toggle_dark_mode",
            description="打开或关闭深色模式",
            parameters={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_all_settings(state: SystemSettingsState) -> Dict[str, Any]:
        return {
            "wifi_enabled": state.wifi_enabled,
            "wifi_ssid": state.wifi_ssid,
            "bluetooth_enabled": state.bluetooth_enabled,
            "brightness": state.brightness,
            "media_volume": state.media_volume,
            "ring_volume": state.ring_volume,
            "alarm_volume": state.alarm_volume,
            "airplane_mode": state.airplane_mode,
            "do_not_disturb": state.do_not_disturb,
            "battery_saver": state.battery_saver,
            "location_enabled": state.location_enabled,
            "auto_rotate": state.auto_rotate,
            "dark_mode": state.dark_mode,
        }

    executor.register_tool(
        name="get_all_settings",
        func=get_all_settings,
        definition=ToolDefine(
            name="get_all_settings",
            description="获取所有系统设置的当前状态",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )


def create_system_settings_executor() -> ToolExecutor:
    """创建系统设置工具执行器"""
    executor = ToolExecutor()
    register_system_settings_tools(executor)
    return executor


if __name__ == "__main__":
    executor = create_system_settings_executor()
    state = SystemSettingsState()

    print("=== 系统设置工具测试 ===\n")

    result = executor.execute(state, ToolCall(tool_name="get_all_settings", arguments={}))
    print(f"1. 获取所有设置：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_wifi", arguments={"enabled": False})
    )
    print(f"2. 关闭 WiFi: success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="set_brightness", arguments={"level": 80}))
    print(f"3. 设置亮度到 80: success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="set_volume", arguments={"volume_type": "media", "level": 50})
    )
    print(f"4. 设置媒体音量为 50: success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_airplane_mode", arguments={"enabled": True})
    )
    print(f"5. 开启飞行模式：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="toggle_wifi", arguments={"enabled": True}))
    print(f"6. 飞行模式下尝试开启 WiFi: success={result.success}, error={result.error}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_airplane_mode", arguments={"enabled": False})
    )
    print(f"7. 关闭飞行模式：success={result.success}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_bluetooth", arguments={"enabled": True})
    )
    print(f"8. 开启蓝牙：success={result.success}\n")

    result = executor.execute(
        state, ToolCall(tool_name="connect_bluetooth", arguments={"device_name": "AirPods Pro"})
    )
    print(f"9. 连接 AirPods Pro: success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_dark_mode", arguments={"enabled": True})
    )
    print(f"10. 开启深色模式：success={result.success}, result={result.result}\n")

    print("=== 所有测试完成 ===")
