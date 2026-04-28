import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('post-login home entry is gated by saved preference, not stale kakao access-token onboarding flag', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.doesNotMatch(source, /if \(!pref\.onboarding_completed \|\| !sessionData\.onboarding_completed\)/)
  assert.match(source, /if \(!pref\.onboarding_completed\) \{/)
  assert.match(source, /onboarding_completed: pref\.onboarding_completed/)
})
