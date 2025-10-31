import { useState } from "react";
import { Bell, CheckCircle, Clock, AlertTriangle, Filter, Search } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { PageLayout } from "@/components";
import { useApi } from "@/hooks";
import { AlertType } from "@/types";
import { getThreatColorClasses } from "@/utils";

export default function AlertManagement() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const { data: alerts, refetch } = useApi<AlertType[]>("/api/alerts/all", 5000);


  const getStatusIcon = (status: string) => {
    switch (status) {
      case "new":
        return <Clock className="w-4 h-4 text-blue-400" />;
      case "acknowledged":
        return <CheckCircle className="w-4 h-4 text-yellow-400" />;
      case "resolved":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-slate-400" />;
    }
  };

  const handleAcknowledge = async (id: number) => {
    try {
      await fetch("/api/alerts/acknowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      refetch();
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
    }
  };

  const handleResolve = async (id: number) => {
    try {
      await fetch("/api/alerts/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      refetch();
    } catch (error) {
      console.error("Failed to resolve alert:", error);
    }
  };

  const filteredAlerts = alerts?.filter((alert) => {
    const matchesSearch = alert.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (alert.description && alert.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = statusFilter === "all" || alert.status === statusFilter;
    const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
    return matchesSearch && matchesStatus && matchesSeverity;
  }) || [];

  return (
    <PageLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gradient flex items-center space-x-3">
            <Bell className="w-8 h-8 text-blue-400" />
            <span>Alert Management</span>
          </h1>
          <p className="text-slate-400 mt-2">Review and manage security alerts</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Alerts</p>
                <p className="text-2xl font-bold text-white mt-1">{alerts?.length || 0}</p>
              </div>
              <Bell className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">New</p>
                <p className="text-2xl font-bold text-blue-400 mt-1">
                  {alerts?.filter(a => a.status === "new").length || 0}
                </p>
              </div>
              <Clock className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Acknowledged</p>
                <p className="text-2xl font-bold text-yellow-400 mt-1">
                  {alerts?.filter(a => a.status === "acknowledged").length || 0}
                </p>
              </div>
              <CheckCircle className="w-6 h-6 text-yellow-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Resolved</p>
                <p className="text-2xl font-bold text-green-400 mt-1">
                  {alerts?.filter(a => a.status === "resolved").length || 0}
                </p>
              </div>
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="card-dark p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 text-base min-h-[44px]"
                aria-label="Search alerts"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50 text-base min-h-[44px]"
                aria-label="Filter by status"
              >
                <option value="all">All Statuses</option>
                <option value="new">New</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="resolved">Resolved</option>
              </select>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-4 py-3 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50 text-base min-h-[44px]"
                aria-label="Filter by severity"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-4">
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className="card-dark p-4 md:p-6 hover:border-slate-600/50 transition-all"
            >
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 lg:gap-0">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    {getStatusIcon(alert.status)}
                    <h3 className="text-lg font-semibold text-white">{alert.title}</h3>
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getThreatColorClasses(alert.severity)}`}>
                      {alert.severity}
                    </span>
                  </div>
                  {alert.description && (
                    <p className="text-sm text-slate-400 mb-3">{alert.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs text-slate-500">
                    <span>Created {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}</span>
                    <span className="hidden sm:inline">•</span>
                    <span className="capitalize">Status: {alert.status}</span>
                    {alert.threat_id && (
                      <>
                        <span className="hidden sm:inline">•</span>
                        <span>Threat ID: {alert.threat_id}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-2 ml-4 mt-4 sm:mt-0">
                  {alert.status === "new" && (
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="px-4 py-3 bg-yellow-600/20 hover:bg-yellow-600/30 border border-yellow-500/30 text-yellow-300 rounded-lg transition-colors text-sm font-medium min-h-[44px] w-full sm:w-auto"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alert.status !== "resolved" && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-4 py-3 bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 text-green-300 rounded-lg transition-colors text-sm font-medium min-h-[44px] w-full sm:w-auto"
                    >
                      Resolve
                    </button>
                  )}
                  {alert.status === "resolved" && (
                    <span className="flex items-center justify-center space-x-2 px-4 py-3 bg-green-500/10 border border-green-500/30 text-green-300 rounded-lg text-sm font-medium min-h-[44px] w-full sm:w-auto">
                      <CheckCircle className="w-4 h-4" />
                      <span>Resolved</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageLayout>
  );
}
