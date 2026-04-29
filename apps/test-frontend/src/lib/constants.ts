export const DEMO_USER_ID = 'demo-user'
export const CARD_TONES = ['tone-light', 'tone-soft', 'tone-outline', 'tone-dark']

const CATEGORY_LABELS: Record<string, string> = {
  sectors: '산업 섹터',
  macro: '거시경제',
  assets: '투자 자산',
  policy: '정책·규제',
}

const SUBCATEGORY_LABELS: Record<string, string> = {
  semiconductor: '반도체',
  mobility: '모빌리티',
  bio: '바이오',
  'rates-fx': '환율·금리',
  energy: '에너지',
  'supply-chain': '공급망',
  'domestic-stocks': '국내주식',
  'global-stocks': '해외주식',
  'real-estate': '부동산',
  fiscal: '재정',
  'central-bank': '중앙은행',
  regulation: '규제',
}

export function toCategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return CATEGORY_LABELS[slug] || slug
}

export function toSubcategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return SUBCATEGORY_LABELS[slug] || slug
}
