export const DEMO_USER_ID = 'ui-demo-user'
export const CARD_TONES = ['tone-light', 'tone-soft', 'tone-outline', 'tone-dark']

const CATEGORY_LABELS: Record<string, string> = {
  economy: '경제',
  politics: '정치',
  entertainment: '연예',
  tech: '테크',
  sports: '스포츠',
}

export function toCategoryLabel(slug?: string | null): string {
  if (!slug) return ''
  return CATEGORY_LABELS[slug] || slug
}
