import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('scrap toggle preserves the current tab context instead of forcing home reloads', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const preferredTab = view\.activeTab/)
  assert.match(source, /if \(restoredViewContext\?\.preferredTab && restoredViewContext\.preferredTab !== 'home'\) \{\s*view\.changeTab\(restoredViewContext\.preferredTab\)\s*return\s*\}/s)
})

test('scrap toggle from detail reopens the same article while preserving the underlying tab', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const reopenDetailArticleId = view\.isDetailOpen \? article\.id : null/)
  assert.match(source, /if \(restoredViewContext\?\.reopenDetailArticleId\) \{\s*view\.changeTab\(restoredViewContext\.preferredTab \?\? 'home'\)\s*await content\.openArticle\(restoredViewContext\.reopenDetailArticleId, nextUserId\)\s*view\.openDetail\(restoredViewContext\.reopenDetailArticleId\)\s*return\s*\}/s)
})
