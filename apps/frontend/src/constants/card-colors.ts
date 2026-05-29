export const CARD_COLORS = [
  '#fceade',
  '#f3782b',
  '#ffbb94',
  '#ff9557',
  '#efefef',
];

export function getCardColor(index: number): string {
  return CARD_COLORS[index % CARD_COLORS.length];
}
