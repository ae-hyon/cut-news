import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const read = (path) => readFileSync(join(root, path), 'utf8');

describe('real frontend backend contract', () => {
  it('uses current-user preference routes instead of legacy user-id preference routes', () => {
    const source = read('src/services/authApi.ts');
    assert.match(source, /\/v1\/me\/preference/);
    assert.doesNotMatch(source, /\/v1\/users\/\$\{userId\}\/preferences/);
  });

  it('types the preference snapshot returned by GET /v1/me', () => {
    const source = read('src/lib/types.ts');
    assert.match(source, /interface UserPreferenceSnapshot/);
    assert.match(source, /preference:\s*UserPreferenceSnapshot\s*\|\s*null/);
  });

  it('refreshes the auth token once before surfacing protected API 401s', () => {
    const apiSource = read('src/lib/api.ts');
    const authSource = read('src/services/authApi.ts');
    assert.match(apiSource, /response\.status === 401/);
    assert.match(apiSource, /\/v1\/auth\/token\/refresh/);
    assert.match(authSource, /retryOnUnauthorized: false/);
  });

  it('wires feed, details, scraps, and archive screens to /v1/me APIs instead of MOCK_NEWS', () => {
    const apiSource = read('src/services/contentApi.ts');
    for (const endpoint of [
      '/v1/me/feed',
      '/v1/me/articles/',
      '/v1/me/scraps',
      '/v1/me/archive',
    ]) {
      assert.match(apiSource, new RegExp(endpoint.replaceAll('/', '\\/')));
    }

    for (const path of [
      'src/app/(main)/page.tsx',
      'src/app/news/[id]/page.tsx',
      'src/app/(main)/scrap/page.tsx',
      'src/app/(main)/archive/page.tsx',
    ]) {
      const source = read(path);
      assert.doesNotMatch(source, /MOCK_NEWS/);
    }
  });

  it('treats monthly archive days as metadata-only snapshot rows', () => {
    const typesSource = read('src/lib/types.ts');
    const archiveSource = read('src/app/(main)/archive/page.tsx');

    assert.match(typesSource, /interface ArchiveDay/);
    assert.match(typesSource, /has_feed:\s*boolean/);
    assert.match(typesSource, /snapshot_id:\s*number/);
    const archiveDaySource = typesSource.match(
      /interface ArchiveDay \{[\s\S]*?\n\}/,
    )?.[0];
    assert.ok(archiveDaySource);
    assert.doesNotMatch(archiveDaySource, /items:\s*ArticleCard\[\]/);
    assert.match(archiveSource, /archiveDay\?\.has_feed \?\? false/);
    assert.doesNotMatch(archiveSource, /archiveDay\.items/);
  });

  it('passes snapshot_id from feed and archive article opens into detail reads', () => {
    const apiSource = read('src/services/contentApi.ts');
    const typesSource = read('src/types/index.ts');
    const homeSource = read('src/app/(main)/page.tsx');
    const archiveSource = read('src/app/(main)/archive/page.tsx');
    const detailSource = read('src/app/news/[id]/page.tsx');

    assert.match(typesSource, /snapshotId\?:\s*number/);
    assert.match(
      apiSource,
      /snapshot_id=\$\{encodeURIComponent\(snapshotId\)\}/,
    );
    assert.match(homeSource, /feed\.snapshot_id/);
    assert.match(archiveSource, /response\.snapshot_id/);
    assert.match(detailSource, /useSearchParams/);
    assert.match(detailSource, /getMyArticle\(id, snapshotId\)/);
  });
});
