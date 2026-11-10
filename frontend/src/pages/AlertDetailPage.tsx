import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Card, Drawer, ErrorMessage, HttpStatus, KeyValue, LinkButton, NeutralBadge, PageHeader, RawLog, SeverityBadge, Spinner, StatusBadge } from "../components/ui";
import { Notes, StatusControl } from "../features/alerts/AlertActions";
import { EventDetailPanel } from "../features/events/EventDetailPanel";
import { useAsync } from "../hooks/useAsync";
import { formatDateTime, formatDuration } from "../lib/format";
import { api } from "../services/api";

export function AlertDetailPage() {
  const { id = "" } = useParams();
  const { data: a, error, loading, reload } = useAsync(() => api.alert(id), [id]);
  const [eventId, setEventId] = useState<number>();

  if (loading && !a) return <Spinner />;
  if (error)
    return (
      <div className="space-y-4">
        <ErrorMessage error={error} onRetry={reload} />
        <Link to="/alerts" className="text-sm font-medium text-sky-700 hover:underline">
          ← Back to alerts
        </Link>
      </div>
    );
  if (!a) return null;

  return (
    <>
      <div className="mb-3">
        <Link to={`/alerts?dataset=${a.dataset_id}`} className="text-sm font-medium text-sky-700 hover:underline">
          ← Alerts
        </Link>
      </div>
      <PageHeader
        title={a.rule_name}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={a.severity} />
            <StatusBadge status={a.status} />
            <span className="font-mono text-xs text-slate-500">{a.rule_code}</span>
            <span className="text-slate-400">·</span>
            <span>source</span>
            <span className="font-mono text-slate-700">{a.source_ip}</span>
          </span>
        }
        actions={<LinkButton href={api.alertsJsonUrl({ dataset_id: a.dataset_id, source_ip: a.source_ip ?? undefined, rule_code: a.rule_code })}>⬇ Export JSON</LinkButton>}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Why this alert fired">
            <p className="text-sm leading-relaxed text-slate-700">{a.explanation}</p>
            <div className="mt-4 rounded-lg bg-slate-50 p-4">
              <KeyValue
                items={[
                  ["Rule", `${a.rule.name} (v${a.rule.version})`],
                  ["Condition", `≥ ${a.rule.threshold} matching events from one IP within ${formatDuration(a.rule.window_seconds)}`],
                  ["Rule description", a.rule.description],
                  ["Observed", `${a.occurrence_count} events over ${formatDuration(a.observed_window_seconds)}`],
                  ["First seen", formatDateTime(a.first_seen)],
                  ["Last seen", formatDateTime(a.last_seen)],
                ]}
              />
            </div>
          </Card>

          <Card
            title="Evidence"
            subtitle={`${a.evidence_total} log events linked to this alert${a.evidence_total > a.evidence.length ? ` (showing first ${a.evidence.length})` : ""} · click a row for full details`}
          >
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="border-b border-slate-200 uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2 pr-3 font-medium">#</th>
                    <th className="py-2 pr-3 font-medium">Time</th>
                    <th className="py-2 pr-3 font-medium">Detail</th>
                    <th className="py-2 pr-3 font-medium">Result</th>
                    <th className="py-2 pr-3 font-medium">Line</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {a.evidence.map((e, i) => (
                    <tr key={e.id} className="cursor-pointer align-top hover:bg-slate-50" onClick={() => setEventId(e.id)}>
                      <td className="py-1.5 pr-3 tabular-nums text-slate-400">{i + 1}</td>
                      <td className="whitespace-nowrap py-1.5 pr-3 text-slate-600">{formatDateTime(e.event_timestamp)}</td>
                      <td className="max-w-md py-1.5 pr-3 font-mono">
                        <div className="truncate" title={e.raw_message}>
                          {e.request_path ? `${e.http_method ?? ""} ${e.request_path}` : e.username ? `user ${e.username}` : e.raw_message}
                        </div>
                      </td>
                      <td className="py-1.5 pr-3">
                        {e.source_type === "SSH" ? <NeutralBadge>{e.auth_result}</NeutralBadge> : <HttpStatus code={e.status_code} />}
                      </td>
                      <td className="py-1.5 pr-3 tabular-nums text-slate-500">{e.line_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {a.evidence[0] && (
              <div className="mt-4">
                <div className="mb-1 text-xs font-medium text-slate-500">First evidence line (raw)</div>
                <RawLog text={a.evidence[0].raw_message} />
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Triage">
            <StatusControl alertId={a.id} status={a.status} onChanged={reload} />
            <div className="mt-4 text-xs text-slate-500">
              Created {formatDateTime(a.created_at)}
              <br />
              Last modified {formatDateTime(a.updated_at)}
            </div>
          </Card>
          <Card title="Investigation notes">
            <Notes alertId={a.id} notes={a.notes} onAdded={reload} />
          </Card>
          <Card title="Context">
            <KeyValue
              items={[
                ["Dataset", <Link key="d" className="text-sky-700 hover:underline" to={`/?dataset=${a.dataset_id}`}>{a.dataset_name}</Link>],
                [
                  "All events from IP",
                  <Link
                    key="e"
                    className="text-sky-700 hover:underline"
                    to={`/events?dataset=${a.dataset_id}&source_ip=${encodeURIComponent(a.source_ip ?? "")}`}
                  >
                    Open in Events →
                  </Link>,
                ],
              ]}
            />
          </Card>
        </div>
      </div>

      <Drawer open={eventId !== undefined} onClose={() => setEventId(undefined)} title={`Event #${eventId ?? ""}`}>
        {eventId !== undefined && <EventDetailPanel id={eventId} />}
      </Drawer>
    </>
  );
}
