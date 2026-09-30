"use client";

import React, { forwardRef } from "react";
import { Button, type ButtonProps } from "./Button";
import { cn } from "@/lib/utils";

export interface IconButtonProps extends Omit<ButtonProps, "leftIcon" | "rightIcon"> {
  "aria-label": string;
  icon: React.ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, icon, "aria-label": ariaLabel, size = "icon", ...props }, ref) => {
    return (
      <Button
        ref={ref}
        size={size}
        aria-label={ariaLabel}
        className={cn("p-0 inline-flex items-center justify-center", className)}
        {...props}
      >
        {icon}
      </Button>
    );
  }
);

IconButton.displayName = "IconButton";
