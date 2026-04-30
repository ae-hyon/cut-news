import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')
const source = (rel) => readFile(path.join(projectRoot, rel), 'utf8')

test('detail screen exposes a preference edit entry and App wires it to editCompletedPreferences', async () => {
  const app = await source('src/App.tsx')
  const detail = await source('src/components/screens/DetailScreen.tsx')

  assert.match(detail, /onEditPreference\?: \(\) => void/)
  assert.match(detail, /showPreferenceMismatchNotice\?: boolean/)
  assert.match(detail, /aria-label="관심 분야 편집"/)
  assert.match(detail, />관심 분야 수정</)
  assert.match(app, /onEditPreference=\{app\.editCompletedPreferences\}/)
  assert.match(app, /showPreferenceMismatchNotice=\{showDetailPreferenceMismatchNotice\}/)
})
