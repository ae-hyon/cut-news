import type { NewsItem } from '@/types'

export const MOCK_NEWS: NewsItem[] = [
  {
    id: '1',
    title: '코스피, 미중 무역협상 기대감에 2,700선 돌파',
    summary:
      '미중 무역협상 재개 소식에 코스피가 장중 2,700선을 돌파했다. 외국인 순매수가 3거래일 연속 이어지며 반도체·2차전지 대형주 중심으로 강세를 보였다.',
    category: '주식시장',
    sourceUrl: 'https://example.com/1',
    publishedAt: '2026-04-28',
    blockSize: 'large',
  },
  {
    id: '2',
    title: '비트코인, 10만 달러 재돌파 시도',
    summary:
      '비트코인이 9만8천 달러를 넘어서며 10만 달러 재돌파를 시도하고 있다. 기관 투자자들의 ETF 유입이 지속되는 가운데 온체인 지표도 강세 신호를 보이고 있다.',
    category: '가상자산',
    sourceUrl: 'https://example.com/2',
    publishedAt: '2026-04-28',
    blockSize: 'medium',
  },
  {
    id: '3',
    title: 'OpenAI, GPT-5 공개 임박… AI 업계 지각변동 예고',
    summary:
      'OpenAI가 차세대 모델 GPT-5 공개를 앞두고 있다. 멀티모달 성능이 대폭 향상되었으며 에이전트 기능이 기본 탑재될 예정이다.',
    category: 'IT/테크',
    sourceUrl: 'https://example.com/3',
    publishedAt: '2026-04-28',
    blockSize: 'large',
  },
  {
    id: '4',
    title: '서울 아파트 매매가 12주 연속 상승',
    summary:
      '서울 아파트 매매가가 12주 연속 상승세를 이어갔다. 강남3구와 마용성 중심으로 상승폭이 확대되고 있다.',
    category: '부동산',
    sourceUrl: 'https://example.com/4',
    publishedAt: '2026-04-28',
    blockSize: 'small',
  },
  {
    id: '5',
    title: '한은, 기준금리 동결… "하반기 인하 가능성 열어둬"',
    summary:
      '한국은행이 기준금리를 2.75%로 동결했다. 다만 이창용 총재는 하반기 경기 상황에 따라 인하 가능성을 배제하지 않겠다고 밝혔다.',
    category: '경제',
    sourceUrl: 'https://example.com/5',
    publishedAt: '2026-04-28',
    blockSize: 'medium',
  },
  {
    id: '6',
    title: 'MLB 김도현, 시즌 8호 홈런 폭발',
    summary:
      '샌디에이고 파드리스 김도현이 시즌 8호 홈런을 기록하며 팀 승리를 이끌었다.',
    category: '스포츠',
    sourceUrl: 'https://example.com/6',
    publishedAt: '2026-04-28',
    blockSize: 'small',
  },
  {
    id: '7',
    title: '넷플릭스 오리지널 "지옥2" 글로벌 1위 등극',
    summary:
      '넷플릭스 오리지널 시리즈 지옥 시즌2가 공개 첫 주 글로벌 TV 시리즈 1위를 차지했다. 83개국에서 톱10에 진입하며 K-콘텐츠의 위상을 다시 한번 증명했다.',
    category: '연예',
    sourceUrl: 'https://example.com/7',
    publishedAt: '2026-04-28',
    blockSize: 'medium',
  },
]
