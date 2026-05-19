from __future__ import annotations

from difflib import SequenceMatcher
import re

from app.domain.entities import Article
from app.domain.enums import PreferenceMode
from app.domain.exceptions import NotFoundError
from app.domain.repositories import ArticleRepository, ScrapRepository, UserPreferenceRepository


class FeedService:
    WIDE_BLOCK_ARTICLE_LIMIT = 4
    NARROW_BLOCK_ARTICLE_TARGET = 4
    DUPLICATE_TITLE_SIMILARITY = 0.72
    MINIMUM_FEED_SCORE_WEIGHT = 0.65

    def __init__(self, article_repository: ArticleRepository, preference_repository: UserPreferenceRepository, scrap_repository: ScrapRepository):
        self.article_repository = article_repository
        self.preference_repository = preference_repository
        self.scrap_repository = scrap_repository

    def get_article(self, article_id: str) -> Article:
        article = self.article_repository.get_by_id(article_id)
        if not article:
            raise NotFoundError('Article not found')
        return article

    @staticmethod
    def _sort_articles(articles: list[Article]) -> list[Article]:
        return sorted(
            articles,
            key=lambda article: (
                article.score_weight,
                article.published_at,
                article.id,
            ),
            reverse=True,
        )

    @staticmethod
    def _normalized_title(title: str) -> str:
        return re.sub(r'[^0-9A-Za-z가-힣]+', '', title).lower()

    @classmethod
    def _is_duplicate_article(cls, candidate: Article, selected: Article) -> bool:
        if candidate.primary_category != selected.primary_category:
            return False
        if candidate.published_at != selected.published_at:
            return False

        candidate_title = cls._normalized_title(candidate.title)
        selected_title = cls._normalized_title(selected.title)
        if not candidate_title or not selected_title:
            return False
        if candidate_title == selected_title:
            return True

        similarity = SequenceMatcher(None, candidate_title, selected_title).ratio()
        return similarity >= cls.DUPLICATE_TITLE_SIMILARITY

    @classmethod
    def _dedupe_articles(cls, articles: list[Article]) -> list[Article]:
        unique: list[Article] = []
        for article in articles:
            if any(cls._is_duplicate_article(article, existing) for existing in unique):
                continue
            unique.append(article)
        return unique

    @classmethod
    def _feed_eligible_articles(cls, articles: list[Article]) -> list[Article]:
        return [article for article in articles if article.score_weight >= cls.MINIMUM_FEED_SCORE_WEIGHT]

    @staticmethod
    def _wide_weights(count: int) -> list[float]:
        if count <= 0:
            return []
        if count == 1:
            return [1.0]
        return [round(1.0 - 0.15 * idx, 2) for idx in range(count)]

    def _resolve_preference(self, user_id: str) -> tuple[PreferenceMode, list[str], list[str]]:
        preference = self.preference_repository.get(user_id)
        if not preference:
            return PreferenceMode.WIDE, ['stock', 'crypto', 'realestate', 'economy', 'tech'], []
        return preference.mode, preference.primary_categories, preference.subcategories

    @staticmethod
    def _matches_preference(
        article: Article,
        preference_mode: PreferenceMode,
        primary_categories: list[str],
        subcategories: list[str],
    ) -> bool:
        if preference_mode is PreferenceMode.NARROW:
            if not primary_categories:
                return False
            return article.primary_category == primary_categories[0] and article.subcategory in subcategories
        return article.primary_category in primary_categories

    def _filter_articles_for_user(self, user_id: str, articles: list[Article]) -> list[Article]:
        preference_mode, primary_categories, subcategories = self._resolve_preference(user_id)
        return [
            article
            for article in articles
            if self._matches_preference(article, preference_mode, primary_categories, subcategories)
        ]

    def _fill_narrow_articles(self, primary_category: str, subcategories: list[str]) -> list[Article]:
        selected = self._dedupe_articles(
            self._feed_eligible_articles(
                self._sort_articles(self.article_repository.list_by_primary_and_subcategories(primary_category, subcategories))
            )
        )
        if len(selected) >= self.NARROW_BLOCK_ARTICLE_TARGET:
            return selected[: self.NARROW_BLOCK_ARTICLE_TARGET]

        selected_ids = {article.id for article in selected}
        fallback = [
            article
            for article in self._feed_eligible_articles(self._sort_articles(self.article_repository.list_by_primary(primary_category)))
            if article.id not in selected_ids
        ]
        return self._dedupe_articles(selected + fallback)[: self.NARROW_BLOCK_ARTICLE_TARGET]

    def get_feed(self, user_id: str) -> dict:
        preference_mode, primary_categories, subcategories = self._resolve_preference(user_id)

        if preference_mode is PreferenceMode.NARROW:
            articles = self._fill_narrow_articles(primary_categories[0], subcategories)
            return {
                'user_id': user_id,
                'mode': preference_mode.value,
                'blocks': [
                    {
                        'key': f'{primary_categories[0]}-focus',
                        'title': '깊게 보기',
                        'weight': 1.0,
                        'articles': articles,
                    }
                ],
            }

        blocks = []
        weights = self._wide_weights(len(primary_categories))
        for slug, weight in zip(primary_categories, weights):
            articles = self._dedupe_articles(self._feed_eligible_articles(self._sort_articles(self.article_repository.list_by_primary(slug))))
            if not articles:
                continue
            blocks.append(
                {
                    'key': f'{slug}-block',
                    'title': f'{slug} block',
                    'weight': weight,
                    'articles': articles[: self.WIDE_BLOCK_ARTICLE_LIMIT],
                }
            )

        return {
            'user_id': user_id,
            'mode': preference_mode.value,
            'blocks': blocks,
        }

    def list_scraps(self, user_id: str) -> list[Article]:
        article_ids = self.scrap_repository.list_article_ids(user_id)
        items = []
        for article_id in article_ids:
            article = self.article_repository.get_by_id(article_id)
            if article:
                items.append(article)
        return items

    def _archive_items_for_user(self, user_id: str, articles: list[Article]) -> list[Article]:
        return self._sort_articles(self._filter_articles_for_user(user_id, articles))

    def get_archive_month(self, user_id: str, archive_month: str) -> dict:
        articles = self._archive_items_for_user(user_id, self.article_repository.list_by_month(archive_month))
        grouped: dict[str, list[Article]] = {}
        for article in articles:
            grouped.setdefault(article.published_at, []).append(article)

        return {
            'user_id': user_id,
            'month': archive_month,
            'days': [
                {
                    'date': archive_date,
                    'count': len(items),
                    'items': items,
                }
                for archive_date, items in sorted(grouped.items(), reverse=True)
            ],
        }

    def get_archive_date(self, user_id: str, archive_date: str) -> dict:
        items = self._archive_items_for_user(user_id, self.article_repository.list_by_date(archive_date))
        return {
            'user_id': user_id,
            'date': archive_date,
            'items': items,
        }

    def add_scrap(self, user_id: str, article_id: str) -> None:
        if not self.article_repository.get_by_id(article_id):
            raise NotFoundError('Article not found')
        self.scrap_repository.add(user_id, article_id)

    def remove_scrap(self, user_id: str, article_id: str) -> None:
        self.scrap_repository.remove(user_id, article_id)
