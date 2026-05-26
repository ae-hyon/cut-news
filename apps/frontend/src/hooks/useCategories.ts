import { useEffect } from 'react';
import { useCategoryStore } from '@/stores/category';

export function useCategories() {
  const { categories, isLoading, error, fetchCategories } = useCategoryStore();

  useEffect(() => {
    if (categories.length === 0 && !isLoading && !error) {
      fetchCategories();
    }
  }, [categories.length, isLoading, error, fetchCategories]);

  return { categories, isLoading, error, refetch: fetchCategories };
}
