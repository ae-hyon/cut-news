import { Category } from '@/types';

export const CATEGORIES: Category[] = [
  {
    id: 'stock',
    name: '주식시장',
    keywords: ['코스피', '나스닥', 'S&P500'],
    subcategories: [
      { id: 'stock-domestic', name: '국내주식' },
      { id: 'stock-overseas', name: '해외주식' },
      { id: 'stock-etf', name: 'ETF' },
      { id: 'stock-unlisted', name: '비상장주식' },
    ],
  },
  {
    id: 'crypto',
    name: '가상자산',
    keywords: ['비트코인', '이더리움', '알트코인'],
    subcategories: [
      { id: 'crypto-bitcoin', name: '비트코인' },
      { id: 'crypto-altcoin', name: '알트코인' },
      { id: 'crypto-defi', name: 'DeFi' },
      { id: 'crypto-nft', name: 'NFT' },
    ],
  },
  {
    id: 'realestate',
    name: '부동산',
    keywords: ['아파트', '청약', '전세'],
    subcategories: [
      { id: 'realestate-apt', name: '아파트' },
      { id: 'realestate-subscription', name: '청약' },
      { id: 'realestate-lease', name: '전세/월세' },
      { id: 'realestate-commercial', name: '상업용' },
    ],
  },
  {
    id: 'politics',
    name: '정치',
    keywords: ['국회', '대통령', '정당'],
    subcategories: [
      { id: 'politics-domestic', name: '국내정치' },
      { id: 'politics-diplomacy', name: '외교' },
      { id: 'politics-policy', name: '정책' },
    ],
  },
  {
    id: 'economy',
    name: '경제',
    keywords: ['금리', '환율', 'GDP'],
    subcategories: [
      { id: 'economy-macro', name: '거시경제' },
      { id: 'economy-finance', name: '금융' },
      { id: 'economy-trade', name: '무역' },
    ],
  },
  {
    id: 'tech',
    name: 'IT/테크',
    keywords: ['AI', '반도체', '스타트업'],
    subcategories: [
      { id: 'tech-ai', name: 'AI' },
      { id: 'tech-semiconductor', name: '반도체' },
      { id: 'tech-startup', name: '스타트업' },
      { id: 'tech-bigtech', name: '빅테크' },
    ],
  },
  {
    id: 'entertainment',
    name: '연예',
    keywords: ['K-POP', '드라마', '영화'],
    subcategories: [
      { id: 'entertainment-kpop', name: 'K-POP' },
      { id: 'entertainment-drama', name: '드라마' },
      { id: 'entertainment-movie', name: '영화' },
    ],
  },
  {
    id: 'sports',
    name: '스포츠',
    keywords: ['축구', '야구', 'NBA'],
    subcategories: [
      { id: 'sports-soccer', name: '축구' },
      { id: 'sports-baseball', name: '야구' },
      { id: 'sports-basketball', name: '농구' },
      { id: 'sports-esports', name: 'e스포츠' },
    ],
  },
  {
    id: 'global',
    name: '국제',
    keywords: ['미국', '중국', 'EU'],
    subcategories: [
      { id: 'global-us', name: '미국' },
      { id: 'global-china', name: '중국' },
      { id: 'global-europe', name: '유럽' },
      { id: 'global-asia', name: '아시아' },
    ],
  },
  {
    id: 'lifestyle',
    name: '라이프',
    keywords: ['건강', '여행', '맛집'],
    subcategories: [
      { id: 'lifestyle-health', name: '건강' },
      { id: 'lifestyle-travel', name: '여행' },
      { id: 'lifestyle-food', name: '맛집' },
    ],
  },
];

export const MAX_WIDE_CATEGORIES = 5;
