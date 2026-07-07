'use client'

import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'

interface ReportCardProps {
  icon: LucideIcon
  title: string
  summary: string
  metrics?: { label: string; value: string }[]
  children?: ReactNode
  accent?: 'primary' | 'secondary' | 'accent'
}

const accentMap = {
  primary: 'from-primary/20 to-primary/0 border-primary/30 text-primary',
  secondary: 'from-secondary/20 to-secondary/0 border-secondary/30 text-secondary',
  accent: 'from-accent/20 to-accent/0 border-accent/30 text-accent',
}

export function ReportCard({
  icon: Icon,
  title,
  summary,
  metrics,
  children,
  accent = 'primary',
}: ReportCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 space-y-4"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`w-11 h-11 rounded-xl bg-gradient-to-br border flex items-center justify-center ${accentMap[accent]}`}
          >
            <Icon size={20} />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">{title}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{summary}</p>
          </div>
        </div>
      </div>
      {metrics && metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-3 pt-2">
          {metrics.map((m) => (
            <div key={m.label} className="rounded-lg bg-white/5 border border-white/10 p-3">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
                {m.label}
              </p>
              <p className="text-lg font-bold text-foreground mt-1">{m.value}</p>
            </div>
          ))}
        </div>
      )}
      {children}
    </motion.div>
  )
}
