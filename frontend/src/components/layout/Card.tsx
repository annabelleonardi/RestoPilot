import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export default function Card({ title, subtitle, children, className }: CardProps) {
  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className ?? ""}`}
    >
      {(title || subtitle) && (
        <header className="mb-4">
          {title && <h3 className="text-sm font-semibold text-slate-800">{title}</h3>}
          {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
