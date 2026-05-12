export const DEMO_USER_ID = 'demo-user'
export const CARD_TONES = ['tone-light', 'tone-soft', 'tone-outline', 'tone-dark']

const CATEGORY_LABELS: Record<string, string> = {
  stock: '주식시장',
  crypto: '가상자산',
  realestate: '부동산',
  politics: '정치',
  economy: '경제',
  tech: 'IT/테크',
  entertainment: '연예',
  sports: '스포츠',
  global: '국제',
  lifestyle: '라이프',
}

const SUBCATEGORY_LABELS: Record<string, string> = {
  'stock-domestic': '국내주식',
  'stock-overseas': '해외주식',
  'stock-etf': 'ETF',
  'stock-unlisted': '비상장주식',
  'crypto-bitcoin': '비트코인',
  'crypto-altcoin': '알트코인',
  'crypto-defi': 'DeFi',
  'crypto-nft': 'NFT',
  'realestate-apt': '아파트',
  'realestate-subscription': '청약',
  'realestate-lease': '전세/월세',
  'realestate-commercial': '상업용',
  'politics-domestic': '국내정치',
  'politics-diplomacy': '외교',
  'politics-policy': '정책',
  'economy-macro': '거시경제',
  'economy-finance': '금융',
  'economy-trade': '무역',
  'tech-ai': 'AI',
  'tech-semiconductor': '반도체',
  'tech-startup': '스타트업',
  'tech-bigtech': '빅테크',
  'entertainment-kpop': 'K-POP',
  'entertainment-drama': '드라마',
  'entertainment-movie': '영화',
  'sports-soccer': '축구',
  'sports-baseball': '야구',
  'sports-basketball': '농구',
  'sports-esports': 'e스포츠',
  'global-us': '미국',
  'global-china': '중국',
  'global-europe': '유럽',
  'global-asia': '아시아',
  'lifestyle-health': '건강',
  'lifestyle-travel': '여행',
  'lifestyle-food': '맛집',
}

export function toCategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return CATEGORY_LABELS[slug] || slug
}

export function toSubcategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return SUBCATEGORY_LABELS[slug] || slug
}
