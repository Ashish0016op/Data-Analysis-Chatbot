'use client'

import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'

interface ExportCardProps {
  icon: LucideIcon
  title: string
  description: string
  format: string
  onExport?: () => void
}

export function ExportCard({ icon: Icon, title, description, format, onExport }: ExportCardProps) {
  return (
    <motion.button
      whileHover={{ y: -4 }}
      onClick={onExport}
      className="glass-card-hover p-5 text-left w-full group flex flex-col gap-4"
    >
      <div className="flex items-center justify-between">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
          <Icon size={18} />
        </div>
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground border border-white/10 px-2 py-0.5 rounded">
          {format}
        </span>
      </div>
      <div className="space-y-1">
        <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors">
          {title}
        </h4>
        <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      </div>
      <span className="text-xs text-primary font-semibold mt-auto">Export →</span>
    </motion.button>
  )
}
