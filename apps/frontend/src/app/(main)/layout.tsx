'use client'

import Header from '@/components/Header'
import TabBar from '@/components/TabBar'
import Toast from '@/components/Toast'

export default function MainLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-dvh flex flex-col max-w-lg mx-auto">
      <Toast />
      <Header userName="선우" />
      <main className="flex-1 pb-[72px]">{children}</main>
      <TabBar />
    </div>
  )
}
