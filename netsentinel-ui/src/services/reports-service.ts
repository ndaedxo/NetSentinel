import type { ReportType } from '@/types';
import { mockReports } from '@/mock';

/**
 * Generate report request data
 */
export interface GenerateReportData {
  title: string;
  report_type: string;
  parameters?: Record<string, unknown>;
  scheduled_for?: string;
}

/**
 * Get all reports
 */
export async function getReports(): Promise<ReportType[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 400));
  return mockReports;
}

/**
 * Generate a new report
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function generateReport(_reportData: GenerateReportData): Promise<{ success: boolean; report_id?: number }> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));
  return { success: true, report_id: Math.floor(Math.random() * 1000) };
}
