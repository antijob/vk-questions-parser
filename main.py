import os
import argparse
import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from vk_api import VKParser
from utils import save_to_csv
from config import GROUPS
from predictor import QuestionPredictor

load_dotenv()


def parse_arguments():
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Парсер постов и комментариев из групп VK')

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--deep',
        type=int,
        default=100,
        help='Глубина сбора постов и комментариев (по умолчанию: 100)'
    )

    group.add_argument(
        '--date',
        type=str,
        help='Дата, до которой собирать посты и комментарии (формат: ДД-ММ-ГГГГ)'
    )

    parser.add_argument(
        '--predict',
        action='store_true',
        help='Включить фильтрацию постов через модель определения вопросов'
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if not GROUPS:
        raise ValueError("Список групп не задан в .env (VK_GROUPS)")

    os.makedirs("output", exist_ok=True)

    # Преобразуем дату, если она указана
    until_date = None
    if args.date:
        try:
            day, month, year = args.date.split('-')
            until_date = datetime.datetime(int(year), int(month), int(day))
        except ValueError:
            raise ValueError("Неверный формат даты. Используйте ДД-ММ-ГГГГ")

    # Инициализируем парсер с указанной глубиной или датой
    # Если указана дата, увеличиваем лимит
    max_posts = args.deep if not until_date else 1000
    vk_parser = VKParser(os.getenv("VK_TOKEN"),
                         max_posts=max_posts, until_date=until_date)

    # Сбор постов
    posts = []
    for group in tqdm(GROUPS, desc="Парсинг групп"):
        posts.extend(vk_parser.get_posts(group))

    # Если включена фильтрация по вопросам
    if args.predict:
        questions = []
        predictor = QuestionPredictor()
        for post in tqdm(posts, desc="Предсказание вопросов"):
            if predictor.predict(post.text):
                questions.append(post)
        posts_to_process = questions
        output_file = "output/questions.csv"
    else:
        posts_to_process = posts
        output_file = "output/posts.csv"

    save_to_csv(posts_to_process, output_file)

    # Сбор комментариев
    comments = []
    # Если указана дата, увеличиваем лимит
    max_comments = args.deep if not until_date else 1000
    for post in tqdm(posts_to_process, desc="Парсинг комментариев"):
        comments.extend(vk_parser.get_comments(
            post.group_id, post.post_id, max_comments=max_comments))
    save_to_csv(comments, "output/comments.csv")


if __name__ == "__main__":
    main()
