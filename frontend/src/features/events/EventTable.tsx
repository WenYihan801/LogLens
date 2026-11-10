import { HttpStatus, NeutralBadge } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import type { LogEvent } from "../../types/api";

export function EventTable({ events, onSelect }: { events: LogEvent[]; onSelect?: (e: LogEvent) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="py-2 pr-4 font-medium">Time</th>
            <th className="py-2 pr-4 font-medium">Source IP</th>
            <th className="py-2 pr-4 font-medium">Source</th>
            <th className="py-2 pr-4 font-medium">Method</th>
            <th className="py-2 pr-4 font-medium">Path / user</th>
            <th className="py-2 pr-4 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {events.map((e) => (
            <tr
              key={e.id}
              className={onSelect ? "cursor-pointer hover:bg-slate-50" : undefined}
              onClick={onSelect ? () => onSelect(e) : undefined}
            >
              <td className="whitespace-nowrap py-2 pr-4 text-slate-600">{formatDateTime(e.event_timestamp)}</td>
              <td className="py-2 pr-4 font-mono text-xs">{e.source_ip ?? "—"}</td>
              <td className="py-2 pr-4">
                <NeutralBadge>{e.source_type}</NeutralBadge>
              </td>
              <td className="py-2 pr-4 font-mono text-xs">{e.http_method ?? "—"}</td>
              <td className="max-w-md truncate py-2 pr-4 font-mono text-xs" title={e.request_path ?? e.username ?? ""}>
                {e.request_path ?? (e.username ? `user: ${e.username}` : "—")}
              </td>
              <td className="py-2 pr-4">
                {e.source_type === "SSH" ? (
                  <span
                    className={
                      e.auth_result === "SUCCESS" ? "text-xs font-semibold text-emerald-700" : "text-xs font-semibold text-amber-700"
                    }
                  >
                    {e.auth_result}
                  </span>
                ) : (
                  <HttpStatus code={e.status_code} />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
