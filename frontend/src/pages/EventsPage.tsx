import { useState } from "react";

import { DatasetSelect } from "../components/DatasetSelect";
import { Card, Drawer, EmptyState, ErrorMessage, LinkButton, PageHeader, Pagination, Spinner } from "../components/ui";
import { EVENT_FILTER_KEYS, EventFilterBar } from "../features/events/EventFilterBar";
import { EventDetailPanel } from "../features/events/EventDetailPanel";
import { EventTable } from "../features/events/EventTable";
import { useAsync } from "../hooks/useAsync";
import { useUrlFilters } from "../hooks/useUrlFilters";
import { api } from "../services/api";
import type { EventFilters, SourceType } from "../types/api";

const PAGE_SIZE = 50;

export function EventsPage() {
  const { filters, setFilters, page, setPage, clear } = useUrlFilters(EVENT_FILTER_KEYS);
  const [selected, setSelected] = useState<number>();

  const apiFilters: EventFilters = {
    dataset_id: filters.dataset,
    source_ip: filters.source_ip,
    source_type: filters.source_type as SourceType | "",
    status_code: filters.status_code,
    start: filters.start,
    end: filters.end,
    q: filters.q,
  };
  const key = JSON.stringify(apiFilters);
  const { data, error, loading, reload } = useAsync(() => api.events(apiFilters, page, PAGE_SIZE), [key, page]);

  return (
    <>
      <PageHeader
        title="Events"
        description="Normalised log events. Filtering and pagination run on the server; click a row for the raw line."
        actions={
          <>
            <DatasetSelect value={filters.dataset} onChange={(id) => setFilters({ dataset: id })} />
            <LinkButton href={api.eventsCsvUrl(apiFilters)}>⬇ Export CSV</LinkButton>
          </>
        }
      />
      <div className="space-y-6">
        <Card>
          <EventFilterBar values={filters} onApply={setFilters} onClear={clear} />
        </Card>
        <Card title="Results" subtitle={data ? `${data.total.toLocaleString()} matching events` : undefined}>
          {error && <ErrorMessage error={error} onRetry={reload} />}
          {loading && !data && <Spinner />}
          {data && data.total === 0 && (
            <EmptyState title="No events match these filters">Try widening the time range or clearing filters.</EmptyState>
          )}
          {data && data.total > 0 && (
            <div className={loading ? "opacity-60 transition-opacity" : undefined}>
              <EventTable events={data.items} onSelect={(e) => setSelected(e.id)} />
              <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={setPage} />
            </div>
          )}
        </Card>
      </div>
      <Drawer open={selected !== undefined} onClose={() => setSelected(undefined)} title={`Event #${selected ?? ""}`}>
        {selected !== undefined && <EventDetailPanel id={selected} />}
      </Drawer>
    </>
  );
}
