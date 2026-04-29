import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('remembered view context stores detail article ids while a detail screen is open', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /rememberViewContext\(\{\s*tab: view\.activeTab === 'scraps' \|\| view\.activeTab === 'archive' \? view\.activeTab : 'home',/s)
  assert.match(source, /detailArticleId: view\.isDetailOpen \? view\.detailArticleId : null/)
  assert.match(source, /view\.detailArticleId,/)
})

test('bootstrap reopens remembered detail articles after content and archive data load', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /function toLoadUserStateOptions\(rememberedViewContext: ReturnType<typeof getRememberedViewContext>\): LoadUserStateOptions \| undefined/)
  assert.match(source, /reopenDetailArticleId: rememberedViewContext\.detailArticleId \?\? null/)
})
