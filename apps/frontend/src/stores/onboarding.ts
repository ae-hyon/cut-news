import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { UserType } from '@/types'

interface OnboardingStore {
  userType: UserType | null
  selectedCategories: string[]
  narrowMainCategory: string | null
  selectedSubCategories: string[]
  isCompleted: boolean

  setUserType: (type: UserType) => void
  toggleCategory: (id: string) => boolean
  setNarrowMainCategory: (id: string) => void
  toggleSubCategory: (id: string) => void
  setCompleted: (val: boolean) => void
  reset: () => void
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set, get) => ({
      userType: null,
      selectedCategories: [],
      narrowMainCategory: null,
      selectedSubCategories: [],
      isCompleted: false,

      setUserType: (type) =>
        set({
          userType: type,
          selectedCategories: [],
          narrowMainCategory: null,
          selectedSubCategories: [],
        }),

      toggleCategory: (id) => {
        const { selectedCategories } = get()
        if (selectedCategories.includes(id)) {
          set({ selectedCategories: selectedCategories.filter((c) => c !== id) })
          return true
        }
        if (selectedCategories.length >= 5) return false
        set({ selectedCategories: [...selectedCategories, id] })
        return true
      },

      setNarrowMainCategory: (id) =>
        set({ narrowMainCategory: id, selectedSubCategories: [] }),

      toggleSubCategory: (id) => {
        const { selectedSubCategories } = get()
        if (selectedSubCategories.includes(id)) {
          set({
            selectedSubCategories: selectedSubCategories.filter((c) => c !== id),
          })
        } else {
          set({ selectedSubCategories: [...selectedSubCategories, id] })
        }
      },

      setCompleted: (val) => set({ isCompleted: val }),

      reset: () =>
        set({
          userType: null,
          selectedCategories: [],
          narrowMainCategory: null,
          selectedSubCategories: [],
          isCompleted: false,
        }),
    }),
    { name: 'annoying-cap-onboarding' }
  )
)
