import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('editing completed preferences marks the flow as an edit, captures return context, and reopens onboarding', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const \[isEditingCompletedPreference, setIsEditingCompletedPreference\] = React\.useState\(false\)/)
  assert.match(source, /const \[preferenceEditReturnContext, setPreferenceEditReturnContext\] = React\.useState<PreferenceEditReturnContext \| null>\(null\)/)
  assert.match(source, /const editCompletedPreferences = React\.useCallback\(\(\) => \{\s*setIsEditingCompletedPreference\(true\)\s*setPreferenceEditReturnContext\(\{\s*preferredTab: view\.activeTab,\s*preferredArchiveMonth: view\.activeTab === 'archive' \? archive\.archiveMonth : null,\s*preferredArchiveDate: view\.activeTab === 'archive' \? archive\.archiveDateData\?\.date \?\? null : null,\s*reopenDetailArticleId: view\.isDetailOpen \? view\.detailArticleId : null,\s*\}\)\s*view\.resetToOnboarding\(\)/s)
})

test('submitting edited preferences reloads live user state into the saved return context instead of resetting home', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /if \(isEditingCompletedPreference\) \{\s*const returnContext = preferenceEditReturnContext\s*setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)\s*await loadUserState\(auth\.userId as string, returnContext \?\? undefined\)\s*return\s*\}/s)
  assert.match(source, /view\.resetToOnboardingComplete\(\)/)
})

test('loading or starting a new preference flow clears edit mode and saved return context before continuing', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)\s*auth\.setUserId\(nextUserId\)/s)
  assert.match(source, /setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)\s*content\.clearContent\(\)/s)
  assert.match(source, /setPreference\(null\)\s*setIsEditingCompletedPreference\(false\)\s*setPreferenceEditReturnContext\(null\)\s*content\.clearContent\(\)/s)
})
