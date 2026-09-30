import React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StepperStep {
  id: string | number;
  label: string;
  description?: string;
}

export interface StepperProps {
  steps: StepperStep[];
  currentStep: number; // 0-indexed
  onStepClick?: (stepIndex: number) => void;
  className?: string;
}

export function Stepper({
  steps,
  currentStep,
  onStepClick,
  className,
}: StepperProps) {
  return (
    <nav aria-label="Progress" className={cn("w-full py-2", className)}>
      <ol className="flex items-center justify-between w-full">
        {steps.map((step, idx) => {
          const isCompleted = idx < currentStep;
          const isCurrent = idx === currentStep;
          const isClickable = !!onStepClick && idx <= currentStep;

          return (
            <li
              key={step.id}
              className={cn(
                "relative flex-1 flex flex-col items-center",
                idx !== steps.length - 1 &&
                  "after:content-[''] after:w-full after:h-0.5 after:border-b-2 after:inline-block after:absolute after:top-4 after:left-1/2 after:-translate-y-1/2 after:z-0",
                isCompleted
                  ? "after:border-primary"
                  : "after:border-border"
              )}
            >
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => onStepClick && onStepClick(idx)}
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "relative z-10 flex items-center justify-center h-9 w-9 rounded-full font-bold text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  isCompleted &&
                    "bg-primary text-white shadow-green-sm",
                  isCurrent &&
                    "bg-white border-2 border-primary text-primary-dark shadow-card font-extrabold ring-4 ring-primary-light",
                  !isCompleted &&
                    !isCurrent &&
                    "bg-surface-soft border border-border text-text-muted"
                )}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4 stroke-[3]" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </button>

              <span
                className={cn(
                  "mt-2 text-xs font-semibold text-center select-none truncate max-w-[80px] sm:max-w-none",
                  isCurrent ? "text-primary-dark font-bold" : "text-text-muted"
                )}
              >
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
