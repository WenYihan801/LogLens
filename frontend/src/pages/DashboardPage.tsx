import { Link, useNavigate } from "react-router-dom";

import { DatasetSelect } from "../components/DatasetSelect";
import { Card, EmptyState, ErrorMessage, PageHeader, Spinner } from "../components/ui";
import { AlertTable } from "../features/alerts/AlertTable";
import { SeverityChart, StatusCodeChart, TopIpChart, TrendChart } from "../features/dashboard/Charts";
import { StatCards } from "../features/dashboard/StatCards";
import { SampleLoader } from "../features/datasets/SampleLoader";
import { useAsync } from "../hooks/useAsync";
import { useDatasetScope } from "../hooks/useDatasetScope";
import { api } from "../services/api";

export function DashboardPage() {
  const [datasetId, setDatasetId] = useDatasetScope();
  const navigate = useNavigate();
  const { data: s, error, loading, reload } = useAsync(() => api.dashboard(datasetId || undefined), [datasetId]);

  const hasData = s && (s.dataset_count > 0 || s.total_events > 0);
  const scope = datasetId ? `?dataset=${datasetId}` : "";

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Overview of imported log events and security alerts for the selected scope."
        actions={hasData && <DatasetSelect value={datasetId} onChange={setDatasetId} />}
      />
      {error && <ErrorMessage error={error} onRetry={reload} />}
      {loading && !s && <Spinner />}

      {s && !hasData && (
        <Card title="Welcome to LogLens">
          <div className="space-y-5">
            <EmptyState title="No logs imported yet" icon="◎">
              LogLens parses Nginx access logs and SSH authentication logs, runs explainable detection rules
              (SSH brute force, HTTP 404 bursts, sensitive-path probing) and links every alert to the raw log
              lines that triggered it. Load a synthetic sample below or{" "}
              <Link to="/datasets" className="font-medium text-sky-700 underline">
                upload your own file
              </Link>
              .
            </EmptyState>
            <SampleLoader onLoaded={(r) => navigate(`/?dataset=${r.dataset_id}`)} />
          </div>
        </Card>
      )}

      {s && hasData && (
        <div className="space-y-6">
          <StatCards s={s} />
          <div className="grid gap-6 lg:grid-cols-3">
            <Card title="Log activity trend" subtitle={`Events and alerts per ${s.trend_bucket} (local time)`} className="lg:col-span-2">
              <TrendChart summary={s} />
            </Card>
            <Card title="Alerts by risk level" subtitle="HIGH / MEDIUM / LOW">
              <SeverityChart data={s.severity_distribution} />
            </Card>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="HTTP status codes" subtitle="Nginx events only">
              <StatusCodeChart data={s.status_code_distribution} />
            </Card>
            <Card title="Top source IPs" subtitle="By number of log events">
              <TopIpChart data={s.top_source_ips} />
            </Card>
          </div>
          <Card
            title="Recent alerts"
            subtitle="Most recent by first-seen time"
            actions={
              <Link to={`/alerts${scope}`} className="text-sm font-medium text-sky-700 hover:underline">
                View all →
              </Link>
            }
          >
            {s.recent_alerts.length ? (
              <AlertTable alerts={s.recent_alerts} compact />
            ) : (
              <EmptyState title="No alerts in this scope" icon="✓">
                None of the detection rules reached their threshold.
              </EmptyState>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
