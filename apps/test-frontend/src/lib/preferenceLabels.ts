import type { Category, PreferenceMode } from './types'

type PreferenceSummaryInput = {
  primary_categories: string[]
  subcategories: string[]
}

function toCategoryLabel(categories: Category[], slug: string) {
  return categories.find((category) => category.slug === slug)?.name || slug
}

function toSubcategoryLabel(categories: Category[], slug: string) {
  for (const category of categories) {
    const subcategory = category.subcategories.find((item) => item.slug === slug)
    if (subcategory) return subcategory.name
  }
  return slug
}

export function formatPreferenceSummary(mode: PreferenceMode, preference: PreferenceSummaryInput | null | undefined, categories: Category[]) {
  const slugs = mode === 'wide'
    ? (preference?.primary_categories ?? [])
    : (preference?.subcategories ?? [])
  const toLabel = mode === 'wide' ? toCategoryLabel : toSubcategoryLabel

  return slugs.map((slug) => toLabel(categories, slug)).join(' · ')
}
