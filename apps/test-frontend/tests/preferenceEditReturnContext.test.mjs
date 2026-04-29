import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('archive preference edit persists the selected archive month/date as the post-save return target', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /type PreferenceEditReturnContext = \{\s*preferredTab: AppTab\s*preferredArchiveMonth\?: string \| null\s*preferredArchiveDate\?: string \| null\s*reopenDetailArticleId\?: string \| null\s*\}/s)
  assert.match(source, /setPreferenceEditReturnContext\(\{\s*preferredTab: view\.activeTab,\s*preferredArchiveMonth: view\.activeTab === 'archive' \? archive\.archiveMonth : null,\s*preferredArchiveDate: view\.activeTab === 'archive' \? archive\.archiveDateData\?\.date \?\? null : null,\s*reopenDetailArticleId: view\.isDetailOpen \? view\.detailArticleId : null,\s*\}\)/s)
  assert.match(source, /await loadUserState\(auth\.userId as string, returnContext \?\? undefined\)/)
})
