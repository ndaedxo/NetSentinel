import { useState, useEffect } from "react";
import { NetworkTopology, NetworkDeviceType } from "@/types";
import { useApi } from "@/hooks";
import { PageLayout } from "@/components";
import {
  Network,
  Server,
  Router,
  Monitor,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  Eye,
  Settings
} from "lucide-react";

export default function NetworkAnalysisPage() {
  const [topology, setTopology] = useState<NetworkTopology | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<NetworkDeviceType | null>(null);
  const [viewMode, setViewMode] = useState<'topology' | 'list'>('topology');
  const { fetchData } = useApi();

  useEffect(() => {
    const loadTopology = async () => {
      try {
        const data = await fetchData<NetworkTopology>("/api/network/topology");
        setTopology(data);
      } catch (error) {
        console.error("Failed to load network topology:", error);
      }
    };

    loadTopology();
  }, [fetchData]);

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType.toLowerCase()) {
      case 'router':
        return <Router className="w-5 h-5" />;
      case 'server':
        return <Server className="w-5 h-5" />;
      case 'firewall':
        return <Shield className="w-5 h-5" />;
      default:
        return <Monitor className="w-5 h-5" />;
    }
  };

  const getStatusColor = (isOnline: number, vulnerabilityScore: number) => {
    if (!isOnline) return "text-red-400 bg-red-500/20";
    if (vulnerabilityScore > 7) return "text-orange-400 bg-orange-500/20";
    return "text-green-400 bg-green-500/20";
  };

  const getStatusIcon = (isOnline: number, vulnerabilityScore: number) => {
    if (!isOnline) return <XCircle className="w-4 h-4" />;
    if (vulnerabilityScore > 7) return <AlertTriangle className="w-4 h-4" />;
    return <CheckCircle className="w-4 h-4" />;
  };

  if (!topology) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-slate-400">Loading network topology...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <div>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 lg:gap-4 mb-6 lg:mb-8">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-purple-500 blur-lg opacity-30"></div>
              <Network className="relative w-8 h-8 text-purple-400" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white">Network Analysis</h1>
              <p className="text-slate-400 text-sm lg:text-base">Real-time network topology and device monitoring</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-3">
            <div className="flex bg-slate-800 rounded-lg p-1 w-full sm:w-auto">
              <button
                onClick={() => setViewMode('topology')}
                className={`px-4 py-3 rounded-md text-sm font-medium transition-colors min-h-[44px] flex-1 sm:flex-initial ${
                  viewMode === 'topology'
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Topology
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-4 py-3 rounded-md text-sm font-medium transition-colors min-h-[44px] flex-1 sm:flex-initial ${
                  viewMode === 'list'
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Device List
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-3">
            {viewMode === 'topology' ? (
              <div className="card-dark p-8">
                <div className="text-center py-16">
                  <Network className="w-16 h-16 text-purple-400 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">Network Topology View</h3>
                  <p className="text-slate-400 mb-6">Interactive network visualization coming soon</p>
                  
                  {/* Simplified topology grid */}
                  <div className="max-w-2xl mx-auto">
                    <div className="grid grid-cols-3 gap-8">
                      {topology.devices.slice(0, 9).map((device) => (
                        <div
                          key={device.id}
                          onClick={() => setSelectedDevice(device)}
                          className="group cursor-pointer"
                        >
                          <div className={`p-4 rounded-xl border transition-all duration-300 hover:scale-105 ${
                            device.is_online 
                              ? 'border-green-500/30 bg-green-500/10 hover:border-green-400/50' 
                              : 'border-red-500/30 bg-red-500/10 hover:border-red-400/50'
                          }`}>
                            <div className="flex flex-col items-center space-y-2">
                              <div className="text-white group-hover:text-purple-300">
                                {getDeviceIcon(device.device_type)}
                              </div>
                              <span className="text-sm text-slate-300 font-medium">
                                {device.hostname}
                              </span>
                              <span className="text-xs text-slate-500">
                                {device.ip_address}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="card-dark">
                <div className="p-6 border-b border-slate-700">
                  <h3 className="text-lg font-semibold text-white">Network Devices</h3>
                </div>
                <div className="divide-y divide-slate-700">
                  {topology.devices.map((device) => (
                    <div
                      key={device.id}
                      onClick={() => setSelectedDevice(device)}
                      className="p-6 hover:bg-slate-800/50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="text-purple-400">
                            {getDeviceIcon(device.device_type)}
                          </div>
                          <div>
                            <h4 className="font-medium text-white">{device.hostname}</h4>
                            <div className="flex items-center space-x-4 text-sm text-slate-400">
                              <span>{device.ip_address}</span>
                              <span>•</span>
                              <span>{device.device_type}</span>
                              {device.location && (
                                <>
                                  <span>•</span>
                                  <span>{device.location}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm ${getStatusColor(device.is_online, device.vulnerability_score)}`}>
                            {getStatusIcon(device.is_online, device.vulnerability_score)}
                            <span>
                              {!device.is_online ? 'Offline' : 
                               device.vulnerability_score > 7 ? 'Vulnerable' : 'Healthy'}
                            </span>
                          </div>
                          <div className="text-slate-400">
                            <Eye className="w-4 h-4" />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Network Stats */}
            <div className="card-dark p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Network Overview</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Total Devices</span>
                  <span className="text-white font-medium">{topology.devices.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Online</span>
                  <span className="text-green-400 font-medium">
                    {topology.devices.filter(d => d.is_online).length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Offline</span>
                  <span className="text-red-400 font-medium">
                    {topology.devices.filter(d => !d.is_online).length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Vulnerable</span>
                  <span className="text-orange-400 font-medium">
                    {topology.devices.filter(d => d.vulnerability_score > 7).length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Connections</span>
                  <span className="text-white font-medium">{topology.connections.length}</span>
                </div>
              </div>
            </div>

            {/* Selected Device Details */}
            {selectedDevice && (
              <div className="card-dark p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Device Details</h3>
                  <button
                    onClick={() => setSelectedDevice(null)}
                    className="text-slate-400 hover:text-slate-300"
                  >
                    ×
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-400 text-sm">Hostname</span>
                    <p className="text-white font-medium">{selectedDevice.hostname}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 text-sm">IP Address</span>
                    <p className="text-white font-medium">{selectedDevice.ip_address}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 text-sm">Device Type</span>
                    <p className="text-white font-medium">{selectedDevice.device_type}</p>
                  </div>
                  {selectedDevice.os_info && (
                    <div>
                      <span className="text-slate-400 text-sm">OS Info</span>
                      <p className="text-white font-medium">{selectedDevice.os_info}</p>
                    </div>
                  )}
                  {selectedDevice.vendor && (
                    <div>
                      <span className="text-slate-400 text-sm">Vendor</span>
                      <p className="text-white font-medium">{selectedDevice.vendor}</p>
                    </div>
                  )}
                  <div>
                    <span className="text-slate-400 text-sm">Vulnerability Score</span>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-slate-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            selectedDevice.vulnerability_score > 7 ? 'bg-red-500' :
                            selectedDevice.vulnerability_score > 4 ? 'bg-orange-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${(selectedDevice.vulnerability_score / 10) * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-white font-medium text-sm">
                        {selectedDevice.vulnerability_score}/10
                      </span>
                    </div>
                  </div>
                  {selectedDevice.last_seen_at && (
                    <div>
                      <span className="text-slate-400 text-sm">Last Seen</span>
                      <p className="text-white font-medium">
                        {new Date(selectedDevice.last_seen_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
                
                <div className="mt-6 space-y-2">
                  <button className="w-full btn-secondary flex items-center justify-center space-x-2">
                    <Activity className="w-4 h-4" />
                    <span>View Traffic</span>
                  </button>
                  <button className="w-full btn-secondary flex items-center justify-center space-x-2">
                    <Settings className="w-4 h-4" />
                    <span>Configure</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
