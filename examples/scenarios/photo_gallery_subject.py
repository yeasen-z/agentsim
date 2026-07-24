"""
相册/媒体库任务主体 - 模拟手机相册功能
包含：照片浏览、搜索、管理、相册等功能
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agentsim.core import ToolCall, ToolDefine, ToolExecutor, ToolRiskLevel


@dataclass
class Photo:
    """照片对象"""

    id: str
    filename: str
    title: str
    description: str = ""
    taken_date: str = ""
    location: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    album_ids: List[str] = field(default_factory=list)
    is_favorite: bool = False
    width: int = 1920
    height: int = 1080
    file_size: int = 2500000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "taken_date": self.taken_date,
            "location": self.location,
            "tags": self.tags,
            "album_ids": self.album_ids,
            "is_favorite": self.is_favorite,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
        }


@dataclass
class Album:
    """相册对象"""

    id: str
    name: str
    description: str = ""
    photo_ids: List[str] = field(default_factory=list)
    created_date: str = ""
    cover_photo_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "photo_count": len(self.photo_ids),
            "created_date": self.created_date,
            "cover_photo_id": self.cover_photo_id,
        }


@dataclass
class PhotoGalleryState:
    """相册媒体库隐藏状态"""

    photos: Dict[str, Photo] = field(default_factory=dict)
    albums: Dict[str, Album] = field(default_factory=dict)
    recently_deleted: List[Photo] = field(default_factory=list)

    def __post_init__(self):
        if not self.photos:
            self._init_sample_photos()
        if not self.albums:
            self._init_sample_albums()

    def _init_sample_photos(self):
        now = datetime.now()
        sample_photos = [
            Photo(
                id="photo_1",
                filename="IMG_001.jpg",
                title="海滩日落",
                description="美丽的海滩日落景色",
                taken_date=(now.replace(month=6, day=15)).strftime("%Y-%m-%d"),
                location="三亚",
                tags=["海滩", "日落", "风景"],
            ),
            Photo(
                id="photo_2",
                filename="IMG_002.jpg",
                title="家庭聚会",
                description="春节家庭聚餐",
                taken_date=(now.replace(month=1, day=22)).strftime("%Y-%m-%d"),
                location="北京",
                tags=["家庭", "聚会"],
            ),
            Photo(
                id="photo_3",
                filename="IMG_003.jpg",
                title="登山远眺",
                description="爬山登顶",
                taken_date=(now.replace(month=9, day=8)).strftime("%Y-%m-%d"),
                location="黄山",
                tags=["登山", "风景"],
            ),
            Photo(
                id="photo_4",
                filename="IMG_004.jpg",
                title="城市夜景",
                description="繁华都市夜景",
                taken_date=(now.replace(month=11, day=3)).strftime("%Y-%m-%d"),
                location="上海",
                tags=["城市", "夜景"],
            ),
            Photo(
                id="photo_5",
                filename="IMG_005.jpg",
                title="樱花盛开",
                description="春天樱花",
                taken_date=(now.replace(month=3, day=20)).strftime("%Y-%m-%d"),
                location="武汉",
                tags=["花", "春天"],
            ),
        ]
        for photo in sample_photos:
            self.photos[photo.id] = photo

    def _init_sample_albums(self):
        self.albums["album_1"] = Album(
            id="album_1",
            name="旅行回忆",
            description="各地旅行照片",
            photo_ids=["photo_1", "photo_3", "photo_4"],
            created_date="2024-01-01",
            cover_photo_id="photo_1",
        )
        self.albums["album_2"] = Album(
            id="album_2",
            name="家庭生活",
            description="家庭相关照片",
            photo_ids=["photo_2"],
            created_date="2024-01-01",
            cover_photo_id="photo_2",
        )
        self.albums["album_3"] = Album(
            id="album_3",
            name="自然风光",
            description="自然风景照片",
            photo_ids=["photo_1", "photo_3", "photo_5"],
            created_date="2024-01-01",
            cover_photo_id="photo_3",
        )


def register_photo_gallery_tools(executor: ToolExecutor):
    """注册所有相册媒体库工具"""

    def list_photos(
        state: PhotoGalleryState, album_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        if album_id:
            if album_id not in state.albums:
                return []
            album = state.albums[album_id]
            photos = [
                state.photos[pid].to_dict() for pid in album.photo_ids if pid in state.photos
            ][:limit]
        else:
            photos = [p.to_dict() for p in state.photos.values()][:limit]
        return photos

    executor.register_tool(
        name="list_photos",
        func=list_photos,
        definition=ToolDefine(
            name="list_photos",
            description="列出照片，可按相册筛选",
            parameters={
                "type": "object",
                "properties": {
                    "album_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def search_photos(
        state: PhotoGalleryState, query: str, search_in: str = "all"
    ) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for photo in state.photos.values():
            match = False
            if search_in == "all" or search_in == "title":
                if query_lower in photo.title.lower():
                    match = True
            if search_in == "all" or search_in == "tags":
                if any(query_lower in tag.lower() for tag in photo.tags):
                    match = True
            if search_in == "all" or search_in == "location":
                if photo.location and query_lower in photo.location.lower():
                    match = True
            if search_in == "all" or search_in == "description":
                if query_lower in photo.description.lower():
                    match = True
            if match:
                results.append(photo.to_dict())
        return results

    executor.register_tool(
        name="search_photos",
        func=search_photos,
        definition=ToolDefine(
            name="search_photos",
            description="搜索照片",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "search_in": {
                        "type": "string",
                        "enum": ["all", "title", "tags", "location", "description"],
                    },
                },
                "required": ["query"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_photo_details(state: PhotoGalleryState, photo_id: str) -> Optional[Dict[str, Any]]:
        if photo_id not in state.photos:
            return None
        return state.photos[photo_id].to_dict()

    executor.register_tool(
        name="get_photo_details",
        func=get_photo_details,
        definition=ToolDefine(
            name="get_photo_details",
            description="获取照片详情",
            parameters={
                "type": "object",
                "properties": {"photo_id": {"type": "string"}},
                "required": ["photo_id"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def toggle_favorite(state: PhotoGalleryState, photo_id: str) -> Dict[str, Any]:
        if photo_id not in state.photos:
            return {"success": False, "error": "照片不存在"}
        state.photos[photo_id].is_favorite = not state.photos[photo_id].is_favorite
        return {"success": True, "is_favorite": state.photos[photo_id].is_favorite}

    executor.register_tool(
        name="toggle_favorite",
        func=toggle_favorite,
        definition=ToolDefine(
            name="toggle_favorite",
            description="切换照片收藏状态",
            parameters={
                "type": "object",
                "properties": {"photo_id": {"type": "string"}},
                "required": ["photo_id"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def add_tag(state: PhotoGalleryState, photo_id: str, tag: str) -> Dict[str, Any]:
        if photo_id not in state.photos:
            return {"success": False, "error": "照片不存在"}
        if tag not in state.photos[photo_id].tags:
            state.photos[photo_id].tags.append(tag)
        return {"success": True, "tags": state.photos[photo_id].tags}

    executor.register_tool(
        name="add_tag",
        func=add_tag,
        definition=ToolDefine(
            name="add_tag",
            description="给照片添加标签",
            parameters={
                "type": "object",
                "properties": {"photo_id": {"type": "string"}, "tag": {"type": "string"}},
                "required": ["photo_id", "tag"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def list_albums(state: PhotoGalleryState) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in state.albums.values()]

    executor.register_tool(
        name="list_albums",
        func=list_albums,
        definition=ToolDefine(
            name="list_albums",
            description="列出所有相册",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def create_album(state: PhotoGalleryState, name: str, description: str = "") -> Dict[str, Any]:
        album_id = f"album_{len(state.albums) + 1}"
        new_album = Album(
            id=album_id,
            name=name,
            description=description,
            created_date=datetime.now().strftime("%Y-%m-%d"),
        )
        state.albums[album_id] = new_album
        return {"success": True, "album": new_album.to_dict()}

    executor.register_tool(
        name="create_album",
        func=create_album,
        definition=ToolDefine(
            name="create_album",
            description="创建新相册",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
                "required": ["name"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def add_to_album(state: PhotoGalleryState, photo_id: str, album_id: str) -> Dict[str, Any]:
        if photo_id not in state.photos:
            return {"success": False, "error": "照片不存在"}
        if album_id not in state.albums:
            return {"success": False, "error": "相册不存在"}
        if photo_id not in state.albums[album_id].photo_ids:
            state.albums[album_id].photo_ids.append(photo_id)
        if photo_id not in state.photos[photo_id].album_ids:
            state.photos[photo_id].album_ids.append(album_id)
        return {"success": True}

    executor.register_tool(
        name="add_to_album",
        func=add_to_album,
        definition=ToolDefine(
            name="add_to_album",
            description="将照片添加到相册",
            parameters={
                "type": "object",
                "properties": {"photo_id": {"type": "string"}, "album_id": {"type": "string"}},
                "required": ["photo_id", "album_id"],
            },
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_favorites(state: PhotoGalleryState) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in state.photos.values() if p.is_favorite]

    executor.register_tool(
        name="get_favorites",
        func=get_favorites,
        definition=ToolDefine(
            name="get_favorites",
            description="获取收藏的照片",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )

    def get_stats(state: PhotoGalleryState) -> Dict[str, Any]:
        return {
            "total_photos": len(state.photos),
            "total_albums": len(state.albums),
            "favorites_count": sum(1 for p in state.photos.values() if p.is_favorite),
            "recently_deleted_count": len(state.recently_deleted),
        }

    executor.register_tool(
        name="get_stats",
        func=get_stats,
        definition=ToolDefine(
            name="get_stats",
            description="获取相册统计信息",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level=ToolRiskLevel.MODERATE,
        ),
    )


def create_photo_gallery_executor() -> ToolExecutor:
    executor = ToolExecutor()
    register_photo_gallery_tools(executor)
    return executor


if __name__ == "__main__":
    executor = create_photo_gallery_executor()
    state = PhotoGalleryState()

    print("=== 相册媒体库工具测试 ===\n")

    result = executor.execute(state, ToolCall(tool_name="get_stats", arguments={}))
    print(f"1. 获取统计：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="list_albums", arguments={}))
    print(f"2. 列出相册：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="list_photos", arguments={"limit": 3}))
    print(f"3. 列出照片：success={result.success}, count={len(result.result)}\n")

    result = executor.execute(
        state, ToolCall(tool_name="search_photos", arguments={"query": "风景"})
    )
    print(f"4. 搜索风景照片：success={result.success}, count={len(result.result)}\n")

    result = executor.execute(
        state, ToolCall(tool_name="get_photo_details", arguments={"photo_id": "photo_1"})
    )
    print(f"5. 获取照片详情：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="toggle_favorite", arguments={"photo_id": "photo_1"})
    )
    print(f"6. 收藏照片：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state, ToolCall(tool_name="add_tag", arguments={"photo_id": "photo_1", "tag": "美丽"})
    )
    print(f"7. 添加标签：success={result.success}, result={result.result}\n")

    result = executor.execute(
        state,
        ToolCall(
            tool_name="create_album", arguments={"name": "我的收藏", "description": "最喜欢的照片"}
        ),
    )
    print(f"8. 创建相册：success={result.success}, result={result.result}\n")

    result = executor.execute(state, ToolCall(tool_name="get_favorites", arguments={}))
    print(f"9. 获取收藏：success={result.success}, count={len(result.result)}\n")

    print("=== 所有测试完成 ===")
