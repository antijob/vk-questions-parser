import requests
import time
import logging
from models import Post, Comment  # Добавлен импорт классов Post и Comment


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
                response = requests.get(
                    f"{self.API_URL}{method}", params=params)
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

    def get_posts(self, group_id):
        posts = []
        offset = 0
        count_per_request = 100  # Максимальное количество постов за один запрос

        while len(posts) < self.max_posts:
            # Вычисляем сколько постов осталось запросить
            remaining = self.max_posts - len(posts)
            current_count = min(count_per_request, remaining)

            response = self._call_api(
                "wall.get",
                {
                    "domain": group_id,
                    "count": current_count,
                    "offset": offset,
                    "filter": "owner"  # Получаем только посты владельца стены
                }
            )

            if not response or "items" not in response or not response["items"]:
                break  # Больше постов нет

            for item in response["items"]:
                posts.append(Post(
                    group_id=group_id,
                    post_id=item["id"],
                    text=item["text"],
                    date=item.get("date", 0)
                ))

            # Если получено меньше постов, чем запрошено, значит это последняя страница
            if len(response["items"]) < current_count:
                break

            offset += current_count

            # Небольшая задержка, чтобы не превысить лимиты API
            time.sleep(0.5)

        return posts[:self.max_posts]  # На всякий случай обрезаем по лимиту

    def get_comments(self, group_id, post_id, max_comments=100):
        numeric_group_id = self._get_numeric_group_id(group_id)
        if not numeric_group_id:
            return []

        # Запрашиваем дополнительные поля: город и место работы (occupation)
        response = self._call_api("wall.getComments", {
            "owner_id": -numeric_group_id,
            "post_id": post_id,
            "extended": 1,
            "fields": "city,occupation",  # Добавлено явное указание полей
            # Ограничиваем количество комментариев
            "count": min(100, max_comments)
        })

        comments = []
        if response and "items" in response:
            profiles = {p["id"]: p for p in response.get("profiles", [])}
            for item in response["items"]:
                user = profiles.get(item.get("from_id"))
                comments.append(Comment(
                    group_id=group_id,
                    post_id=post_id,
                    text=item.get("text", ""),
                    user_name=f"{user.get('first_name', '')} {user.get('last_name', '')}" if user else "Неизвестно",
                    city=user.get("city", {}).get(
                        "title", "") if user else "null",
                    workplace=user.get(
                        "occupation", "null") if user else "null",  # Исправлено
                    date=item.get("date", 0)
                ))
        return comments

    def _get_numeric_group_id(self, group_id):
        """Получает числовой ID группы по screen_name."""
        response = self._call_api("groups.getById", {"group_id": group_id})
        if response and response[0].get("id"):
            return response[0]["id"]
        return None
