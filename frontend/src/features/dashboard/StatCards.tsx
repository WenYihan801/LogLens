import { cx } from "../../lib/cx";
import { formatNumber } from "../../lib/format";
import type { DashboardSummary } from "../../types/api";

function Stat({ label, value, tone = "slate", hint }: { label: string; value: number; tone?: string; hint?: string }) {
  const tones: Record<string, string> = {
    slate: "text-slate-900",
    red: "text-red-600",
    amber: "text-amber-600",
    sky: "text-sky-600",
    rose: "text-rose-600",
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={cx("mt-1 text-2xl font-semibold tabular-nums", tones[tone])} data-testid={`stat-${label}`}>
        {formatNumber(value)}
      </div>
      {hint && <div className="text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export function StatCards({ s }: { s: DashboardSummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
      <Stat label="Log events" value={s.total_events} />
      <Stat label="Alerts" value={s.total_alerts} />
      <Stat label="High" value={s.high_alerts} tone="red" />
      <Stat label="Medium" value={s.medium_alerts} tone="amber" />
      <Stat label="Low" value={s.low_alerts} tone="sky" />
      <Stat label="Open" value={s.open_alerts} tone="rose" hint="needs review" />
      <Stat label="Source IPs" value={s.unique_source_ips} hint="distinct" />
    </div>
  );
}
