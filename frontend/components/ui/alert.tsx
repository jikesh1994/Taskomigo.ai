import { clsx } from "clsx";
import type { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  info: "border-primary/25 bg-primary-soft text-fg",
  success: "border-success/30 bg-success-soft text-fg",
  warning: "border-warning/30 bg-warning-soft text-fg",
  danger: "border-danger/30 bg-danger-soft text-fg",
};

interface AlertProps {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export function Alert({ tone = "info", title, children, className }: AlertProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={clsx("rounded-lg border px-4 py-3 text-sm", tones[tone], className)}
    >
      {title && <p className="font-medium">{title}</p>}
      {children && <div className={clsx(title && "mt-1", "text-muted")}>{children}</div>}
    </div>
  );
}
