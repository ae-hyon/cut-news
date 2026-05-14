'use client'

import Toast from '@/components/Toast'

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{
        background:
          'radial-gradient(ellipse at 46% 8%, rgba(86,44,17,1) 0%, rgba(51,30,17,1) 25%, rgba(34,23,16,1) 45%, rgba(16,16,16,1) 70%)',
      }}
    >
      <Toast />
      {children}
    </div>
  )
}
