import { useState, useEffect } from "react";
import { ReportType } from "@/types";

type ReportFilterStatus = "all" | "completed" | "generating" | "failed";
import { useApi } from "@/hooks";
import Header from "@/components/Header";
import { 
  FileText, 
  Download, 
  Calendar, 
  Clock, 
  CheckCircle,
  XCircle,
  AlertCircle,
  Plus,
  BarChart3,
  Shield,
  Network,
  Activity,
  Zap
} from "lucide-react";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportType[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filter, setFilter] = useState<ReportFilterStatus>('all');
  const [newReport, setNewReport] = useState({
    title: '',
    report_type: 'security_summary',
    parameters: ''
  });
  const { fetchData, postData } = useApi();

  useEffect(() => {
    const loadReports = async () => {
      try {
        const data = await fetchData<ReportType[]>("/api/reports");
        setReports(data);
      } catch (error) {
        console.error("Failed to load reports:", error);
      }
    };

    loadReports();
  }, [fetchData]);

  const generateReport = async () => {
    try {
      await postData("/api/reports/generate", newReport);
      setShowCreateModal(false);
      setNewReport({ title: '', report_type: 'security_summary', parameters: '' });
      // Reload reports
      const data = await fetchData<ReportType[]>("/api/reports");
      setReports(data);
    } catch (error) {
      console.error("Failed to generate report:", error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400 bg-green-500/20';
      case 'generating':
        return 'text-blue-400 bg-blue-500/20';
      case 'failed':
        return 'text-red-400 bg-red-500/20';
      case 'scheduled':
        return 'text-yellow-400 bg-yellow-500/20';
      default:
        return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
      case 'generating':
        return <Clock className="w-4 h-4 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4" />;
      case 'scheduled':
        return <Calendar className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  const getReportIcon = (reportType: string) => {
    switch (reportType) {
      case 'security_summary':
        return <Shield className="w-5 h-5" />;
      case 'threat_analysis':
        return <AlertCircle className="w-5 h-5" />;
      case 'network_analysis':
        return <Network className="w-5 h-5" />;
      case 'performance_metrics':
        return <Activity className="w-5 h-5" />;
      case 'incident_report':
        return <Zap className="w-5 h-5" />;
      default:
        return <BarChart3 className="w-5 h-5" />;
    }
  };

  const getReportTypeLabel = (reportType: string) => {
    const labels: { [key: string]: string } = {
      'security_summary': 'Security Summary',
      'threat_analysis': 'Threat Analysis',
      'network_analysis': 'Network Analysis', 
      'performance_metrics': 'Performance Metrics',
      'incident_report': 'Incident Report',
      'compliance_audit': 'Compliance Audit'
    };
    return labels[reportType] || reportType;
  };

  const filteredReports = reports.filter(report => 
    filter === 'all' || report.status === filter
  );

  const reportTemplates = [
    {
      type: 'security_summary',
      title: 'Security Summary Report',
      description: 'Comprehensive overview of security metrics and threats',
      icon: <Shield className="w-6 h-6" />
    },
    {
      type: 'threat_analysis',
      title: 'Threat Analysis Report',
      description: 'Detailed analysis of detected threats and patterns',
      icon: <AlertCircle className="w-6 h-6" />
    },
    {
      type: 'network_analysis',
      title: 'Network Analysis Report',
      description: 'Network topology and traffic analysis',
      icon: <Network className="w-6 h-6" />
    },
    {
      type: 'performance_metrics',
      title: 'Performance Metrics Report',
      description: 'System performance and health metrics',
      icon: <Activity className="w-6 h-6" />
    },
    {
      type: 'incident_report',
      title: 'Incident Response Report',
      description: 'Summary of security incidents and responses',
      icon: <Zap className="w-6 h-6" />
    },
    {
      type: 'compliance_audit',
      title: 'Compliance Audit Report',
      description: 'Compliance status and audit findings',
      icon: <CheckCircle className="w-6 h-6" />
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Header />
      
      <div className="px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-emerald-500 blur-lg opacity-30"></div>
              <FileText className="relative w-8 h-8 text-emerald-400" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Reports & Analytics</h1>
              <p className="text-slate-400">Generate and manage security reports</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex bg-slate-800 rounded-lg p-1">
              {(['all', 'completed', 'generating', 'failed'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    filter === status
                      ? 'bg-emerald-500 text-white'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Generate Report</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Reports List */}
          <div className="lg:col-span-2">
            <div className="card-dark">
              <div className="p-6 border-b border-slate-700">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Generated Reports</h3>
                  <span className="text-sm text-slate-400">
                    {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
              <div className="divide-y divide-slate-700">
                {filteredReports.map((report) => (
                  <div key={report.id} className="p-6 hover:bg-slate-800/50 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="text-emerald-400 mt-1">
                          {getReportIcon(report.report_type)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h4 className="font-medium text-white">{report.title}</h4>
                            <span className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium ${getStatusColor(report.status)}`}>
                              {getStatusIcon(report.status)}
                              <span>{report.status.toUpperCase()}</span>
                            </span>
                          </div>
                          <p className="text-sm text-slate-400 mb-2">
                            {getReportTypeLabel(report.report_type)}
                          </p>
                          <div className="flex items-center space-x-4 text-xs text-slate-500">
                            <span className="flex items-center space-x-1">
                              <Calendar className="w-3 h-3" />
                              <span>Generated {new Date(report.created_at).toLocaleDateString()}</span>
                            </span>
                            {report.generated_by && (
                              <span>by {report.generated_by}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="ml-4 flex items-center space-x-2">
                        {report.status === 'completed' && (
                          <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors">
                            <Download className="w-4 h-4 text-slate-400" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {filteredReports.length === 0 && (
                  <div className="p-12 text-center">
                    <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-400 mb-2">No Reports Found</h3>
                    <p className="text-slate-500">Generate your first security report to get started</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Report Statistics</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Total Reports</span>
                  <span className="text-white font-medium">{reports.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Completed</span>
                  <span className="text-green-400 font-medium">
                    {reports.filter(r => r.status === 'completed').length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">In Progress</span>
                  <span className="text-blue-400 font-medium">
                    {reports.filter(r => r.status === 'generating').length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Failed</span>
                  <span className="text-red-400 font-medium">
                    {reports.filter(r => r.status === 'failed').length}
                  </span>
                </div>
              </div>
            </div>

            {/* Scheduled Reports */}
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Scheduled Reports</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-white">Weekly Security Summary</p>
                    <p className="text-xs text-slate-400">Every Monday at 9:00 AM</p>
                  </div>
                  <div className="text-emerald-400">
                    <CheckCircle className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-white">Monthly Threat Analysis</p>
                    <p className="text-xs text-slate-400">First day of each month</p>
                  </div>
                  <div className="text-emerald-400">
                    <CheckCircle className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
              <div className="space-y-3">
                {reports.slice(0, 3).map((report) => (
                  <div key={report.id} className="flex items-center space-x-3">
                    <div className="text-emerald-400">
                      {getReportIcon(report.report_type)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-white">{report.title}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(report.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className={`text-xs px-2 py-1 rounded ${getStatusColor(report.status)}`}>
                      {report.status}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Create Report Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="card-dark p-6 w-full max-w-2xl mx-4">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Generate New Report</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-slate-300"
                >
                  ×
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">
                    Report Template
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {reportTemplates.map((template) => (
                      <div
                        key={template.type}
                        onClick={() => {
                          setNewReport(prev => ({
                            ...prev,
                            report_type: template.type,
                            title: template.title
                          }));
                        }}
                        className={`p-4 rounded-lg border cursor-pointer transition-all ${
                          newReport.report_type === template.type
                            ? 'border-emerald-500 bg-emerald-500/10'
                            : 'border-slate-600 hover:border-slate-500'
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          <div className={`${newReport.report_type === template.type ? 'text-emerald-400' : 'text-slate-400'}`}>
                            {template.icon}
                          </div>
                          <div>
                            <h3 className="font-medium text-white text-sm">{template.title}</h3>
                            <p className="text-xs text-slate-400 mt-1">{template.description}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Report Title
                  </label>
                  <input
                    type="text"
                    value={newReport.title}
                    onChange={(e) => setNewReport(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500"
                    placeholder="Enter report title"
                  />
                </div>

                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={generateReport}
                    disabled={!newReport.title || !newReport.report_type}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Generate Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
