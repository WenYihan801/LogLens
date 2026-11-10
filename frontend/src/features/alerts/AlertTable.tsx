import { Link } from "react-router-dom";

import { SeverityBadge, StatusBadge } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import type { Alert } from "../../types/api";

export function AlertTable({ alerts, compact = false }: { alerts: Alert[]; compact?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="py-2 pr-4 font-medium">Severity</th>
            <th className="py-2 pr-4 font-medium">Rule</th>
            <th className="py-2 pr-4 font-medium">Source IP</th>
            <th className="py-2 pr-4 text-right font-medium">Hits</th>
            <th className="py-2 pr-4 font-medium">First seen</th>
            {!compact && <th className="py-2 pr-4 font-medium">Last seen</th>}
            <th className="py-2 pr-4 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {alerts.map((a) => (
            <tr key={a.id} className="hover:bg-slate-50">
              <td className="py-2 pr-4">
                <SeverityBadge severity={a.severity} />
              </td>
              <td className="py-2 pr-4">
                <Link to={`/alerts/${a.id}`} className="font-medium text-sky-700 hover:underline">
                  {a.rule_name}
                </Link>
                <div className="font-mono text-[11px] text-slate-400">{a.rule_code}</div>
              </td>
              <td className="py-2 pr-4 font-mono text-xs">{a.source_ip}</td>
              <td className="py-2 pr-4 text-right tabular-nums">{a.occurrence_count}</td>
              <td className="whitespace-nowrap py-2 pr-4 text-slate-600">{formatDateTime(a.first_seen)}</td>
              {!compact && <td className="whitespace-nowrap py-2 pr-4 text-slate-600">{formatDateTime(a.last_seen)}</td>}
              <td className="py-2 pr-4">
                <StatusBadge status={a.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
