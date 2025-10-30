import type { ReportType } from '@/types';
import { mockConfig } from '@/test/__mocks__/mock-config';
import { generateMockReports } from '@/mock/reports-mock';

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
 * Get all reports using dynamic mocking
 */
export async function getReports(): Promise<ReportType[]> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay
  await store.getGenerator('threats').delay(delayRange.min * 1.6, delayRange.max * 1.6);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('network');
  }

  // Generate dynamic reports
  return generateMockReports(15);
}

/**
 * Generate a new report using dynamic mocking
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function generateReport(_reportData: GenerateReportData): Promise<{ success: boolean; report_id?: number }> {
  const store = mockConfig.getStore('threats');
  const delayRange = mockConfig.getDelayRange('threats');

  // Simulate realistic API delay (longer for report generation)
  await store.getGenerator('threats').delay(delayRange.min * 2, delayRange.max * 3);

  // Check for simulated errors
  if (store.getGenerator('threats').shouldError()) {
    throw store.getGenerator('threats').generateError('server');
  }

  return { success: true, report_id: Math.floor(Math.random() * 1000) };
}
