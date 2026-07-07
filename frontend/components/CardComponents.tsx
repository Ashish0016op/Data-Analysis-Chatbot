'use client'

import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatsCardProps {
  label: string
  value: string | number
  unit?: string
  change?: number
  icon?: ReactNode
  className?: string
}

export function StatsCard({ label, value, unit = '', change, icon, className = '' }: StatsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`glass-card p-5 ${className}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">{label}</p>
          <div className="flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-foreground">{value}</span>
            {unit && <span className="text-sm text-primary font-semibold">{unit}</span>}
          </div>
        </div>
        {icon && <div className="text-2xl opacity-60">{icon}</div>}
      </div>

      {change !== undefined && (
        <div className={`flex items-center space-x-1 text-xs font-medium ${change >= 0 ? 'text-primary' : 'text-accent'}`}>
          {change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span>{Math.abs(change)}%</span>
        </div>
      )}
    </motion.div>
  )
}

interface AnalyticsCardProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  actionButton?: { label: string; onClick: () => void }
}

export function AnalyticsCard({ title, subtitle, children, className = '', actionButton }: AnalyticsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`glass-card-hover p-6 ${className}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        {actionButton && (
          <button
            onClick={actionButton.onClick}
            className="px-3 py-1 text-xs font-medium rounded-lg bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 transition-colors"
          >
            {actionButton.label}
          </button>
        )}
      </div>
      <div>{children}</div>
    </motion.div>
  )
}

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card p-12 text-center space-y-4"
    >
      {icon && <div className="text-4xl opacity-40 mx-auto">{icon}</div>}
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 rounded-lg bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 transition-colors text-sm font-medium"
        >
          {action.label}
        </button>
      )}
    </motion.div>
  )
}

interface LoadingSkeletonProps {
  count?: number
}

export function LoadingSkeleton({ count = 1 }: LoadingSkeletonProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="glass-card p-6 h-32 rounded-xl"
        />
      ))}
    </div>
  )
}
