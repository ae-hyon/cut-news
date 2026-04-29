import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('scraps screen explains that saved articles stay available independently of current preferences', async () => {
  const screen = await readFile(path.join(projectRoot, 'src/components/screens/ScrapsScreen.tsx'), 'utf8')
  const readme = await readFile(path.join(projectRoot, 'README.md'), 'utf8')

  assert.match(screen, /관심 분야를 바꿔도, 저장한 기사는 여기서 다시 볼 수 있어요\./)
  assert.match(readme, /스크랩은 현재 관심 분야 필터와 별개로 유지되는 개인 저장 목록으로 취급/)
})
