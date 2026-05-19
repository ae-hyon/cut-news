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
});
