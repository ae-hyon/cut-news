import * as cheerio from 'cheerio';
import { BaseScraper, NewsArticle } from './base.scraper';

// ─── 언론사 코드 (네이버 뉴스 기준) ─────────────────────────────────────────
export const PRESS_CODES = {
  매일경제: '009',
  연합뉴스: '001',
  아시아경제: '277',
} as const;

export type PressName = keyof typeof PRESS_CODES;

// ─── 목록 페이지 결과 타입 ────────────────────────────────────────────────────
// 목록 단계에서는 본문이 없으므로 content를 Optional로 분리
export type PressArticleItem = Omit<NewsArticle, 'content'> & { content: '' };

// ─── 스크래퍼 ─────────────────────────────────────────────────────────────────
export class NaverPressScraper extends BaseScraper {
  readonly source = 'naver-press';

  private readonly listBaseUrl =
    'https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid=';

  // ── 목록 페이지: 언론사별 최신 기사 N개 수집 ─────────────────────────────
  async scrapeList(
    pressName: PressName,
    limit = 5,
  ): Promise<PressArticleItem[]> {
    const code = PRESS_CODES[pressName];
    const url = `${this.listBaseUrl}${code}`;
    const $ = await this.fetchHtml(url);

    const items: PressArticleItem[] = [];

    // 파이썬 원본 셀렉터 + 현행 Naver 구조 fallback 순서로 시도
    const candidateSelectors = [
      '.list_body .type06_headline li',   // 헤드라인 목록 (구 Naver)
      '.list_body .type06 li',            // 일반 목록 (구 Naver)
      '.list_body li',                    // 파이썬 원본
      'ul.list_news li',                  // 신 Naver 구조
    ];

    for (const sel of candidateSelectors) {
      const rows = $(sel);
      if (rows.length === 0) continue;

      rows.slice(0, limit).each((_, el) => {
        // 파이썬 원본: dt:not(.photo) a
        const anchor = $(el).find('dt:not(.photo) a').first();
        const title = anchor.text().trim();
        const href = anchor.attr('href') ?? '';
        const articleUrl = href.startsWith('http')
          ? href
          : `https://news.naver.com${href}`;

        if (title) {
          items.push({
            url: articleUrl,
            title,
            content: '',
            media: pressName,
            scrapedAt: new Date(),
          });
        }
      });

      if (items.length > 0) break; // 첫 번째로 결과가 나온 셀렉터 사용
    }

    return items;
  }

  // ── 전체 언론사 한 번에 수집 ───────────────────────────────────────────────
  async scrapeAllPresses(
    limit = 5,
  ): Promise<Record<PressName, PressArticleItem[]>> {
    const pressNames = Object.keys(PRESS_CODES) as PressName[];

    const entries = await Promise.allSettled(
      pressNames.map(async (name) => {
        const items = await this.scrapeList(name, limit);
        return [name, items] as const;
      }),
    );

    return Object.fromEntries(
      entries
        .filter((r): r is PromiseFulfilledResult<readonly [PressName, PressArticleItem[]]> =>
          r.status === 'fulfilled',
        )
        .map((r) => r.value),
    ) as Record<PressName, PressArticleItem[]>;
  }

  // ── 단일 기사 본문 수집 (BaseScraper 추상 메서드 구현) ─────────────────────
  async scrape(url: string): Promise<NewsArticle> {
    const $ = await this.fetchHtml(url);

    $('#dic_area script, #dic_area .end_photo_org').remove();

    const title = this.pickText($, [
      '#title_area span',
      'h2.media_end_head_headline',
    ]);
    const content = this.pickText($, [
      '#dic_area',
      '#newsct_article',
      '#articleBodyContents',
    ]);
    const media =
      $('.media_end_head_top_logo img').attr('alt') ??
      $('.press_logo img').attr('alt') ??
      '';

    return { url, title, content, media, scrapedAt: new Date() };
  }
}
