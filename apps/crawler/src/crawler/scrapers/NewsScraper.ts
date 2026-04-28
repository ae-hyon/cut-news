import * as cheerio from 'cheerio';
import { BaseScraper, NewsArticle } from './scrapers/base.scraper';

// ─── 사이트별 본문 셀렉터 힌트 ────────────────────────────────────────────────
// WebFetch로 확인: 각 사이트 모두 h1 + p 구조이며 og:meta 보유
const CONTENT_SELECTORS: Record<string, string[]> = {
  'newsis.com':       ['#textBody p', '.view_txt p',           '.news_article_body p'],
  'mt.co.kr':         ['#textBody p', '.news_cnt_detail_wrap p','#newsContents p'    ],
  'news1.kr':         ['.article-body p', '#article-body p',   '.news_body_wrap p'  ],
  'imnews.imbc.com':  ['.news_body p', '.article_txt p',       '.view_con p'        ],
};

const GENERIC_FALLBACK = [
  'article p',
  '[class*="article"] p',
  '[class*="content"] p',
  'section p',
];

// ─── GenericNewsScraper ───────────────────────────────────────────────────────
class GenericNewsScraper extends BaseScraper {
  readonly source = 'generic';

  async scrape(url: string): Promise<NewsArticle> {
    const $ = await this.fetchHtml(url);
    const hostname = new URL(url).hostname.replace(/^www\./, '');

    const title =
      $('meta[property="og:title"]').attr('content')?.trim() ||
      $('meta[name="twitter:title"]').attr('content')?.trim() ||
      $('h1').first().text().replace(/\s+/g, ' ').trim();

    const media =
      $('meta[property="og:site_name"]').attr('content')?.trim() ||
      $('meta[name="twitter:site"]').attr('content')?.replace('@', '').trim() ||
      hostname;

    const siteSelectors = CONTENT_SELECTORS[hostname] ?? [];
    const content = this.extractContent($, [...siteSelectors, ...GENERIC_FALLBACK]);

    return { url, title, content, media, scrapedAt: new Date() };
  }

  private extractContent($: cheerio.CheerioAPI, selectors: string[]): string {
    for (const sel of selectors) {
      const paragraphs = $(sel)
        .map((_, el) => $(el).text().replace(/\s+/g, ' ').trim())
        .get()
        .filter((t) => t.length > 30);   // 캡션·광고 짧은 텍스트 제거

      if (paragraphs.length >= 2) {
        return paragraphs.join('\n');
      }
    }
    return '';
  }
}

// ─── 선정 기사 5건 ─────────────────────────────────────────────────────────────
interface ArticleEntry {
  index: number;
  topic: string;
  url: string;
}

const ARTICLES: ArticleEntry[] = [
  {
    index: 1,
    topic: '방시혁, 2000억 부당이득 혐의 구속영장 신청',
    url: 'https://www.newsis.com/view/NISX20260421_0003600696',
  },
  {
    index: 2,
    topic: '뉴진스, 코펜하겐 포착…민지 합류 미정 컴백 임박',
    url: 'https://www.mt.co.kr/entertainment/2026/04/27/2026042714067299138',
  },
  {
    index: 3,
    topic: '위너 송민호, 병역법 위반 징역 1년 6개월 구형',
    url: 'https://www.news1.kr/society/court-prosecution/6143557',
  },
  {
    index: 4,
    topic: '어도어, 다니엘·민희진에 431억 손해배상 청구 소송',
    url: 'https://www.newsis.com/view/NISX20260325_0003563829',
  },
  {
    index: 5,
    topic: '위너 송민호, 부실 복무 이유 묻자 즉답 회피 (현장)',
    url: 'https://imnews.imbc.com/news/2026/society/article/6816838_36918.html',
  },
];

// ─── 출력 ──────────────────────────────────────────────────────────────────────
function printResult(entry: ArticleEntry, article: NewsArticle): void {
  const LINE = '═'.repeat(68);
  console.log(`\n${LINE}`);
  console.log(`[${entry.index}/5] ${entry.topic}`);
  console.log(LINE);
  console.log(`  언론사  : ${article.media}`);
  console.log(`  제목    : ${article.title}`);
  console.log(`  본문    : ${article.content.slice(0, 200).trimEnd()}…`);
  console.log(`  URL     : ${article.url}`);
  console.log(`  수집시각: ${article.scrapedAt.toISOString()}`);
}

function printError(entry: ArticleEntry, err: unknown): void {
  console.error(`\n[${entry.index}/5] ❌ 실패: ${entry.topic}`);
  console.error(`  URL  : ${entry.url}`);
  console.error(`  오류 : ${(err as Error).message}`);
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ─── 진입점 ───────────────────────────────────────────────────────────────────
async function main(): Promise<void> {
  const scraper = new GenericNewsScraper();
  let successCount = 0;

  console.log('뉴스 크롤링 시작 (총 5건)\n');

  for (const entry of ARTICLES) {
    try {
      const article = await scraper.scrape(entry.url);
      printResult(entry, article);
      successCount++;
    } catch (err) {
      printError(entry, err);
    }

    if (entry.index < ARTICLES.length) {
      await sleep(1_500);   // 사이트 부하 방지용 딜레이
    }
  }

  console.log(`\n${'─'.repeat(68)}`);
  console.log(`완료: ${successCount} / ${ARTICLES.length}건 성공`);
}

main().catch((err) => {
  console.error('예기치 않은 오류:', err);
  process.exit(1);
});
