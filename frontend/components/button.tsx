import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  compact?: boolean;
};

export function PrimaryButton({
  children,
  className = "",
  compact = false,
  ...props
}: Props) {
  return (
    <button
      className={`primary-button group ${compact ? "primary-button-compact" : ""} ${className}`}
      {...props}
    >
      <span className="primary-glow" />
      <span className="primary-surface" />
      <span className="primary-highlight" />
      <span className="relative z-10 inline-flex items-center justify-center gap-2">
        {children}
      </span>
    </button>
  );
}

export function SecondaryButton({
  children,
  className = "",
  compact = false,
  ...props
}: Props) {
  return (
    <button
      className={`secondary-button ${compact ? "secondary-button-compact" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
