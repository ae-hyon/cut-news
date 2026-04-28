from __future__ import annotations

from app.domain.entities import Category
from app.domain.exceptions import NotFoundError
from app.domain.repositories import CategoryRepository


class CatalogService:
    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository

    def list_categories(self) -> list[Category]:
        return self.category_repository.list_categories()

    def get_category(self, slug: str) -> Category:
        category = self.category_repository.get_by_slug(slug)
        if not category:
            raise NotFoundError('Category not found')
        return category
