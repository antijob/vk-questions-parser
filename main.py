import os
from dotenv import load_dotenv
from tqdm import tqdm
from vk_api import VKParser
from utils import save_to_csv
from config import GROUPS
from predictor import QuestionPredictor

load_dotenv()


def main():
    if not GROUPS:
        raise ValueError("Список групп не задан в .env (VK_GROUPS)")

    os.makedirs("output", exist_ok=True)

    vk_parser = VKParser(os.getenv("VK_TOKEN"))

    # Сбор постов
    posts = []
    for group in tqdm(GROUPS, desc="Парсинг групп"):
        posts.extend(vk_parser.get_posts(group))

    questions = []
    # Предсказание вопросов
    predictor = QuestionPredictor()
    for post in tqdm(posts, desc="Предсказание вопросов"):
        if predictor.predict(post.text):
            questions.append(post)

    save_to_csv(questions, "output/questions.csv")

    # Сбор комментариев
    comments = []
    for question in tqdm(questions, desc="Парсинг комментариев"):
        comments.extend(vk_parser.get_comments(
            question.group_id, question.post_id))
    save_to_csv(comments, "output/comments.csv")


if __name__ == "__main__":
    main()
