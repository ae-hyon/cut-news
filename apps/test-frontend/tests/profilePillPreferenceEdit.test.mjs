import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('profile pill can reopen preference editing from any non-detail logged-in screen', async () => {
  const topBar = await source('src/components/layout/TopBar.tsx')
  const app = await source('src/App.tsx')
  const prototype = await source('src/hooks/usePrototypeApp.ts')

  assert.match(topBar, /onProfileClick\?: \(\) => void/)
  assert.match(topBar, /aria-label="사용자 프로필"/)
  assert.match(topBar, /onClick=\{onProfileClick\}/)
  assert.match(app, /<TopBar activeTab=\{app\.activeTab\} onNavigate=\{app\.changeTab\} onProfileClick=\{app\.editCompletedPreferences\} onLogout=\{app\.logout\} profilePill="선우" \/>/)
  assert.match(prototype, /const editCompletedPreferences = React\.useCallback\(\(\) => \{\s*setIsEditingCompletedPreference\(true\)\s*setPreferenceEditReturnContext\(\{\s*preferredTab: view\.activeTab,/s)
})
