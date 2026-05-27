from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.application.services.feed_service import FeedService
from app.domain.entities import Article, DailyFeedSnapshot, DailyFeedSnapshotItem
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.repositories import DailyFeedSnapshotRepository, UserArticleReadRepository, UserPreferenceRepository


class DailyFeedSnapshotService:
    def __init__(
        self,
        feed_service: FeedService,
        preference_repository: UserPreferenceRepository,
        snapshot_repository: DailyFeedSnapshotRepository,
        read_repository: UserArticleReadRepository,
        clock: Callable[[], datetime] | None = None,
    ):
        self.feed_service = feed_service
        self.preference_repository = preference_repository
        self.snapshot_repository = snapshot_repository
        self.read_repository = read_repository
        self.clock = clock or (lambda: datetime.now(UTC))

    def generate_for_user_date(
        self,
        user_id: str,
        feed_date: str,
        generation_source: str | None = None,
        force: bool = False,
    ) -> DailyFeedSnapshot:
        existing = self.snapshot_repository.get_by_user_date(user_id, feed_date)
        if (
            existing is not None
            and existing.first_viewed_at is not None
            and existing.items
            and not force
            and self._snapshot_items_match_feed_date(existing, feed_date)
        ):
            return existing

        preference = self.preference_repository.get(user_id)
        if preference is None:
            raise NotFoundError('User preference not found')
        if not preference.onboarding_completed:
            raise ValidationError('User onboarding is not completed')

        blocks = self.feed_service.build_feed_blocks_for_preference(
            preference.mode,
            preference.primary_categories,
            preference.subcategories,
            published_date=feed_date,
        )
        items = self._snapshot_items_from_blocks(blocks)
        snapshot = DailyFeedSnapshot(
            id=existing.id if existing else None,
            user_id=user_id,
            feed_date=feed_date,
            status='generated',
            generated_at=self.clock(),
            preference_mode=preference.mode,
            primary_categories=list(preference.primary_categories),
            subcategories=list(preference.subcategories),
            generation_source=generation_source,
            items=items,
        )
        return self.snapshot_repository.save(snapshot)

    def _snapshot_items_match_feed_date(self, snapshot: DailyFeedSnapshot, feed_date: str) -> bool:
        for item in snapshot.items:
            try:
                article = self.feed_service.get_article(item.article_id)
            except NotFoundError:
                return False
            if article.published_at != feed_date:
                return False
        return True

    @staticmethod
    def _snapshot_items_from_blocks(blocks: list[dict]) -> list[DailyFeedSnapshotItem]:
        items: list[DailyFeedSnapshotItem] = []
        sort_order = 1
        for block in blocks:
            block_key = str(block.get('key', ''))
            block_title = str(block.get('title', ''))
            for article in block.get('articles', []):
                if not isinstance(article, Article):
                    continue
                items.append(
                    DailyFeedSnapshotItem(
                        article_id=article.id,
                        block_key=block_key,
                        block_title=block_title,
                        sort_order=sort_order,
                        score_weight=article.score_weight,
                    )
                )
                sort_order += 1
        return items

    def list_by_user_month(self, user_id: str, month: str) -> list[DailyFeedSnapshot]:
        return self.snapshot_repository.list_by_user_month(user_id, month)

    def get_by_user_date(self, user_id: str, feed_date: str) -> DailyFeedSnapshot | None:
        return self.snapshot_repository.get_by_user_date(user_id, feed_date)

    def mark_viewed(self, snapshot_id: int, viewed_at: datetime | None = None) -> DailyFeedSnapshot:
        return self.snapshot_repository.mark_viewed(snapshot_id, viewed_at or self.clock())

    def list_read_article_ids(self, user_id: str, snapshot_id: int) -> set[str]:
        return self.read_repository.list_read_article_ids(user_id, snapshot_id)

    def mark_article_read(
        self,
        user_id: str,
        article_id: str,
        snapshot_id: int | None,
        read_at: datetime | None = None,
        read_source: str | None = None,
    ) -> None:
        effective_read_at = read_at or self.clock()
        self.read_repository.mark_read(user_id, article_id, snapshot_id, effective_read_at, read_source)
        if snapshot_id is None:
            return

        snapshot = self.snapshot_repository.get_by_id(snapshot_id)
        if snapshot is None or snapshot.user_id != user_id or snapshot.completed_at is not None:
            return
        snapshot_article_ids = {item.article_id for item in snapshot.items}
        if article_id not in snapshot_article_ids:
            return
        read_article_ids = self.read_repository.list_read_article_ids(user_id, snapshot_id)
        if snapshot_article_ids and snapshot_article_ids <= read_article_ids:
            snapshot.status = 'completed'
            snapshot.completed_at = effective_read_at
            self.snapshot_repository.save(snapshot)
