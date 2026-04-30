import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function read(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('bootstrap runs only once even when loadBootstrap callback identity changes after user state hydration', async () => {
  const source = await read('src/hooks/usePrototypeApp.ts')

  assert.match(source, /const bootstrapStartedRef = React\.useRef\(false\)/)
  assert.match(source, /if \(bootstrapStartedRef\.current\) return\s+bootstrapStartedRef\.current = true\s+void loadBootstrap\(\)/s)
})

test('frontend logout clears backend session through the dedicated API and exposes logout controls in authenticated screens', async () => {
  const api = await read('src/services/backendApi.ts')
  const authHook = await read('src/hooks/useAuthSession.ts')
  const app = await read('src/App.tsx')
  const topbar = await read('src/components/layout/TopBar.tsx')
  const detail = await read('src/components/screens/DetailScreen.tsx')
  const devPanel = await read('src/components/common/DevPanel.tsx')

  assert.match(api, /export function postLogout\(\) \{\s+return api<AuthLogoutResponse>\('\/v1\/auth\/logout', \{ method: 'POST' \}\)/s)
  assert.match(authHook, /const logout = React\.useCallback\(async \(\) => \{\s+const result = await postLogout\(\)/s)
  assert.match(app, /onLogout=\{app\.logout\}/)
  assert.match(topbar, /aria-label="로그아웃"/)
  assert.match(detail, /aria-label="로그아웃"/)
  assert.match(devPanel, /<button onClick=\{onLogout\} disabled=\{loading \|\| !userId\}>Logout<\/button>/)
})

test('intro screen explicitly separates first-time onboarding from returning-user kakao login', async () => {
  const intro = await read('src/components/screens/IntroScreen.tsx')
  const app = await read('src/App.tsx')

  assert.match(intro, /처음 쓰는 분은 관심사부터 고르고, 기존 사용자는 바로 카카오 로그인으로 이어서 볼 수 있어요\./)
  assert.match(intro, /처음 쓰는 분: 관심사 고르기/)
  assert.match(intro, /기존 사용자는 카카오 로그인/)
  assert.match(app, /onBeginKakaoLogin=\{app\.beginKakaoStart\}/)
})
