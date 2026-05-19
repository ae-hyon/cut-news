import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ScrapStore {
  scrappedIds: string[];
  toggleScrap: (id: string) => void;
  isScrapped: (id: string) => boolean;
}

export const useScrapStore = create<ScrapStore>()(
  persist(
    (set, get) => ({
      scrappedIds: [],

      toggleScrap: (id) => {
        const { scrappedIds } = get();
        if (scrappedIds.includes(id)) {
          set({ scrappedIds: scrappedIds.filter((s) => s !== id) });
        } else {
          set({ scrappedIds: [...scrappedIds, id] });
        }
      },

      isScrapped: (id) => get().scrappedIds.includes(id),
    }),
    { name: 'annoying-cap-scrap' },
  ),
);
