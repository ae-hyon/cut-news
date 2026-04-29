import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('scrap toggle preserves the current tab context instead of forcing home reloads', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const preferredTab = view\.activeTab/)
  assert.match(source, /await loadUserState\(auth\.userId as string, \{\s*preferredTab,\s*reopenDetailArticleId,\s*preferredArchiveMonth,\s*preferredArchiveDate,\s*\}\)/s)
  assert.match(source, /if \(options\?\.preferredTab && options\.preferredTab !== 'home'\) \{\s*view\.changeTab\(options\.preferredTab\)\s*return\s*\}/s)
})

test('scrap toggle from detail reopens the same article while preserving the underlying tab', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const reopenDetailArticleId = view\.isDetailOpen \? article\.id : null/)
  assert.match(source, /if \(options\?\.reopenDetailArticleId\) \{\s*view\.changeTab\(options\.preferredTab \?\? 'home'\)\s*await content\.openArticle\(options\.reopenDetailArticleId, nextUserId\)\s*view\.openDetail\(options\.reopenDetailArticleId\)\s*return\s*\}/s)
})
