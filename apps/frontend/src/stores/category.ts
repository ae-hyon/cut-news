import { create } from 'zustand';
import type { Category as ApiCategory } from '@/lib/types';
import type { Category } from '@/types';
import { getCategories } from '@/services/categoryApi';

interface CategoryStore {
  categories: Category[];
  isLoading: boolean;
  error: string | null;
  fetchCategories: () => Promise<void>;
}

function mapCategory(api: ApiCategory): Category {
  return {
    id: api.slug,
    name: api.name,
    description: api.description,
    subcategories: api.subcategories.map((sub) => ({
      id: sub.slug,
      name: sub.name,
    })),
  };
}

export const useCategoryStore = create<CategoryStore>()((set) => ({
  categories: [],
  isLoading: false,
  error: null,

  fetchCategories: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await getCategories();
      set({
        categories: data.map(mapCategory),
        isLoading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: message });
    }
  },
}));
