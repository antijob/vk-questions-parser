from functools import lru_cache
from typing import Optional, Dict, Any, Union
from transformers import pipeline, Pipeline
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionPredictor:
    """Класс для определения, является ли текст вопросом, с использованием моделей Hugging Face."""

    # Кэш для хранения загруженных моделей
    _model_cache = {}

    def __init__(
        self,
        model_name: str = "Vldln/bert-question-detector-russian",
        threshold: float = 0.8,
        use_cache: bool = True
    ):
        """
        Инициализирует предиктор с указанной моделью и пороговым значением.

        Args:
            model_name: Название модели в Hugging Face Hub или путь к локальной модели
            threshold: Пороговое значение уверенности для определения вопроса (от 0 до 1)
            use_cache: Использовать ли кэширование модели
        """
        self.model_name = model_name
        self.threshold = threshold
        self.use_cache = use_cache
        self.classifier = self._get_cached_pipeline()

    def _get_cached_pipeline(self) -> Pipeline:
        """Получает модель из кэша или загружает новую."""
        if not self.use_cache or self.model_name not in self._model_cache:
            self._model_cache[self.model_name] = self._load_pipeline()
        return self._model_cache[self.model_name]

    def _truncate_text(self, text: str, max_length: int = 500) -> str:
        """
        Обрезает текст до максимального количества токенов.

        Args:
            text: Входной текст
            max_length: Максимальное количество токенов (оставляем запас от 512)

        Returns:
            str: Обрезанный текст
        """
        if not text:
            return ""

        # Если текст короче максимальной длины, возвращаем как есть
        if len(text) <= max_length:
            return text

        # Находим последний пробел до максимальной длины, чтобы не обрезать слова
        truncated = text[:max_length]
        if ' ' in text[max_length:max_length + 10]:  # Смотрим немного вперед
            # Обрезаем до последнего пробела
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]

        return truncated.strip()

    def predict(self, text: str) -> bool:
        """
        Предсказывает, является ли текст вопросом.

        Args:
            text: Текст для анализа

        Returns:
            bool: True, если текст является вопросом с уверенностью выше порога
        """
        if not text or not text.strip():
            return False

        try:
            # Обрезаем текст до разумной длины перед передачей в модель
            truncated_text = self._truncate_text(text)
            result = self.classifier(truncated_text)

            if not result or not isinstance(result, list) or not result[0]:
                return False

            prediction = result[0]
            is_question = prediction.get("label") == "question" and prediction.get(
                "score", 0) > self.threshold

            # Логируем только если это вопрос или есть ошибки
            if is_question or not is_question and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Текст: {truncated_text[:100]}...")
                logger.debug(f"Результат: {prediction}")

            return is_question

        except Exception as e:
            logger.error(f"Ошибка при предсказании: {e}")
            # В случае ошибки пробуем предсказать по первым 100 символам
            if len(text) > 100:
                logger.info("Попытка предсказания по первым 100 символам...")
                return self.predict(text[:100])
            return False

    def _load_pipeline(self) -> Pipeline:
        """Загружает pipeline для классификации текста."""
        models_to_try = [
            self.model_name,
            "./question-detector-russian",
            "DeepPavlov/rubert-base-cased"
        ]

        for model in models_to_try:
            try:
                logger.info(f"Попытка загрузки модели: {model}")
                return pipeline("text-classification", model=model)
            except Exception as e:
                logger.warning(f"Не удалось загрузить модель {model}: {e}")
                continue

        raise RuntimeError("Не удалось загрузить ни одну из доступных моделей")

    def set_threshold(self, threshold: float) -> None:
        """Устанавливает новое пороговое значение."""
        if 0 <= threshold <= 1:
            self.threshold = threshold
        else:
            raise ValueError(
                "Пороговое значение должно быть в диапазоне от 0 до 1")


if __name__ == "__main__":
    # Пример использования
    predictor = QuestionPredictor()
    test_texts = [
        "Как дела?",
        "Привет, как твои дела?",
        "Это утверждение.",
        ""
    ]

    for text in test_texts:
        result = predictor.predict(text)
        print(f"'{text}' -> {'Вопрос' if result else 'Не вопрос'}")

    # Тестирование изменения порога
    print("\nТестирование с порогом 0.9:")
    predictor.set_threshold(0.9)
    for text in test_texts:
        if text:  # Пропускаем пустые строки
            result = predictor.predict(text)
            print(f"'{text}' -> {'Вопрос' if result else 'Не вопрос'}")
