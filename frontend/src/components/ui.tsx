import { useEffect, type ReactNode } from "react";

import { cx } from "../lib/cx";
import { ApiError } from "../services/api";
import type { AlertStatus, Severity } from "../types/api";

export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 px-5 py-3">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-800">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
const variants: Record<ButtonVariant, string> = {
  primary: "bg-sky-600 text-white hover:bg-sky-700 disabled:bg-sky-300",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400",
  danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50 disabled:text-red-300",
  ghost: "text-slate-600 hover:bg-slate-100 disabled:text-slate-300",
};

export function Button({
  variant = "secondary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type="button"
      {...props}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed",
        variants[variant],
        className,
      )}
    />
  );
}

export function LinkButton({ href, children, variant = "secondary" }: { href: string; children: ReactNode; variant?: ButtonVariant }) {
  return (
    <a
      href={href}
      className={cx(
        "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
        variants[variant],
      )}
    >
      {children}
    </a>
  );
}

const severityStyle: Record<Severity, string> = {
  HIGH: "bg-red-50 text-red-700 ring-red-600/20",
  MEDIUM: "bg-amber-50 text-amber-800 ring-amber-600/20",
  LOW: "bg-sky-50 text-sky-700 ring-sky-600/20",
};

const statusStyle: Record<AlertStatus, string> = {
  OPEN: "bg-rose-50 text-rose-700 ring-rose-600/20",
  ACKNOWLEDGED: "bg-violet-50 text-violet-700 ring-violet-600/20",
  RESOLVED: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
};

function Pill({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset", className)}>
      {children}
    </span>
  );
}

export const SeverityBadge = ({ severity }: { severity: Severity }) => (
  <Pill className={severityStyle[severity]}>{severity}</Pill>
);
export const StatusBadge = ({ status }: { status: AlertStatus }) => (
  <Pill className={statusStyle[status]}>{status}</Pill>
);
export const NeutralBadge = ({ children }: { children: ReactNode }) => (
  <Pill className="bg-slate-50 text-slate-700 ring-slate-500/20">{children}</Pill>
);

export function HttpStatus({ code }: { code: number | null }) {
  if (code == null) return <span className="text-slate-400">—</span>;
  const c =
    code >= 500 ? "text-red-700" : code >= 400 ? "text-amber-700" : code >= 300 ? "text-sky-700" : "text-emerald-700";
  return <span className={cx("font-mono text-xs font-semibold", c)}>{code}</span>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-sky-600" />
      {label}
    </div>
  );
}

export function ErrorMessage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  const code = error instanceof ApiError ? error.code : undefined;
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <p className="font-medium">{msg}</p>
      <div className="mt-1 flex items-center gap-3 text-xs text-red-700">
        {code && <span className="font-mono">{code}</span>}
        {onRetry && (
          <button type="button" onClick={onRetry} className="font-medium underline">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, children, icon = "◎" }: { title: string; children?: ReactNode; icon?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center">
      <div className="text-3xl text-slate-300" aria-hidden>
        {icon}
      </div>
      <p className="mt-2 text-sm font-medium text-slate-700">{title}</p>
      {children && <div className="mt-2 max-w-md text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  pageSize,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-4 pt-4 text-sm text-slate-600">
      <span>
        {from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()}
      </span>
      <div className="flex items-center gap-2">
        <Button onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
          ← Prev
        </Button>
        <span className="tabular-nums">
          Page {page} / {pages}
        </span>
        <Button onClick={() => onPage(page + 1)} disabled={page >= pages} aria-label="Next page">
          Next →
        </Button>
      </div>
    </nav>
  );
}

export function Drawer({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" aria-label="Close" className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <div className="relative z-10 flex h-full w-full max-w-2xl flex-col bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-800">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close panel">
            ✕
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}

/** Untrusted log text: always rendered as a text node inside <pre> (NFR-06). */
export function RawLog({ text }: { text: string }) {
  return (
    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-100">
      {text}
    </pre>
  );
}

export function Field({ label, children, htmlFor }: { label: string; children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="flex flex-col gap-1 text-xs font-medium text-slate-600">
      {label}
      {children}
    </label>
  );
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
      {items.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-slate-500">{k}</dt>
          <dd className="break-words text-slate-800 [overflow-wrap:anywhere]">{v ?? <span className="text-slate-400">—</span>}</dd>
        </div>
      ))}
    </dl>
  );
}
