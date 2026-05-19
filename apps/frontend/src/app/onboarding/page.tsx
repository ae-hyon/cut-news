'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useOnboardingStore } from '@/stores/onboarding';
import type { UserType } from '@/types';
import OnboardingHeader from './_components/OnboardingHeader';
import OnboardingGuide from './_components/OnboardingGuide';
import OnboardingProgress from './_components/OnboardingProgress';

function WideIcon() {
  return (
    <svg
      width="50"
      height="32"
      viewBox="0 0 50 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="opacity-80"
    >
      <rect x="5" y="9" width="3" height="14" rx="2" fill="#FFE5D4" />
      <rect x="43" y="9" width="3" height="14" rx="2" fill="#FFE5D4" />
      <rect x="6" y="14.5" width="38" height="3" fill="#FFE5D4" />
    </svg>
  );
}

function NarrowIcon() {
  return (
    <svg
      width="50"
      height="32"
      viewBox="0 0 40 27"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="opacity-80"
    >
      <path
        d="M0 21.0937C0 20.1618 0.75552 19.4062 1.6875 19.4062H5.90625C6.83823 19.4062 7.59375 20.1618 7.59375 21.0938V25.3125C7.59375 26.2445 6.83823 27 5.90625 27H1.6875C0.755519 27 0 26.2445 0 25.3125V21.0937Z"
        fill="#FFE5D4"
      />
      <path
        d="M16.0312 21.0937C16.0312 20.1618 16.7868 19.4062 17.7188 19.4062H21.9375C22.8695 19.4062 23.625 20.1618 23.625 21.0938V25.3125C23.625 26.2445 22.8695 27 21.9375 27H17.7187C16.7868 27 16.0312 26.2445 16.0312 25.3125V21.0937Z"
        fill="#FFE5D4"
      />
      <path
        d="M16.0312 1.6875C16.0312 0.755519 16.7868 0 17.7188 0H21.9375C22.8695 0 23.625 0.75552 23.625 1.6875V5.90625C23.625 6.83823 22.8695 7.59375 21.9375 7.59375H17.7187C16.7868 7.59375 16.0312 6.83823 16.0312 5.90625V1.6875Z"
        fill="#FFE5D4"
      />
      <path
        d="M32.0625 21.0937C32.0625 20.1618 32.818 19.4062 33.75 19.4062H37.9688C38.9007 19.4062 39.6562 20.1618 39.6562 21.0938V25.3125C39.6562 26.2445 38.9007 27 37.9688 27H33.75C32.818 27 32.0625 26.2445 32.0625 25.3125V21.0937Z"
        fill="#FFE5D4"
      />
      <path
        d="M20.625 12.7031H32.4844C34.7884 12.7031 36.6562 14.5709 36.6562 16.875V24H35.0625V16.875C35.0625 15.4511 33.9082 14.2969 32.4844 14.2969H20.625V23.1562H19.0312V14.2969H7.17188C5.74802 14.2969 4.59375 15.4511 4.59375 16.875V21.4688H3V16.875C3 14.5709 4.86781 12.7031 7.17188 12.7031H19.0312V6.375H20.625V12.7031Z"
        fill="#FFE5D4"
      />
    </svg>
  );
}

function CheckIcon({ checked }: { checked: boolean }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`transition-opacity duration-200 ${checked ? 'opacity-100' : 'opacity-50'}`}
    >
      <path
        d="M5 12.5L9.5 17L19 7"
        stroke={checked ? '#f3782b' : '#ffffff'}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function OnboardingStep1() {
  const router = useRouter();
  const { userType, setUserType } = useOnboardingStore();

  const handleNext = () => {
    if (!userType) return;
    router.push(
      userType === 'wide' ? '/onboarding/wide' : '/onboarding/narrow',
    );
  };

  return (
    <>
      <OnboardingHeader />

      <div className="flex flex-1 flex-col justify-between px-5 pt-6 pb-10">
        <div className="flex flex-col gap-6 pt-4">
          <OnboardingGuide />
          <OnboardingProgress step={1} label="시작" />

          {/* Type cards */}
          <div className="flex gap-4 pt-6">
            <TypeCard
              type="wide"
              selected={userType === 'wide'}
              onSelect={setUserType}
              icon={<WideIcon />}
              title="Wide"
              description={
                <>
                  여러 카테고리를
                  <br />
                  모아보고 싶어요
                </>
              }
              delay={0.25}
            />
            <TypeCard
              type="narrow"
              selected={userType === 'narrow'}
              onSelect={setUserType}
              icon={<NarrowIcon />}
              title="Narrow"
              description={
                <>
                  하나 카테고리를
                  <br />
                  깊게 보고 싶어요
                </>
              }
              delay={0.35}
            />
          </div>
        </div>

        {/* Next button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45 }}
          className="mt-8"
        >
          <button
            onClick={handleNext}
            disabled={!userType}
            className={`w-full py-5 rounded-[24px] text-[18px] font-bold text-white text-center transition-all duration-200 ${
              userType
                ? 'bg-gradient-to-r from-[#f07426] to-[#f3782b]'
                : 'bg-[#414141] opacity-50 cursor-not-allowed'
            }`}
          >
            다음
          </button>
        </motion.div>
      </div>
    </>
  );
}

function TypeCard({
  type,
  selected,
  onSelect,
  icon,
  title,
  description,
  delay,
}: {
  type: UserType;
  selected: boolean;
  onSelect: (t: UserType) => void;
  icon: React.ReactNode;
  title: string;
  description: React.ReactNode;
  delay: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileTap={{ scale: 0.97 }}
      onClick={() => onSelect(type)}
      className={`relative flex-1 flex flex-col gap-4 justify-end h-[180px] rounded-[24px] border pl-4 pr-5 py-5 text-left overflow-hidden transition-all duration-200 ${
        selected
          ? 'bg-white/15 border-[#f3782b]'
          : 'bg-white/10 border-white/20'
      }`}
    >
      <div className="absolute top-[15px] right-[14px]">
        <CheckIcon checked={selected} />
      </div>
      <div className="h-8 w-[50px]">{icon}</div>
      <div className="flex flex-col gap-1.5 pl-1">
        <p className="text-[20px] font-bold text-[#f3782b] leading-[24px]">
          {title}
        </p>
        <p className="text-[16px] font-normal text-white leading-[24px]">
          {description}
        </p>
      </div>
    </motion.button>
  );
}
