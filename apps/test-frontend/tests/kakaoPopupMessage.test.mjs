import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('usePrototypeApp listens for kakao popup completion messages and checks the session', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /annoyingcap:kakao-authenticated/)
  assert.match(source, /window\.addEventListener\('message'/)
  assert.match(source, /checkKakaoSession\(true\)/)
})

test('useAuthSession turns redirected kakao popup landing into a completion message with resolved user id', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/useAuthSession.ts'), 'utf8')

  assert.match(source, /URLSearchParams\(window\.location\.search\)/)
  assert.match(source, /searchParams\.get\('auth'\) !== 'kakao'/)
  assert.match(source, /const sessionData = await getAnonymousSession\(\)/)
  assert.match(source, /window\.opener\.postMessage\(\{ type: 'annoyingcap:kakao-authenticated', userId: sessionData\.user_id \}/)
  assert.match(source, /'\*'/)
  assert.match(source, /window\.close\(\)/)
})
