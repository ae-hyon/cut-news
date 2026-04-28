import type { Category, Subcategory } from './types'

export function getCategoryDescription(category: Category) {
  return category.description || '주요 이슈를 한 번에 요약해드려요'
}

export function getSubcategoryDescription(subcategory: Subcategory) {
  return subcategory.description || '세부 이슈를 집중해서 받아보세요'
}
