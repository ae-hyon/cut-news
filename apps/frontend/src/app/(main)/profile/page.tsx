'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useAuthStore } from '@/stores/auth';
import { useCategories } from '@/hooks/useCategories';
import { updateUserPreference } from '@/services/authApi';
import { showToast } from '@/components/Toast';
import { MAX_WIDE_CATEGORIES } from '@/constants/categories';
import type { Category } from '@/types';

export default function ProfilePage() {
  const router = useRouter();
  const { session, logout, checkSession } = useAuthStore();
  console.log(session);
  const { categories } = useCategories();
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const preference = session?.preference;
  const isWide = preference?.mode === 'wide';

  // 편집용 로컬 상태
  const [editCategories, setEditCategories] = useState<string[]>([]);
  const [editSubCategories, setEditSubCategories] = useState<string[]>([]);
  const [editMainCategory, setEditMainCategory] = useState<string | null>(null);

  const startEditing = () => {
    if (!preference) return;
    if (isWide) {
      setEditCategories([...preference.primary_categories]);
    } else {
      setEditMainCategory(preference.primary_categories[0] ?? null);
      setEditSubCategories([...preference.subcategories]);
    }
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
  };

  const handleToggleCategory = (slug: string) => {
    if (isWide) {
      setEditCategories((prev) => {
        if (prev.includes(slug)) return prev.filter((c) => c !== slug);
        if (prev.length >= MAX_WIDE_CATEGORIES) {
          showToast(`대분류 ${MAX_WIDE_CATEGORIES}개까지만 선택 가능해요`);
          return prev;
        }
        return [...prev, slug];
      });
    } else {
      if (editMainCategory === slug) return;
      setEditMainCategory(slug);
      setEditSubCategories([]);
    }
  };

  const handleToggleSubCategory = (slug: string) => {
    setEditSubCategories((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug],
    );
  };

  const canSave = isWide
    ? editCategories.length >= 3
    : editMainCategory !== null && editSubCategories.length > 0;

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const payload = {
        mode: preference!.mode,
        primary_categories: isWide
          ? editCategories
          : editMainCategory
            ? [editMainCategory]
            : [],
        subcategories: isWide ? [] : editSubCategories,
      };
      await updateUserPreference(payload);
      await checkSession();
      setIsEditing(false);
      showToast('관심 카테고리가 업데이트되었어요');
    } catch {
      showToast('저장에 실패했어요. 다시 시도해주세요.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.replace('/onboarding');
  };

  if (!session || !preference) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 py-20">
        <p className="text-text-tertiary text-sm animate-pulse">로딩 중...</p>
      </div>
    );
  }

  // 카테고리 slug → name 매핑
  const resolveName = (slug: string): string =>
    categories.find((c) => c.id === slug)?.name ?? slug;

  const resolveSubName = (catSlug: string, subSlug: string): string => {
    const cat = categories.find((c) => c.id === catSlug);
    return cat?.subcategories?.find((s) => s.id === subSlug)?.name ?? subSlug;
  };

  const selectedMainCat: Category | undefined = isWide
    ? undefined
    : categories.find(
        (c) =>
          c.id ===
          (isEditing ? editMainCategory : preference.primary_categories[0]),
      );

  return (
    <div className="px-5 pt-6 pb-10">
      {/* 프로필 헤더 */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center py-6"
      >
        <div className="w-16 h-16 rounded-full bg-[#3c3c3c] border border-[#343434] flex items-center justify-center mb-3">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-text-secondary)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="8" r="4" />
            <path d="M20 21a8 8 0 10-16 0" />
          </svg>
        </div>
        <p className="text-white text-[16px] font-semibold">
          {session.auth_provider === 'kakao'
            ? '카카오 로그인'
            : session.auth_provider}
        </p>
        <p className="text-white/40 text-[12px] mt-1">
          {isWide ? 'Wide 모드' : 'Narrow 모드'}
        </p>
      </motion.div>

      {/* 관심 카테고리 섹션 */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-4"
      >
        <div className="flex items-center justify-between mb-3">
          <p className="text-white text-[14px] font-semibold">관심 카테고리</p>
          {!isEditing ? (
            <button
              onClick={startEditing}
              className="text-[#f3782b] text-[13px] font-medium"
            >
              편집
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={cancelEditing}
                className="text-white/50 text-[13px] font-medium"
              >
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={!canSave || saving}
                className="text-[#f3782b] text-[13px] font-medium disabled:opacity-40"
              >
                {saving ? '저장 중...' : '저장'}
              </button>
            </div>
          )}
        </div>

        {!isEditing ? (
          /* 보기 모드 */
          <div className="flex flex-wrap gap-2">
            {isWide
              ? preference.primary_categories.map((slug) => (
                  <span
                    key={slug}
                    className="px-3 py-1.5 rounded-full bg-[#f3782b]/15 text-[#f3782b] text-[13px] font-medium"
                  >
                    {resolveName(slug)}
                  </span>
                ))
              : (() => {
                  const mainSlug = preference.primary_categories[0];
                  return (
                    <>
                      <span className="px-3 py-1.5 rounded-full bg-[#f3782b] text-white text-[13px] font-medium">
                        {resolveName(mainSlug)}
                      </span>
                      {preference.subcategories.map((sub) => (
                        <span
                          key={sub}
                          className="px-3 py-1.5 rounded-full bg-[#f3782b]/15 text-[#f3782b] text-[13px] font-medium"
                        >
                          {resolveSubName(mainSlug, sub)}
                        </span>
                      ))}
                    </>
                  );
                })()}
          </div>
        ) : (
          /* 편집 모드 */
          <div className="flex flex-col gap-3">
            <p className="text-white/40 text-[12px]">
              {isWide
                ? `3~${MAX_WIDE_CATEGORIES}개 선택 (${editCategories.length}개 선택됨)`
                : '대분류 1개와 세부 관심사를 선택하세요'}
            </p>

            {/* 카테고리 그리드 */}
            <div className="grid grid-cols-2 gap-2">
              {categories.map((cat) => {
                const selected = isWide
                  ? editCategories.includes(cat.id)
                  : editMainCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => handleToggleCategory(cat.id)}
                    className={`flex flex-col gap-0.5 items-center justify-center h-[65px] rounded-[20px] px-1 py-5 text-center text-white transition-all duration-200 ${
                      selected
                        ? 'bg-[#f3782b]'
                        : 'bg-[#3c3c3c] border border-[#343434]'
                    }`}
                  >
                    <p className="font-bold text-[14px] leading-[17px]">
                      {cat.name}
                    </p>
                    <p className="font-normal text-[11px] leading-[13px] opacity-70 whitespace-pre-line">
                      {cat.description.replace(/ 등 /, '\n')}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Narrow 모드: 서브카테고리 */}
            {!isWide && selectedMainCat?.subcategories && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-1"
              >
                <p className="text-white/50 text-[12px] mb-2">
                  {selectedMainCat.name} 세부 관심사
                </p>
                <div className="flex flex-wrap gap-2">
                  {selectedMainCat.subcategories.map((sub) => {
                    const selected = editSubCategories.includes(sub.id);
                    return (
                      <button
                        key={sub.id}
                        onClick={() => handleToggleSubCategory(sub.id)}
                        className={`px-3 py-1.5 rounded-full text-[13px] font-medium transition-all duration-200 ${
                          selected
                            ? 'bg-[#f3782b] text-white'
                            : 'bg-white/10 text-white/70'
                        }`}
                      >
                        {sub.name}
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>
        )}
      </motion.div>

      {/* 로그아웃 */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-10"
      >
        <button
          onClick={handleLogout}
          className="w-full py-4 rounded-[20px] text-[14px] font-medium text-white/50 border border-white/10 transition-all duration-200 hover:border-white/20"
        >
          로그아웃
        </button>
      </motion.div>
    </div>
  );
}
