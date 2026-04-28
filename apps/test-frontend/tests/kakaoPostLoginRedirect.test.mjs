import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('kakao popup completion is handled even if the waiting-state render is missed', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /window\.addEventListener\('message', handleKakaoMessage\)/)
  assert.match(source, /event\.data\?\.type !== 'annoyingcap:kakao-authenticated'/)
  assert.match(source, /if \(event\.data\.userId\)/)
  assert.match(source, /void loadUserState\(event\.data\.userId\)/)
  assert.match(source, /void checkKakaoSession\(true\)/)
  assert.doesNotMatch(source, /if \(!auth\.kakaoAuthPending\) return undefined[\s\S]*window\.addEventListener\('message'/)
})

test('same-tab kakao callback landing checks the backend session instead of staying on the current screen', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /new URLSearchParams\(window\.location\.search\)/)
  assert.match(source, /searchParams\.get\('auth'\) !== 'kakao'/)
  assert.match(source, /window\.history\.replaceState/)
  assert.match(source, /void checkKakaoSession\(true\)/)
})
