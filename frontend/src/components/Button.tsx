import { clsx } from "clsx";
import { ButtonHTMLAttributes } from "react";

type Variant = "lost" | "found" | "neutral";

export function Button({
  variant = "neutral",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={clsx(
        "rounded-lg px-4 py-2.5 font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50",
        variant === "lost" && "bg-lost text-white hover:bg-lost-dark focus-visible:ring-lost",
        variant === "found" && "bg-found text-white hover:bg-found-dark focus-visible:ring-found",
        variant === "neutral" && "bg-slate-900 text-white hover:bg-slate-700 focus-visible:ring-slate-900",
        className
      )}
      {...props}
    />
  );
}
