import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "./cx";

export type ButtonVariant = "primary" | "secondary" | "quiet";
export type ButtonSize = "md" | "lg";

// Primary: teal fill with the canvas color as text, 10.29:1. Never white on
// the legacy #0D9488 fill (3.74:1). Secondary is outlined with the Slate
// control border (3:1 or better); quiet is text only. Every size is at least
// 44px tall.
export const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-teal text-bg font-semibold hover:brightness-110",
  secondary: "border border-control bg-transparent text-fg hover:border-teal/60",
  quiet: "text-muted hover:text-fg underline-offset-4 hover:underline",
};

const SIZES: Record<ButtonSize, string> = {
  md: "min-h-11 px-4 text-small",
  lg: "min-h-12 px-6 text-body",
};

export function buttonClasses(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className?: string,
) {
  return cx(
    "inline-flex items-center justify-center gap-2 rounded-control font-medium transition-[filter,border-color,color] duration-150 disabled:cursor-not-allowed disabled:opacity-60",
    BUTTON_VARIANTS[variant],
    SIZES[size],
    className,
  );
}

type Common = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
};

type AsLink = Common & { href: string; type?: never };
type AsButton = Common & { href?: undefined } & Omit<
    ButtonHTMLAttributes<HTMLButtonElement>,
    "className" | "children"
  >;

export type ButtonProps = AsLink | AsButton;

export default function Button(props: ButtonProps) {
  if (typeof props.href === "string") {
    const { href, variant, size, className, children } = props;
    const cls = buttonClasses(variant, size, className);
    const external = /^(https?:|mailto:|tel:)/.test(href);
    return external ? (
      <a href={href} className={cls}>
        {children}
      </a>
    ) : (
      <Link href={href} className={cls}>
        {children}
      </Link>
    );
  }
  const { variant, size, className, children, ...rest } = props;
  return (
    <button type="button" {...rest} className={buttonClasses(variant, size, className)}>
      {children}
    </button>
  );
}
