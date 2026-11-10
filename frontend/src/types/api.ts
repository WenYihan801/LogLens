// Types mirror the FastAPI response schemas in backend/app/schemas.

export type SourceType = "NGINX" | "SSH";
export type Severity = "HIGH" | "MEDIUM" | "LOW";
export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
export type DatasetStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface ApiErrorBody {
  error_code: string;
  message: string;
  details?: unknown;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AppConfig {
  app_env: string;
  read_only: boolean;
  max_upload_size_mb: number;
  max_log_lines: number;
}

export interface Dataset {
  id: string;
  name: string;
  source_type: SourceType;
  original_filename: string;
  file_sha256: string;
  size_bytes: number;
  total_lines: number;
  parsed_lines: number;
  failed_lines: number;
  detection_skipped: number;
  status: DatasetStatus;
  status_message: string | null;
  created_at: string;
  alert_count: number;
}

export interface ImportErrorItem {
  id: number;
  line_number: number;
  error_code: string;
  error_message: string;
  raw_preview: string | null;
}

export interface DatasetDetail extends Dataset {
  error_summary: Record<string, number>;
  import_errors: ImportErrorItem[];
  import_errors_truncated: boolean;
}

export interface UploadResult {
  dataset_id: string;
  status: DatasetStatus;
  source_type: SourceType;
  total_lines: number;
  parsed_lines: number;
  failed_lines: number;
  alerts_generated: number;
  detection_skipped_events: number;
  duplicate_of: string | null;
  processing_ms: number;
}

export interface DetectionRunResult {
  dataset_id: string;
  alerts_total: number;
  created: number;
  updated: number;
  removed: number;
  skipped_events: number;
}

export interface SampleInfo {
  key: string;
  name: string;
  source_type: SourceType;
  filename: string;
  description: string;
}

export interface LogEvent {
  id: number;
  dataset_id: string;
  event_timestamp: string;
  source_type: SourceType;
  source_ip: string | null;
  http_method: string | null;
  request_path: string | null;
  status_code: number | null;
  user_agent: string | null;
  username: string | null;
  auth_result: string | null;
  line_number: number;
}

export interface EvidenceEvent extends LogEvent {
  raw_message: string;
}

export interface EventDetail extends EvidenceEvent {
  created_at: string;
  dataset_name: string;
  alert_ids: string[];
}

export interface Rule {
  id: string;
  rule_code: string;
  name: string;
  description: string | null;
  source_type: SourceType;
  threshold: number;
  window_seconds: number;
  severity: Severity;
  enabled: boolean;
  version: number;
}

export interface Alert {
  id: string;
  dataset_id: string;
  rule_code: string;
  rule_name: string;
  source_ip: string | null;
  severity: Severity;
  status: AlertStatus;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: string;
  note: string;
  created_at: string;
}

export interface AlertDetail extends Alert {
  dataset_name: string;
  rule: Rule;
  explanation: string;
  observed_window_seconds: number;
  evidence: EvidenceEvent[];
  evidence_total: number;
  notes: Note[];
}

export interface CountItem {
  key: string;
  count: number;
}

export interface TrendPoint {
  bucket: string;
  events: number;
  alerts: number;
}

export interface DashboardSummary {
  dataset_id: string | null;
  total_events: number;
  total_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  open_alerts: number;
  unique_source_ips: number;
  dataset_count: number;
  severity_distribution: CountItem[];
  alert_status_distribution: CountItem[];
  status_code_distribution: CountItem[];
  source_type_distribution: CountItem[];
  top_source_ips: CountItem[];
  trend_bucket: "minute" | "hour" | "day";
  activity_trend: TrendPoint[];
  recent_alerts: Alert[];
}

export interface EventFilters {
  dataset_id?: string;
  source_ip?: string;
  source_type?: SourceType | "";
  status_code?: string;
  start?: string;
  end?: string;
  q?: string;
}

export interface AlertFilters {
  dataset_id?: string;
  severity?: Severity | "";
  status?: AlertStatus | "";
  source_ip?: string;
  rule_code?: string;
}
