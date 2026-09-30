"use client";

import React, { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center font-medium rounded-btn transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none touch-target select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-white hover:bg-primary-dark shadow-green-sm active:translate-y-px",
        secondary:
          "bg-white border border-border text-primary-dark hover:bg-surface-soft hover:border-primary",
        outline:
          "bg-transparent border-2 border-primary text-primary hover:bg-primary-light",
        ghost:
          "bg-transparent text-text hover:bg-surface-soft hover:text-primary-dark",
        danger:
          "bg-status-risk text-white hover:bg-red-700 active:translate-y-px",
      },
      size: {
        sm: "h-10 px-3 text-sm rounded-md",
        md: "h-12 px-5 text-base rounded-btn min-h-[48px]",
        lg: "h-14 px-8 text-lg rounded-btn min-h-[52px]",
        icon: "h-12 w-12 rounded-btn min-h-[48px] min-w-[48px] p-0",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
      fullWidth: false,
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      isLoading,
      disabled,
      leftIcon,
      rightIcon,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(buttonVariants({ variant, size, fullWidth, className }))}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-current" />
        ) : (
          leftIcon && <span className="mr-2.5 inline-flex">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && (
          <span className="ml-2.5 inline-flex">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
