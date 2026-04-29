import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('editing completed preferences marks the flow as an edit and reopens onboarding', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const \[isEditingCompletedPreference, setIsEditingCompletedPreference\] = React\.useState\(false\)/)
  assert.match(source, /const editCompletedPreferences = React\.useCallback\(\(\) => \{\s*setIsEditingCompletedPreference\(true\)\s*view\.resetToOnboarding\(\)/s)
})

test('submitting edited preferences reloads live user state instead of returning to onboarding complete', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /if \(isEditingCompletedPreference\) \{\s*setIsEditingCompletedPreference\(false\)\s*await loadUserState\(auth\.userId as string\)\s*return\s*\}/s)
  assert.match(source, /view\.resetToOnboardingComplete\(\)/)
})

test('loading or starting a new preference flow clears edit mode before continuing', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /setIsEditingCompletedPreference\(false\)\s*auth\.setUserId\(nextUserId\)/s)
  assert.match(source, /setIsEditingCompletedPreference\(false\)\s*content\.clearContent\(\)/s)
})
