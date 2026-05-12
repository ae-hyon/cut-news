'use client'

import { motion } from 'motion/react'
import type { NewsItem } from '@/types'

interface NewsBlockProps {
  news: NewsItem
  index: number
  onClick: (id: string) => void
}

const sizeStyles = {
  large: 'row-span-2 min-h-[220px]',
  medium: 'min-h-[160px]',
  small: 'min-h-[120px]',
}

const titleStyles = {
  large: 'text-lg font-bold leading-snug',
  medium: 'text-base font-bold leading-snug',
  small: 'text-sm font-bold leading-snug',
}

export default function NewsBlock({ news, index, onClick }: NewsBlockProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(news.id)}
      className={`${sizeStyles[news.blockSize]} w-full text-left p-5 rounded-lg border border-border-default bg-bg-card hover:border-text-tertiary transition-colors duration-200 flex flex-col justify-between group break-inside-avoid mb-3`}
    >
      <div>
        <span className="text-accent text-[10px] font-bold uppercase tracking-widest">
          {news.category}
        </span>
        <h3
          className={`${titleStyles[news.blockSize]} mt-2 group-hover:text-accent transition-colors duration-200`}
        >
          {news.title}
        </h3>
        {news.blockSize !== 'small' && (
          <p className="text-text-secondary text-xs mt-2 leading-relaxed line-clamp-3">
            {news.summary}
          </p>
        )}
      </div>
      <p className="text-text-tertiary text-[10px] mt-3">{news.publishedAt}</p>
    </motion.button>
  )
}
