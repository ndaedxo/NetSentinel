import { useState } from 'react';
import {
  Download,
  FileText,
  File,
  Database,
  ChevronDown,
  Check
} from 'lucide-react';
import { useExport, type ExportColumn, type ExportOptions } from '@/utils/export';

interface ExportButtonProps {
  data: unknown[];
  columns: ExportColumn[];
  filename?: string;
  title?: string;
  disabled?: boolean;
  className?: string;
}

export default function ExportButton({
  data,
  columns,
  filename = 'export',
  title = 'Data Export',
  disabled = false,
  className = ''
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const { toCSV, toPDF, toJSON } = useExport();

  const exportOptions = [
    {
      id: 'csv',
      label: 'Export as CSV',
      description: 'Comma-separated values for spreadsheet applications',
      icon: FileText,
      action: () => exportToCSV('csv')
    },
    {
      id: 'pdf',
      label: 'Export as PDF',
      description: 'Portable document format for printing and sharing',
      icon: File,
      action: () => exportToCSV('pdf')
    },
    {
      id: 'json',
      label: 'Export as JSON',
      description: 'JavaScript object notation for developers',
      icon: Database,
      action: () => exportToCSV('json')
    }
  ];

  const exportToCSV = async (format: 'csv' | 'pdf' | 'json') => {
    setExporting(format);
    setIsOpen(false);

    try {
      const options: ExportOptions = {
        filename,
        title,
        includeTimestamp: true
      };

      switch (format) {
        case 'csv':
          toCSV(data, columns, options);
          break;
        case 'pdf':
          toPDF(data, columns, options);
          break;
        case 'json':
          toJSON(data, options);
          break;
      }
    } catch (error) {
      console.error('Export failed:', error);
      // Could show a toast notification here
    } finally {
      setExporting(null);
    }
  };

  if (disabled || data.length === 0) {
    return (
      <button
        disabled
        className={`flex items-center space-x-2 px-4 py-3 bg-slate-700 text-slate-500 rounded-lg cursor-not-allowed min-h-[44px] ${className}`}
      >
        <Download className="w-4 h-4" />
        <span>Export</span>
        <ChevronDown className="w-4 h-4" />
      </button>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors min-h-[44px]"
      >
        <Download className="w-4 h-4" />
        <span>Export</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20">
            <div className="p-4">
              <h3 className="text-lg font-semibold text-slate-200 mb-3">
                Export Options
              </h3>

              <div className="space-y-3">
                {exportOptions.map((option) => {
                  const Icon = option.icon;
                  const isExporting = exporting === option.id;

                  return (
                    <button
                      key={option.id}
                      onClick={option.action}
                      disabled={isExporting}
                      className="w-full flex items-start space-x-3 p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors text-left group disabled:opacity-50"
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {isExporting ? (
                          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Icon className="w-5 h-5 text-slate-400 group-hover:text-slate-300" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-slate-200 group-hover:text-white">
                            {option.label}
                          </span>
                          {isExporting && (
                            <Check className="w-4 h-4 text-green-400" />
                          )}
                        </div>
                        <p className="text-sm text-slate-400 group-hover:text-slate-300 mt-1">
                          {option.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-700">
                <div className="text-xs text-slate-500">
                  Exporting {data.length} {data.length === 1 ? 'record' : 'records'}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Quick export buttons for common use cases
export function QuickExportButtons({
  data,
  columns,
  filename = 'export',
  title = 'Data Export',
  className = ''
}: ExportButtonProps) {
  const { toCSV, toPDF, toJSON } = useExport();
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (format: 'csv' | 'pdf' | 'json') => {
    setExporting(format);

    try {
      const options = {
        filename,
        title,
        includeTimestamp: true
      };

      switch (format) {
        case 'csv':
          toCSV(data, columns, options);
          break;
        case 'pdf':
          toPDF(data, columns, options);
          break;
        case 'json':
          toJSON(data, options);
          break;
      }
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <button
        onClick={() => handleExport('csv')}
        disabled={exporting === 'csv'}
        className="flex items-center space-x-2 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white rounded-lg transition-colors text-sm"
      >
        {exporting === 'csv' ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <FileText className="w-4 h-4" />
        )}
        <span>CSV</span>
      </button>

      <button
        onClick={() => handleExport('pdf')}
        disabled={exporting === 'pdf'}
        className="flex items-center space-x-2 px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white rounded-lg transition-colors text-sm"
      >
        {exporting === 'pdf' ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <File className="w-4 h-4" />
        )}
        <span>PDF</span>
      </button>

      <button
        onClick={() => handleExport('json')}
        disabled={exporting === 'json'}
        className="flex items-center space-x-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors text-sm"
      >
        {exporting === 'json' ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Database className="w-4 h-4" />
        )}
        <span>JSON</span>
      </button>
    </div>
  );
}
