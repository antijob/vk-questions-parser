from typing import Optional
import requests
import time
import datetime
import logging
from models import Post, Comment


class VKParser:
    API_URL = "https://api.vk.com/method/"

    def __init__(self, token, max_posts=100):
        self.token = token
        self.max_posts = max_posts
        self.logger = logging.getLogger(__name__)

    def _call_api(self, method, params):
        params.update({"access_token": self.token, "v": "5.131"})
        while True:
            try:
                response = requests.get(f"{self.API_URL}{method}", params=params)
                data = response.json()
                if "error" in data:
                    if data["error"]["error_code"] in [6, 10, 28]:
                        time.sleep(1)
                        continue
                    else:
                        self.logger.error(f"Ошибка API: {data['error']}")
                        return None
                return data["response"]
            except Exception as e:
                self.logger.error(f"Ошибка запроса: {e}")
                return None

    def _format_date(self, timestamp: int) -> str:
        if not timestamp:
            return ""
        try:
            dt = datetime.datetime.utcfromtimestamp(timestamp)
            return dt.strftime("%d-%m-%Y")
        except Exception as e:
            self.logger.error(f"Ошибка преобразования даты: {e}")
            return ""

    def _convert_sex(self, sex_code: int) -> Optional[str]:
        if sex_code == 2:
            return 'M'
        elif sex_code == 1:
            return 'F'
        return None

    def get_posts(self, group_id, since_date: str = None):
        posts = []
        offset = 0
        count_per_request = 100
        since_dt = None
        if since_date:
            try:
                since_dt = datetime.datetime.strptime(since_date, "%d-%m-%Y")
            except Exception as e:
                self.logger.error(f"Некорректный формат даты для since_date: {e}")
                since_dt = None
        while len(posts) < self.max_posts:
            remaining = self.max_posts - len(posts)
            current_count = min(count_per_request, remaining)
            response = self._call_api(
                "wall.get",
                {
                    "domain": group_id,
                    "count": current_count,
                    "offset": offset,
                    "filter": "owner"
                }
            )
            if not response or "items" not in response or not response["items"]:
                break
            stop = False
            for item in response["items"]:
                post_date_str = self._format_date(item.get("date", 0))
                posts.append(Post(
                    group_id=group_id,
                    post_id=item["id"],
                    text=item["text"].encode('utf-8', errors='replace').decode('utf-8'),
                    date=post_date_str,
                    likes=item.get("likes", {}).get("count", 0)
                ))
                if since_dt:
                    try:
                        post_dt = datetime.datetime.strptime(post_date_str, "%d-%m-%Y")
                        if post_dt <= since_dt:
                            stop = True
                    except Exception as e:
                        self.logger.error(f"Ошибка сравнения дат: {e}")
            if stop:
                break
            if len(response["items"]) < current_count:
                break
            offset += current_count
            time.sleep(0.5)
        return posts[:self.max_posts]

    def get_comments(self, group_id, post_id, max_comments=100):
        numeric_group_id = self._get_numeric_group_id(group_id)
        if not numeric_group_id:
            return []
        response = self._call_api("wall.getComments", {
            "owner_id": -numeric_group_id,
            "post_id": post_id,
            "extended": 1,
            "fields": "occupation,sex,bdate",
            "count": min(100, max_comments)
        })
        profiles = {p["id"]: p for p in response.get("profiles", [])} if response else {}
        items = response["items"] if response and "items" in response else []
        if not items:
            return []
        comments = []
        for item in items:
            user = profiles.get(item.get("from_id"))
            workplace = user["occupation"].get("name") if user and isinstance(user.get("occupation"), dict) else None
            bdate = user.get("bdate") if user else None
            if bdate and len(bdate.split('.')) == 3:
                try:
                    day, month, year = bdate.split('.')
                    bdate = f"{int(day):02d}-{int(month):02d}-{year}"
                except Exception:
                    bdate = None
            else:
                bdate = None
            sex = self._convert_sex(user.get("sex")) if user else None
            comment_id = item.get("id")
            likes = self.get_comment_likes(-numeric_group_id, comment_id) if comment_id else 0
            comments.append(Comment(
                group_id=group_id,
                post_id=post_id,
                comment_id=comment_id,
                text=item.get("text", "").encode('utf-8', errors='replace').decode('utf-8'),
                user_name=f"{user.get('first_name', '')} {user.get('last_name', '')}" if user else "Неизвестно",
                workplace=workplace,
                date=self._format_date(item.get("date", 0)),
                sex=sex,
                bdate=bdate,
                likes=likes
            ))
        return comments

    def _get_numeric_group_id(self, group_id):
        response = self._call_api("groups.getById", {"group_id": group_id})
        if response and response[0].get("id"):
            return response[0]["id"]
        return None

    def get_comment_likes(self, owner_id, comment_id):
        """Получить количество лайков для комментария через likes.getList"""
        response = self._call_api("likes.getList", {
            "type": "comment",
            "owner_id": owner_id,
            "item_id": comment_id
        })
        if response and "count" in response:
            return response["count"]
        return 0
