import type { ReactNode } from "react";

export function PageHeader({ title, description }: { title: string; description?: ReactNode }) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {description && <p className="mt-1 text-muted">{description}</p>}
    </div>
  );
}
