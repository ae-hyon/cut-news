import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('frontend feed/detail/scrap flows are wired to backend APIs instead of local mock articles', async () => {
  const backendApi = await readFile(path.join(projectRoot, 'src/services/backendApi.ts'), 'utf8')
  const content = await readFile(path.join(projectRoot, 'src/hooks/useContentFeed.ts'), 'utf8')
  const home = await readFile(path.join(projectRoot, 'src/components/screens/HomeScreen.tsx'), 'utf8')

  assert.match(backendApi, /api<FeedResponse>\(`\/v1\/users\/\$\{userId\}\/feed`\)/)
  assert.match(backendApi, /api<ScrapResponse>\(`\/v1\/users\/\$\{userId\}\/scraps`\)/)
  assert.match(backendApi, /api<ArticleDetail>\(`\/v1\/articles\/\$\{articleId\}/)
  assert.match(backendApi, /api<void>\(`\/v1\/users\/\$\{userId\}\/scraps\/\$\{articleId\}`/)

  assert.match(content, /getUserFeed\(userId\)/)
  assert.match(content, /getUserScraps\(userId\)/)
  assert.match(content, /getArticleDetail\(articleId, userId\)/)
  assert.match(content, /addScrap\(userId, article\.id\)/)
  assert.match(content, /removeScrap\(userId, article\.id\)/)
  assert.doesNotMatch(home, /MOCK|mock|fixture|dummy|sample/i)
})
