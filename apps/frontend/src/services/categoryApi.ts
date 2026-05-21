import { api } from '@/lib/api';
import type { Category } from '@/lib/types';

export function getCategories() {
  return api<Category[]>('/v1/categories');
}
