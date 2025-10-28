import jsPDF from 'jspdf';
import 'jspdf-autotable';

// Extend jsPDF type for autoTable
declare module 'jspdf' {
  interface jsPDF {
    autoTable: (options: any) => jsPDF;
  }
}

export interface ExportColumn {
  key: string;
  label: string;
  formatter?: (value: any) => string;
}

export interface ExportOptions {
  filename?: string;
  title?: string;
  includeTimestamp?: boolean;
  dateFormat?: Intl.DateTimeFormatOptions;
}

// CSV Export
export function exportToCSV<T>(
  data: T[],
  columns: ExportColumn[],
  options: ExportOptions = {}
): void {
  const {
    filename = 'export',
    includeTimestamp = true
  } = options;

  // Create CSV header
  const headers = columns.map(col => col.label);

  // Create CSV rows
  const rows = data.map(item => {
    return columns.map(col => {
      const value = getNestedValue(item, col.key);
      const formattedValue = col.formatter ? col.formatter(value) : String(value || '');
      // Escape CSV special characters
      return escapeCSVValue(formattedValue);
    });
  });

  // Combine headers and rows
  const csvContent = [headers, ...rows]
    .map(row => row.join(','))
    .join('\n');

  // Create and download file
  const timestamp = includeTimestamp ? `_${new Date().toISOString().split('T')[0]}` : '';
  const fullFilename = `${filename}${timestamp}.csv`;

  downloadFile(csvContent, fullFilename, 'text/csv');
}

// PDF Export
export function exportToPDF<T>(
  data: T[],
  columns: ExportColumn[],
  options: ExportOptions = {}
): void {
  const {
    filename = 'export',
    title = 'Data Export',
    includeTimestamp = true
  } = options;

  // Create PDF document
  const pdf = new jsPDF();

  // Add title
  pdf.setFontSize(16);
  pdf.text(title, 14, 20);

  // Add timestamp if requested
  if (includeTimestamp) {
    pdf.setFontSize(10);
    pdf.text(`Generated on ${new Date().toLocaleString()}`, 14, 30);
  }

  // Prepare table data
  const headers = columns.map(col => col.label);
  const rows = data.map(item => {
    return columns.map(col => {
      const value = getNestedValue(item, col.key);
      return col.formatter ? col.formatter(value) : String(value || '');
    });
  });

  // Add table
  pdf.autoTable({
    head: [headers],
    body: rows,
    startY: includeTimestamp ? 40 : 30,
    styles: {
      fontSize: 8,
      cellPadding: 2,
    },
    headStyles: {
      fillColor: [59, 130, 246], // blue-500
      textColor: 255,
      fontStyle: 'bold',
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252], // slate-50
    },
    margin: { top: 10 },
  });

  // Download PDF
  const timestamp = includeTimestamp ? `_${new Date().toISOString().split('T')[0]}` : '';
  const fullFilename = `${filename}${timestamp}.pdf`;

  pdf.save(fullFilename);
}

// JSON Export
export function exportToJSON<T>(
  data: T[],
  options: ExportOptions = {}
): void {
  const {
    filename = 'export',
    includeTimestamp = true
  } = options;

  const jsonContent = JSON.stringify(data, null, 2);

  const timestamp = includeTimestamp ? `_${new Date().toISOString().split('T')[0]}` : '';
  const fullFilename = `${filename}${timestamp}.json`;

  downloadFile(jsonContent, fullFilename, 'application/json');
}

// Excel-style CSV (with proper escaping)
function escapeCSVValue(value: string): string {
  // If value contains comma, newline, or quote, wrap in quotes and escape internal quotes
  if (value.includes(',') || value.includes('\n') || value.includes('"')) {
    return '"' + value.replace(/"/g, '""') + '"';
  }
  return value;
}

// Get nested object value by path
function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => {
    return current && typeof current === 'object' ? current[key] : undefined;
  }, obj);
}

// Download file utility
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up the URL object
  URL.revokeObjectURL(url);
}

// Predefined column configurations for common data types
export const THREAT_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'ip_address', label: 'IP Address' },
  { key: 'threat_type', label: 'Threat Type' },
  { key: 'severity', label: 'Severity' },
  { key: 'threat_score', label: 'Threat Score' },
  {
    key: 'created_at',
    label: 'Detected At',
    formatter: (value) => new Date(value).toLocaleString()
  },
  { key: 'country_code', label: 'Country' },
  { key: 'status', label: 'Status' }
];

export const ALERT_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'title', label: 'Title' },
  { key: 'message', label: 'Message' },
  { key: 'severity', label: 'Severity' },
  { key: 'status', label: 'Status' },
  {
    key: 'created_at',
    label: 'Created At',
    formatter: (value) => new Date(value).toLocaleString()
  },
  { key: 'source', label: 'Source' },
  { key: 'category', label: 'Category' }
];

export const SYSTEM_HEALTH_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'name', label: 'Service Name' },
  { key: 'status', label: 'Status' },
  { key: 'uptime', label: 'Uptime' },
  { key: 'response_time', label: 'Response Time (ms)' },
  {
    key: 'last_checked',
    label: 'Last Checked',
    formatter: (value) => new Date(value).toLocaleString()
  },
  { key: 'error_count', label: 'Error Count' }
];

// Export component hook
export function useExport() {
  const exportData = {
    toCSV: exportToCSV,
    toPDF: exportToPDF,
    toJSON: exportToJSON
  };

  return exportData;
}
