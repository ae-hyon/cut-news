import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('editing completed preferences marks the flow as an edit, captures return context, and reopens onboarding', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const \[isEditingCompletedPreference, setIsEditingCompletedPreference\] = React\.useState\(false\)/)
  assert.match(source, /const \[preferenceEditReturnContext, setPreferenceEditReturnContext\] = React\.useState<PreferenceEditReturnContext \| null>\(null\)/)
})

test('submitting edited preferences reloads live user state into the saved return context instead of resetting home', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /if \(isEditingCompletedPreference\) \{\s*const returnContext = preferenceEditReturnContext\s*setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)\s*await loadUserState\(auth\.userId as string, returnContext \?\? undefined\)\s*return\s*\}/s)
  assert.match(source, /view\.resetToOnboardingComplete\(\)/)
})

test('loading out or starting fresh clears stale onboarding selection state before a new flow begins', async () => {
  const selection = await readFile(path.join(projectRoot, 'src/hooks/usePreferenceSelection.ts'), 'utf8')
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(selection, /const resetSelectionState = React\.useCallback\(\(nextMode: PreferenceMode = 'wide'\) => \{\s*setMode\(nextMode\)\s*setSelectedCategories\(DEFAULT_WIDE_CATEGORIES\)\s*setSelectedPrimary\(DEFAULT_NARROW_PRIMARY\)\s*setSelectedSubs\(\[\]\)\s*setNarrowStep\(1\)/s)
  assert.match(source, /const nextMode = preferenceSelection\.mode\s*preferenceSelection\.resetSelectionState\(nextMode\)\s*auth\.setUserId\(DEMO_USER_ID\)/s)
  assert.match(source, /const restartIntroFlow = React\.useCallback\(\(\) => \{\s*preferenceSelection\.resetSelectionState\(\)\s*clearRememberedDemoUserId\(\)/s)
  assert.match(source, /const logout = React\.useCallback\(async \(\) => \{\s*await runWithLoading\(async \(\) => \{\s*await auth\.logout\(\)\s*preferenceSelection\.resetSelectionState\(\)/s)
  assert.match(source, /const beginKakaoStart = React\.useCallback\(\(\) => \{\s*preferenceSelection\.resetSelectionState\(\)\s*setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)/s)
})
