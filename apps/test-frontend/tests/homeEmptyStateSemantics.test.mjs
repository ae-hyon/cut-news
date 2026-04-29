import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('home empty state distinguishes onboarding-before-selection from preference-filtered zero-result feeds', async () => {
  const home = await source('src/components/screens/HomeScreen.tsx')

  const css = await source('src/styles/screens.css')

  assert.match(home, /const emptyMessage = preference\?\.onboarding_completed/)
  assert.match(home, /\? '선택한 관심사에 맞는 뉴스가 아직 없어요\.'/)
  assert.match(home, /: '관심사를 선택하면 뉴스가 표시됩니다\.'/)
  assert.match(home, /<div className="empty-state">\{emptyMessage\}<\/div>/)
  assert.match(home, /preference\?\.onboarding_completed \? \(/)
  assert.match(home, /상단 선택 버튼에서 관심 분야를 다시 조정해보세요\./)
  assert.match(css, /\.screen-helper-text/)
  assert.match(css, /\.home-empty-helper/)
})
