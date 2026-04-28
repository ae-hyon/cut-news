import React from 'react'
import type { Category, PreferenceMode, Subcategory, UserPreference } from '../lib/types'
import type { PreferencePayload } from '../services/backendApi'

export type NarrowStep = 1 | 2
export type SubcategoryMap = Record<string, Subcategory[]>

const DEFAULT_WIDE_CATEGORIES: string[] = []
const DEFAULT_NARROW_PRIMARY = ''

export function usePreferenceSelection(categories: Category[]) {
  const [mode, setMode] = React.useState<PreferenceMode>('wide')
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>(DEFAULT_WIDE_CATEGORIES)
  const [selectedPrimary, setSelectedPrimary] = React.useState<string>(DEFAULT_NARROW_PRIMARY)
  const [selectedSubs, setSelectedSubs] = React.useState<string[]>([])
  const [narrowStep, setNarrowStep] = React.useState<NarrowStep>(1)

  const subcategoryMap = React.useMemo<SubcategoryMap>(() => {
    const map: SubcategoryMap = {}
    for (const category of categories) map[category.slug] = category.subcategories || []
    return map
  }, [categories])

  const chooseMode = React.useCallback((nextMode: PreferenceMode) => {
    setMode(nextMode)
    if (nextMode === 'wide') {
      setSelectedCategories((current) => (current.length ? current.slice(0, 5) : DEFAULT_WIDE_CATEGORIES))
      setSelectedPrimary('')
      setSelectedSubs([])
      setNarrowStep(1)
      return
    }

    setSelectedCategories([])
    setSelectedPrimary((current) => current || DEFAULT_NARROW_PRIMARY)
    setSelectedSubs([])
    setNarrowStep(1)
  }, [])

  const hydratePreferenceState = React.useCallback((pref: UserPreference | null) => {
    if (!pref) return
    setMode(pref.mode)
    if (pref.mode === 'wide') {
      setSelectedCategories(pref.primary_categories.length ? [...pref.primary_categories] : DEFAULT_WIDE_CATEGORIES)
      setSelectedPrimary('')
      setSelectedSubs([])
      setNarrowStep(1)
      return
    }

    const primary = pref.primary_categories[0] || DEFAULT_NARROW_PRIMARY
    setSelectedCategories([])
    setSelectedPrimary(primary)
    setSelectedSubs(pref.subcategories.length ? [...pref.subcategories] : [])
    setNarrowStep(pref.subcategories.length ? 2 : 1)
  }, [])

  const toggleWideCategory = React.useCallback((slug: string) => {
    setSelectedCategories((current) =>
      current.includes(slug) ? current.filter((item) => item !== slug) : [...current, slug].slice(0, 5)
    )
  }, [])

  const toggleSubcategory = React.useCallback((slug: string) => {
    setSelectedSubs((current) =>
      current.includes(slug) ? current.filter((item) => item !== slug) : [...current, slug]
    )
  }, [])

  const isWideValid = selectedCategories.length >= 3 && selectedCategories.length <= 5
  const isNarrowValid = Boolean(selectedPrimary) && selectedSubs.length >= 1
  const isSelectionValid = mode === 'wide' ? isWideValid : isNarrowValid

  function toPreferencePayload(): PreferencePayload {
    return mode === 'wide'
      ? { mode, primary_categories: selectedCategories, subcategories: [] }
      : { mode, primary_categories: selectedPrimary ? [selectedPrimary] : [], subcategories: selectedSubs }
  }

  return {
    mode,
    selectedCategories,
    selectedPrimary,
    selectedSubs,
    narrowStep,
    subcategoryMap,
    setMode: chooseMode,
    setSelectedPrimary,
    setNarrowStep,
    hydratePreferenceState,
    toggleWideCategory,
    toggleSubcategory,
    isWideValid,
    isNarrowValid,
    isSelectionValid,
    toPreferencePayload,
  }
}
