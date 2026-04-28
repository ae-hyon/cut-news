from __future__ import annotations

from app.domain.entities import UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import ValidationError
from app.domain.repositories import CategoryRepository, UserPreferenceRepository

DEFAULT_PRIMARY = ['economy', 'politics', 'tech']


class UserPreferenceService:
    def __init__(self, preference_repository: UserPreferenceRepository, category_repository: CategoryRepository):
        self.preference_repository = preference_repository
        self.category_repository = category_repository

    def get_preferences(self, user_id: str) -> UserPreference:
        preference = self.preference_repository.get(user_id)
        if preference:
            return preference
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode.WIDE,
            primary_categories=DEFAULT_PRIMARY.copy(),
            subcategories=[],
            onboarding_completed=False,
        )

    def update_preferences(self, user_id: str, mode: str, primary_categories: list[str], subcategories: list[str]) -> UserPreference:
        enum_mode = PreferenceMode(mode)

        if len(set(primary_categories)) != len(primary_categories):
            raise ValidationError('primary categories must be unique')
        if len(set(subcategories)) != len(subcategories):
            raise ValidationError('subcategories must be unique')

        invalid_primary = [slug for slug in primary_categories if not self.category_repository.exists_by_slug(slug)]
        if invalid_primary:
            raise ValidationError(f'Unknown primary categories: {invalid_primary}')

        if enum_mode is PreferenceMode.WIDE:
            if not (3 <= len(primary_categories) <= 5):
                raise ValidationError('wide mode requires 3~5 primary categories')
            if subcategories:
                raise ValidationError('wide mode does not accept subcategories')
        else:
            if len(primary_categories) != 1:
                raise ValidationError('narrow mode requires exactly 1 primary category')
            if len(subcategories) < 1:
                raise ValidationError('narrow mode requires at least 1 subcategory')
            valid_subcategories = self.category_repository.valid_subcategories(primary_categories[0])
            invalid_sub = [slug for slug in subcategories if slug not in valid_subcategories]
            if invalid_sub:
                raise ValidationError(f'Subcategories do not belong to {primary_categories[0]}: {invalid_sub}')

        preference = UserPreference(
            user_id=user_id,
            mode=enum_mode,
            primary_categories=primary_categories,
            subcategories=subcategories,
            onboarding_completed=True,
        )
        return self.preference_repository.save(preference)
