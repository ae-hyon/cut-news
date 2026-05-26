export type UserType = 'wide' | 'narrow';

export type BlockSize = 'large' | 'medium' | 'small';

export interface Category {
  id: string;
  name: string;
  description: string;
  subcategories?: SubCategory[];
}

export interface SubCategory {
  id: string;
  name: string;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  category: string;
  sourceUrl: string;
  publishedAt: string;
  blockSize: BlockSize;
  isScrapped?: boolean;
}

export interface OnboardingState {
  userType: UserType | null;
  selectedCategories: string[];
  selectedSubCategories: string[];
  narrowMainCategory: string | null;
}
