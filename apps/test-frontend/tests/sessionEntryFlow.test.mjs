import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('bootstrap with an existing authenticated session hydrates the full user state and enters home', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const bootstrap = await auth\.loadBootstrap\(\)/)
  assert.match(source, /if \(bootstrap\.session\.user_id\) \{\s*await loadUserState\(bootstrap\.session\.user_id, rememberedViewContext\)/s)
})

test('logged-in state is represented by direct home entry, not a visible login badge', async () => {
  const app = await readFile(path.join(projectRoot, 'src/App.tsx'), 'utf8')

  assert.doesNotMatch(app, /AuthStatusBadge/)
})
