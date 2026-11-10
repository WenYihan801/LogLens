import { Link } from "react-router-dom";

import { ErrorMessage, HttpStatus, KeyValue, NeutralBadge, RawLog, Spinner } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime } from "../../lib/format";
import { api } from "../../services/api";

export function EventDetailPanel({ id }: { id: number }) {
  const { data: e, error, loading } = useAsync(() => api.event(id), [id]);
  if (loading && !e) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!e) return null;
  return (
    <div className="space-y-5">
      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-800">Raw log line</h3>
        <RawLog text={e.raw_message} />
        <p className="mt-1 text-xs text-slate-500">
          Line {e.line_number} of dataset <strong>{e.dataset_name}</strong>
        </p>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-800">Normalised fields</h3>
        <KeyValue
          items={[
            ["Event ID", e.id],
            ["Timestamp (local)", formatDateTime(e.event_timestamp)],
            ["Timestamp (UTC)", <span key="u" className="font-mono text-xs">{e.event_timestamp}</span>],
            ["Source type", <NeutralBadge key="s">{e.source_type}</NeutralBadge>],
            ["Source IP", e.source_ip && <span className="font-mono">{e.source_ip}</span>],
            ["HTTP method", e.http_method],
            ["Request path", e.request_path && <span className="font-mono text-xs">{e.request_path}</span>],
            ["Status code", e.status_code != null && <HttpStatus code={e.status_code} />],
            ["User-Agent", e.user_agent],
            ["Username", e.username],
            ["Auth result", e.auth_result],
            ["Stored at", formatDateTime(e.created_at)],
          ]}
        />
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-800">Linked alerts</h3>
        {e.alert_ids.length === 0 ? (
          <p className="text-sm text-slate-500">This event is not evidence for any alert.</p>
        ) : (
          <ul className="list-inside list-disc text-sm">
            {e.alert_ids.map((a) => (
              <li key={a}>
                <Link to={`/alerts/${a}`} className="font-mono text-sky-700 hover:underline">
                  {a}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
