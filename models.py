from dataclasses import dataclass


@dataclass
class Post:
    group_id: str
    post_id: int
    text: str


@dataclass
class Comment:
    group_id: str
    post_id: int
    text: str
    user_name: str
    city: str = None
    workplace: str = None
