import React from 'react'

interface SectionHeaderProps {
  label?: string
  title: string
  index?: number
}

export default function SectionHeader({ label, title, index }: SectionHeaderProps) {
  return (
    <div className="section-header">
      <div>
        {label && <p className="mini-label">{label}</p>}
        <h3>{title}</h3>
      </div>
      {index !== undefined && <span className="block-index">0{index + 1}</span>}
    </div>
  )
}
