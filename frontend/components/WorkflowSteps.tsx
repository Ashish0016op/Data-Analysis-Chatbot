'use client'

import { motion } from 'framer-motion'
import { Check, ChevronRight, LucideIcon } from 'lucide-react'

export interface WorkflowStep {
  id: string
  label: string
  description: string
  icon: LucideIcon
  status: 'completed' | 'active' | 'pending'
}

interface WorkflowStepsProps {
  steps: WorkflowStep[]
}

export function WorkflowSteps({ steps }: WorkflowStepsProps) {
  return (
    <div className="glass-card p-6">
      <div className="flex flex-col lg:flex-row lg:items-stretch gap-3 lg:gap-2">
        {steps.map((step, idx) => {
          const Icon = step.icon
          const isLast = idx === steps.length - 1
          const colors =
            step.status === 'completed'
              ? 'border-primary/40 bg-primary/10 text-primary'
              : step.status === 'active'
                ? 'border-secondary/50 bg-secondary/10 text-secondary'
                : 'border-white/10 bg-white/[0.02] text-muted-foreground'

          return (
            <div key={step.id} className="flex-1 flex items-center gap-2">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.06 }}
                className={`flex-1 rounded-xl border p-4 transition-colors ${colors}`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center bg-background/40 border ${
                      step.status === 'pending'
                        ? 'border-white/10'
                        : 'border-current'
                    }`}
                  >
                    {step.status === 'completed' ? <Check size={16} /> : <Icon size={16} />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">
                      {step.label}
                    </p>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {step.description}
                    </p>
                  </div>
                </div>
              </motion.div>
              {!isLast && (
                <ChevronRight
                  size={18}
                  className="hidden lg:block text-muted-foreground shrink-0"
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
