from dataclasses import dataclass
from typing import Optional


@dataclass
class Post:
    group_id: str
    post_id: int
    text: str
    date: str
    likes: int = 0


@dataclass
class Comment:
    group_id: str
    post_id: int
    text: str
    user_name: str
    date: str
    city: str = None
    workplace: str = None
    sex: Optional[str] = None  # 'M', 'F' или None
    bdate: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    likes: int = 0
