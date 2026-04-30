import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')
const source = (rel) => readFile(path.join(projectRoot, rel), 'utf8')

test('detail screen shows a current-preference mismatch notice when a reopened article falls outside the saved preference', async () => {
  const app = await source('src/App.tsx')
  const detail = await source('src/components/screens/DetailScreen.tsx')
  const css = await source('src/styles/screens.css')

  assert.match(app, /function articleMatchesPreference\(/)
  assert.match(app, /const showDetailPreferenceMismatchNotice = !articleMatchesPreference\(app\.selectedArticle, app\.preference\)/)
  assert.match(app, /showPreferenceMismatchNotice=\{showDetailPreferenceMismatchNotice\}/)
  assert.match(detail, /showPreferenceMismatchNotice\?: boolean/)
  assert.match(detail, /이 기사는 현재 관심사 밖에 있지만, 저장하거나 원문으로 계속 확인할 수 있어요\./)
  assert.match(css, /\.detail-preference-mismatch/)
})
