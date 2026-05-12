import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('content feed applies scrap state across feed, scraps, and selected detail before reload', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/useContentFeed.ts'), 'utf8')

  assert.match(source, /const applyScrapState = React\.useCallback\(\(articleId: string, nextScrapped: boolean\) => \{/)
  assert.match(source, /setFeed\(\(currentFeed\) => currentFeed \? \{/)
  assert.match(source, /articles: block\.articles\.map\(\(article\) => updateArticleCard\(article, articleId, nextScrapped\)\)/)
  assert.match(source, /setScraps\(\(currentScraps\) => \{/)
  assert.match(source, /if \(!nextScrapped\) return withoutArticle/)
  assert.match(source, /const sourceArticle = fromSelectedArticle \?\? fromFeed/)
  assert.match(source, /setSelectedArticle\(\(currentArticle\) => currentArticle && currentArticle\.id === articleId/)
})

test('prototype toggleScrap applies optimistic scrap state before triggering full reload', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const nextScrapped = !article\.is_scrapped/)
  assert.match(source, /await content\.toggleScrap\(auth\.userId as string, article\)/)
  assert.match(source, /content\.applyScrapState\(article\.id, nextScrapped\)/)
})
