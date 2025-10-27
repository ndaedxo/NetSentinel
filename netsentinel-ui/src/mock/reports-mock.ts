import type { ReportType } from '@/types';

/**
 * Mock report data
 */
export const mockReports: ReportType[] = [
  {
    id: 1,
    title: "Weekly Security Summary",
    report_type: "security_summary",
    status: "completed",
    parameters: JSON.stringify({
      period: "weekly",
      include_threats: true,
      include_alerts: true
    }),
    file_path: "/reports/security-summary-2025-10-27.pdf",
    generated_by: "system",
    scheduled_for: null,
    created_at: "2025-10-27T06:00:00Z",
    updated_at: "2025-10-27T06:15:00Z"
  },
  {
    id: 2,
    title: "Network Traffic Analysis",
    report_type: "network_analysis",
    status: "generating",
    parameters: JSON.stringify({
      timeframe: "24h",
      include_anomalies: true
    }),
    file_path: null,
    generated_by: "admin",
    scheduled_for: null,
    created_at: "2025-10-27T10:00:00Z",
    updated_at: "2025-10-27T10:00:00Z"
  },
  {
    id: 3,
    title: "Monthly Threat Intelligence",
    report_type: "threat_intelligence",
    status: "scheduled",
    parameters: JSON.stringify({
      period: "monthly",
      focus_areas: ["malware", "ddos"]
    }),
    file_path: null,
    generated_by: "system",
    scheduled_for: "2025-11-01T00:00:00Z",
    created_at: "2025-10-27T08:00:00Z",
    updated_at: "2025-10-27T08:00:00Z"
  }
];
