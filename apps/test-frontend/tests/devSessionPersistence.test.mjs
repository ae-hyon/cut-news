import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('bootstrap re-enters the remembered demo user when no backend auth session exists', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const rememberedDemoUserId = getRememberedDemoUserId\(\)/)
  assert.match(source, /if \(rememberedDemoUserId\) \{\s*await loadUserState\(rememberedDemoUserId, rememberedViewContext\)/s)
})

test('demo entry persists the remembered demo user and intro reset clears local session memory', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /rememberDemoUserId\(DEMO_USER_ID\)/)
  assert.match(source, /if \(auth\.userId === DEMO_USER_ID\) rememberDemoUserId\(auth\.userId\)/)
  assert.match(source, /clearRememberedDemoUserId\(\)/)
  assert.match(source, /clearRememberedViewContext\(\)/)
})

test('app uses shared dev-session gating for demo entry visibility', async () => {
  const source = await readFile(path.join(projectRoot, 'src/App.tsx'), 'utf8')

  assert.match(source, /import \{ isDevDemoEntryEnabled \} from '\.\/lib\/devSession'/)
  assert.match(source, /const showDevDemoEntry = isDevDemoEntryEnabled\(window\.location\.search\)/)
})
