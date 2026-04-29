'use client'

import { useEffect, useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'motion/react'

interface ToastMessage {
  id: number
  text: string
}

let toastId = 0
let addToastFn: ((text: string) => void) | null = null

export function showToast(text: string) {
  addToastFn?.(text)
}

export default function Toast() {
  const [messages, setMessages] = useState<ToastMessage[]>([])

  const addToast = useCallback((text: string) => {
    const id = ++toastId
    setMessages((prev) => [...prev, { id, text }])
    setTimeout(() => {
      setMessages((prev) => prev.filter((m) => m.id !== id))
    }, 2500)
  }, [])

  useEffect(() => {
    addToastFn = addToast
    return () => {
      addToastFn = null
    }
  }, [addToast])

  return (
    <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[1000] pointer-events-none">
      <AnimatePresence>
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            className="bg-bg-elevated border border-border-default text-text-primary px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap pointer-events-auto shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.25 }}
          >
            {msg.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
