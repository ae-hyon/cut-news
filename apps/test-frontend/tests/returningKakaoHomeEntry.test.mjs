import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function source(file) {
  return readFile(path.join(projectRoot, file), 'utf8')
}

test('returning onboarded kakao users load content and avoid onboarding reset', async () => {
  const hook = await source('src/hooks/usePrototypeApp.ts')

  assert.match(hook, /if \(!pref\.onboarding_completed\) \{[\s\S]*view\.resetToOnboarding\(\)[\s\S]*return\s*\}/)
  assert.match(hook, /const \{ feed \} = await content\.loadContent\(nextUserId\)/)
  assert.match(hook, /setPreference\(pref\)/)
  assert.match(hook, /session_state: pref\.onboarding_completed \? 'onboarded' : sessionData\.session_state/)
  assert.match(hook, /view\.resetToHome\(\)/)
})

test('pre-login completed preference carry-over only applies when the authenticated user is not already onboarded', async () => {
  const hook = await source('src/hooks/usePrototypeApp.ts')

  assert.match(hook, /const canCarryCompletedPreference =[\s\S]*\(!pref\.onboarding_completed \|\| !sessionData\.onboarding_completed\)/)
  assert.match(hook, /if \(canCarryCompletedPreference\) \{[\s\S]*saveUserPreference\(nextUserId/)
})
