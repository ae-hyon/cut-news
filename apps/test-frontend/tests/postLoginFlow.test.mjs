import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('post-kakao login preserves completed pre-login onboarding preference for the authenticated user', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /preference\?\.onboarding_completed/)
  assert.match(source, /nextUserId !== preference\.user_id/)
  assert.match(source, /saveUserPreference\(nextUserId/)
  assert.match(source, /primary_categories: preference\.primary_categories/)
  assert.match(source, /subcategories: preference\.subcategories/)
})

test('authenticated sessions enter the feed flow directly instead of rendering a login-status badge', async () => {
  const app = await readFile(path.join(projectRoot, 'src/App.tsx'), 'utf8')
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.doesNotMatch(app, /AuthStatusBadge/)
  assert.match(source, /const bootstrap = await auth\.loadBootstrap\(\)/)
  assert.match(source, /await loadUserState\(bootstrap\.session\.user_id, rememberedViewContext\)/)
  assert.match(source, /view\.resetToHome\(\)/)
})
