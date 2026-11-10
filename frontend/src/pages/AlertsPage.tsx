import { useEffect, useState, type FormEvent } from "react";

import { DatasetSelect } from "../components/DatasetSelect";
import { Button, Card, EmptyState, ErrorMessage, Field, LinkButton, PageHeader, Pagination, Spinner } from "../components/ui";
import { inputCls } from "../lib/styles";
import { AlertTable } from "../features/alerts/AlertTable";
import { useAsync } from "../hooks/useAsync";
import { useUrlFilters } from "../hooks/useUrlFilters";
import { api } from "../services/api";
import type { AlertFilters, AlertStatus, Severity } from "../types/api";

const KEYS = ["dataset", "severity", "status", "source_ip", "rule_code"] as const;
const PAGE_SIZE = 25;

export function AlertsPage() {
  const { filters, setFilters, page, setPage, clear } = useUrlFilters(KEYS);
  const { data: rules } = useAsync(() => api.rules(), []);
  const [ip, setIp] = useState(filters.source_ip);
  useEffect(() => setIp(filters.source_ip), [filters.source_ip]);

  const apiFilters: AlertFilters = {
    dataset_id: filters.dataset,
    severity: filters.severity as Severity | "",
    status: filters.status as AlertStatus | "",
    source_ip: filters.source_ip,
    rule_code: filters.rule_code,
  };
  const key = JSON.stringify(apiFilters);
  const { data, error, loading, reload } = useAsync(() => api.alerts(apiFilters, page, PAGE_SIZE), [key, page]);

  const submitIp = (e: FormEvent) => {
    e.preventDefault();
    setFilters({ source_ip: ip.trim() });
  };

  return (
    <>
      <PageHeader
        title="Alerts"
        description="Rule-based detections. Each alert links to the log events that triggered it. Alerts indicate suspicious behaviour to investigate — not confirmed attacks."
        actions={
          <>
            <DatasetSelect value={filters.dataset} onChange={(id) => setFilters({ dataset: id })} />
            <LinkButton href={api.alertsJsonUrl(apiFilters)}>⬇ Export JSON</LinkButton>
          </>
        }
      />
      <div className="space-y-6">
        <Card>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
            <Field label="Severity" htmlFor="a-sev">
              <select id="a-sev" className={inputCls} value={filters.severity} onChange={(e) => setFilters({ severity: e.target.value })}>
                <option value="">Any</option>
                <option>HIGH</option>
                <option>MEDIUM</option>
                <option>LOW</option>
              </select>
            </Field>
            <Field label="Status" htmlFor="a-status">
              <select id="a-status" className={inputCls} value={filters.status} onChange={(e) => setFilters({ status: e.target.value })}>
                <option value="">Any</option>
                <option>OPEN</option>
                <option>ACKNOWLEDGED</option>
                <option>RESOLVED</option>
              </select>
            </Field>
            <Field label="Detection rule" htmlFor="a-rule">
              <select id="a-rule" className={inputCls} value={filters.rule_code} onChange={(e) => setFilters({ rule_code: e.target.value })}>
                <option value="">Any</option>
                {rules?.map((r) => (
                  <option key={r.rule_code} value={r.rule_code}>
                    {r.name}
                  </option>
                ))}
              </select>
            </Field>
            <form onSubmit={submitIp} className="flex items-end gap-2" aria-label="Filter by source IP">
              <Field label="Source IP" htmlFor="a-ip">
                <input id="a-ip" className={inputCls} value={ip} onChange={(e) => setIp(e.target.value)} placeholder="203.0.113.99" />
              </Field>
              <Button type="submit">Apply</Button>
            </form>
            <div>
              <Button variant="ghost" onClick={clear}>
                Reset filters
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Alert queue" subtitle={data ? `${data.total} alerts · sorted by severity, then most recent` : undefined}>
          {error && <ErrorMessage error={error} onRetry={reload} />}
          {loading && !data && <Spinner />}
          {data && data.total === 0 && (
            <EmptyState title="No alerts match" icon="✓">
              Either no rule reached its threshold for this scope, or the filters exclude every alert.
            </EmptyState>
          )}
          {data && data.total > 0 && (
            <>
              <AlertTable alerts={data.items} />
              <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={setPage} />
            </>
          )}
        </Card>
      </div>
    </>
  );
}
