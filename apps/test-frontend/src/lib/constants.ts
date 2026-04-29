export const DEMO_USER_ID = 'demo-user'
export const CARD_TONES = ['tone-light', 'tone-soft', 'tone-outline', 'tone-dark']

const CATEGORY_LABELS: Record<string, string> = {
  sectors: '산업 섹터',
  macro: '거시경제',
  assets: '투자 자산',
  policy: '정책·규제',
}

export function toCategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return CATEGORY_LABELS[slug] || slug
}
