'use client'

import Toast from '@/components/Toast'

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-dvh flex flex-col px-6 py-8">
      <Toast />
      {children}
    </div>
  )
}
