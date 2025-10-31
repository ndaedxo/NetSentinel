import { useState, useEffect } from "react";
import { IncidentType, IncidentTimelineType } from "@/types";

type IncidentStatus = "open" | "investigating" | "contained" | "resolved" | "closed";
type FilterStatus = "all" | "open" | "investigating" | "contained";
import { getThreatColorClasses } from "@/utils";
import { useApi } from "@/hooks";
import { PageLayout } from "@/components";
import {
  AlertTriangle,
  Clock,
  User,
  CheckCircle,
  XCircle,
  Eye,
  Play,
  Pause,
  Plus,
  Calendar
} from "lucide-react";

export default function IncidentResponsePage() {
  const [incidents, setIncidents] = useState<IncidentType[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentType | null>(null);
  const [timeline, setTimeline] = useState<IncidentTimelineType[]>([]);
  
  const [filter, setFilter] = useState<FilterStatus>('all');
  const { fetchData, postData } = useApi();

  useEffect(() => {
    const loadIncidents = async () => {
      try {
        const data = await fetchData<IncidentType[]>("/api/incidents");
        setIncidents(data);
      } catch (error) {
        console.error("Failed to load incidents:", error);
      }
    };

    loadIncidents();
  }, [fetchData]);

  const loadTimeline = async (incidentId: number) => {
    try {
      const data = await fetchData<IncidentTimelineType[]>(`/api/incidents/${incidentId}/timeline`);
      setTimeline(data);
    } catch (error) {
      console.error("Failed to load incident timeline:", error);
    }
  };

  const updateIncidentStatus = async (incidentId: number, status: IncidentStatus) => {
    try {
      await postData(`/api/incidents/${incidentId}/status`, { status });
      setIncidents(prev => prev.map(incident => 
        incident.id === incidentId 
          ? { ...incident, status, updated_at: new Date().toISOString() }
          : incident
      ));
      if (selectedIncident?.id === incidentId) {
        setSelectedIncident(prev => prev ? { ...prev, status } : null);
      }
    } catch (error) {
      console.error("Failed to update incident status:", error);
    }
  };


  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-red-400 bg-red-500/20';
      case 'investigating':
        return 'text-orange-400 bg-orange-500/20';
      case 'contained':
        return 'text-yellow-400 bg-yellow-500/20';
      case 'resolved':
        return 'text-green-400 bg-green-500/20';
      case 'closed':
        return 'text-slate-400 bg-slate-500/20';
      default:
        return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open':
        return <AlertTriangle className="w-4 h-4" />;
      case 'investigating':
        return <Eye className="w-4 h-4" />;
      case 'contained':
        return <Pause className="w-4 h-4" />;
      case 'resolved':
        return <CheckCircle className="w-4 h-4" />;
      case 'closed':
        return <XCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const filteredIncidents = incidents.filter(incident => 
    filter === 'all' || incident.status === filter
  );

  return (
    <PageLayout>
      <div>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6 lg:mb-8">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-red-500 blur-lg opacity-30"></div>
              <AlertTriangle className="relative w-8 h-8 text-red-400" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white">Incident Response</h1>
              <p className="text-slate-400 text-sm lg:text-base">Manage and track security incidents</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex bg-slate-800 rounded-lg p-1 w-full sm:w-auto overflow-x-auto">
              {(['all', 'open', 'investigating', 'contained'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-[44px] whitespace-nowrap ${
                    filter === status
                      ? 'bg-red-500 text-white'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
            <button className="px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center justify-center space-x-2 min-h-[44px] w-full sm:w-auto">
              <Plus className="w-4 h-4" />
              <span>New Incident</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Incidents List */}
          <div className="lg:col-span-2">
            <div className="card-dark">
              <div className="p-6 border-b border-slate-700">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Active Incidents</h3>
                  <span className="text-sm text-slate-400">
                    {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
              <div className="divide-y divide-slate-700 max-h-96 overflow-y-auto">
                {filteredIncidents.map((incident) => (
                  <div
                    key={incident.id}
                    onClick={() => {
                      setSelectedIncident(incident);
                      loadTimeline(incident.id);
                    }}
                    className="p-6 hover:bg-slate-800/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getThreatColorClasses(incident.severity)}`}>
                            {incident.severity.toUpperCase()}
                          </span>
                          <span className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium ${getStatusColor(incident.status)}`}>
                            {getStatusIcon(incident.status)}
                            <span>{incident.status.toUpperCase()}</span>
                          </span>
                        </div>
                        <h4 className="font-medium text-white mb-1">{incident.title}</h4>
                        <p className="text-sm text-slate-400 mb-2">{incident.description}</p>
                        <div className="flex items-center space-x-4 text-xs text-slate-500">
                          <span className="flex items-center space-x-1">
                            <Calendar className="w-3 h-3" />
                            <span>{new Date(incident.created_at).toLocaleDateString()}</span>
                          </span>
                          {incident.assigned_to && (
                            <span className="flex items-center space-x-1">
                              <User className="w-3 h-3" />
                              <span>{incident.assigned_to}</span>
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="ml-4">
                        <Eye className="w-4 h-4 text-slate-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Incident Details Sidebar */}
          <div className="space-y-6">
            {selectedIncident ? (
              <>
                <div className="card-dark p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">Incident Details</h3>
                    <button
                      onClick={() => setSelectedIncident(null)}
                      className="text-slate-400 hover:text-slate-300"
                    >
                      ×
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <span className="text-slate-400 text-sm">Title</span>
                      <p className="text-white font-medium">{selectedIncident.title}</p>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <div>
                        <span className="text-slate-400 text-sm block">Severity</span>
                        <span className={`inline-flex px-2 py-1 rounded text-xs font-medium border ${getThreatColorClasses(selectedIncident.severity)}`}>
                          {selectedIncident.severity.toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-sm block">Status</span>
                        <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium ${getStatusColor(selectedIncident.status)}`}>
                          {getStatusIcon(selectedIncident.status)}
                          <span>{selectedIncident.status.toUpperCase()}</span>
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 text-sm">Category</span>
                      <p className="text-white font-medium">{selectedIncident.category}</p>
                    </div>

                    <div>
                      <span className="text-slate-400 text-sm">Description</span>
                      <p className="text-white">{selectedIncident.description}</p>
                    </div>

                    {selectedIncident.affected_systems && (
                      <div>
                        <span className="text-slate-400 text-sm">Affected Systems</span>
                        <p className="text-white">{selectedIncident.affected_systems}</p>
                      </div>
                    )}

                    {selectedIncident.assigned_to && (
                      <div>
                        <span className="text-slate-400 text-sm">Assigned To</span>
                        <p className="text-white font-medium">{selectedIncident.assigned_to}</p>
                      </div>
                    )}

                    <div>
                      <span className="text-slate-400 text-sm">Created</span>
                      <p className="text-white">{new Date(selectedIncident.created_at).toLocaleString()}</p>
                    </div>
                  </div>

                  <div className="mt-6 space-y-2">
                    {selectedIncident.status === 'open' && (
                      <button
                        onClick={() => updateIncidentStatus(selectedIncident.id, 'investigating')}
                        className="w-full btn-primary flex items-center justify-center space-x-2"
                      >
                        <Play className="w-4 h-4" />
                        <span>Start Investigation</span>
                      </button>
                    )}
                    {selectedIncident.status === 'investigating' && (
                      <button
                        onClick={() => updateIncidentStatus(selectedIncident.id, 'contained')}
                        className="w-full btn-secondary flex items-center justify-center space-x-2"
                      >
                        <Pause className="w-4 h-4" />
                        <span>Mark Contained</span>
                      </button>
                    )}
                    {(selectedIncident.status === 'contained' || selectedIncident.status === 'investigating') && (
                      <button
                        onClick={() => updateIncidentStatus(selectedIncident.id, 'resolved')}
                        className="w-full btn-secondary flex items-center justify-center space-x-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Mark Resolved</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Timeline */}
                <div className="card-dark p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Timeline</h3>
                  <div className="space-y-4 max-h-64 overflow-y-auto">
                    {timeline.map((event) => (
                      <div key={event.id} className="flex space-x-3">
                        <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-white">{event.action_type}</span>
                            <span className="text-xs text-slate-500">
                              {new Date(event.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-sm text-slate-400 mt-1">{event.description}</p>
                          {event.performed_by && (
                            <p className="text-xs text-slate-500 mt-1">by {event.performed_by}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="card-dark p-6">
                <div className="text-center py-8">
                  <AlertTriangle className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-400 mb-2">No Incident Selected</h3>
                  <p className="text-slate-500">Select an incident to view details and timeline</p>
                </div>
              </div>
            )}

            {/* Quick Stats */}
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Quick Stats</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Open</span>
                  <span className="text-red-400 font-medium">
                    {incidents.filter(i => i.status === 'open').length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Investigating</span>
                  <span className="text-orange-400 font-medium">
                    {incidents.filter(i => i.status === 'investigating').length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Contained</span>
                  <span className="text-yellow-400 font-medium">
                    {incidents.filter(i => i.status === 'contained').length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Resolved</span>
                  <span className="text-green-400 font-medium">
                    {incidents.filter(i => i.status === 'resolved').length}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
