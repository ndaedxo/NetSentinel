import type { ReportType } from '@/types';
import { faker } from '@faker-js/faker';

/**
 * Generate dynamic mock reports
 */
export const generateMockReports = (count: number = 12): ReportType[] => {
  const reportTypes = ['security_summary', 'network_analysis', 'threat_intelligence', 'performance_report', 'compliance_report'];
  const statuses: Array<'completed' | 'generating' | 'scheduled' | 'failed'> = ['completed', 'generating', 'scheduled', 'failed'];
  const generators = ['system', 'admin', 'analyst'];

  return Array.from({ length: count }, (_, index) => {
    const reportType = reportTypes[Math.floor(Math.random() * reportTypes.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    const generatedBy = generators[Math.floor(Math.random() * generators.length)];

    let title: string;
    let parameters: Record<string, unknown>;
    let filePath: string | null = null;
    let scheduledFor: string | null = null;

    switch (reportType) {
      case 'security_summary':
        title = `${faker.helpers.arrayElement(['Daily', 'Weekly', 'Monthly'])} Security Summary`;
        parameters = {
          period: faker.helpers.arrayElement(['daily', 'weekly', 'monthly']),
          include_threats: Math.random() > 0.3,
          include_alerts: Math.random() > 0.2,
          include_metrics: Math.random() > 0.4
        };
        break;
      case 'network_analysis':
        title = `Network ${faker.helpers.arrayElement(['Traffic', 'Performance', 'Security'])} Analysis`;
        parameters = {
          timeframe: faker.helpers.arrayElement(['1h', '24h', '7d', '30d']),
          include_anomalies: Math.random() > 0.3,
          protocols: faker.helpers.arrayElements(['HTTP', 'HTTPS', 'SSH', 'FTP', 'SMTP'], { min: 1, max: 3 })
        };
        break;
      case 'threat_intelligence':
        title = `${faker.helpers.arrayElement(['Weekly', 'Monthly'])} Threat Intelligence Report`;
        parameters = {
          period: faker.helpers.arrayElement(['weekly', 'monthly']),
          focus_areas: faker.helpers.arrayElements(['malware', 'ddos', 'phishing', 'ransomware', 'brute-force'], { min: 1, max: 3 }),
          regions: faker.helpers.arrayElements(['US', 'EU', 'Asia', 'Global'], { min: 1, max: 2 })
        };
        break;
      case 'performance_report':
        title = `System Performance ${faker.helpers.arrayElement(['Analysis', 'Report', 'Dashboard'])}`;
        parameters = {
          metrics: faker.helpers.arrayElements(['cpu', 'memory', 'network', 'disk', 'response-time'], { min: 2, max: 5 }),
          timeframe: faker.helpers.arrayElement(['1h', '24h', '7d'])
        };
        break;
      case 'compliance_report':
        title = `${faker.helpers.arrayElement(['GDPR', 'HIPAA', 'SOX', 'PCI-DSS'])} Compliance Report`;
        parameters = {
          standard: faker.helpers.arrayElement(['GDPR', 'HIPAA', 'SOX', 'PCI-DSS']),
          assessment_period: faker.helpers.arrayElement(['monthly', 'quarterly', 'yearly'])
        };
        break;
      default:
        title = `${faker.company.buzzNoun()} Report`;
        parameters = {};
    }

    // Generate file path for completed reports
    if (status === 'completed') {
      const date = new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000); // Within last 30 days
      const dateStr = date.toISOString().split('T')[0];
      filePath = `/reports/${reportType}-${dateStr}-${faker.string.alphanumeric(8)}.pdf`;
    }

    // Generate scheduled date for scheduled reports
    if (status === 'scheduled') {
      const futureDate = new Date(Date.now() + Math.random() * 30 * 24 * 60 * 60 * 1000); // Within next 30 days
      scheduledFor = futureDate.toISOString();
    }

    const createdAt = new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000);
    const updatedAt = new Date(createdAt.getTime() + Math.random() * 2 * 60 * 60 * 1000); // Up to 2 hours later

    return {
      id: index + 1,
      title,
      report_type: reportType,
      status,
      parameters: JSON.stringify(parameters),
      file_path: filePath,
      generated_by: generatedBy,
      scheduled_for: scheduledFor,
      created_at: createdAt.toISOString(),
      updated_at: updatedAt.toISOString()
    };
  });
};

/**
 * Mock report data - dynamically generated
 */
export const mockReports: ReportType[] = generateMockReports(15);

/**
 * Generate reports by status
 */
export const generateReportsByStatus = (status: 'completed' | 'generating' | 'scheduled' | 'failed', count: number = 5): ReportType[] => {
  return Array.from({ length: count }, (_, index) => {
    const baseReport = generateMockReports(1)[0];
    return {
      ...baseReport,
      id: Date.now() + index,
      status,
      file_path: status === 'completed' ? `/reports/${baseReport.report_type}-${Date.now()}.pdf` : null,
      scheduled_for: status === 'scheduled' ? new Date(Date.now() + 86400000).toISOString() : null,
    };
  });
};

/**
 * Generate reports by type
 */
export const generateReportsByType = (reportType: string, count: number = 3): ReportType[] => {
  return Array.from({ length: count }, (_, index) => {
    const report = generateMockReports(1)[0];
    return {
      ...report,
      id: Date.now() + index,
      report_type: reportType,
      title: `${faker.company.buzzNoun()} ${reportType.replace('_', ' ')} Report`,
    };
  });
};

/**
 * Get reports ready for download
 */
export const getCompletedReports = (): ReportType[] => {
  return mockReports.filter(report => report.status === 'completed' && report.file_path);
};

/**
 * Get pending reports (generating or scheduled)
 */
export const getPendingReports = (): ReportType[] => {
  return mockReports.filter(report => report.status === 'generating' || report.status === 'scheduled');
};
