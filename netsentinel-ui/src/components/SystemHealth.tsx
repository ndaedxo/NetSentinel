import { SystemHealthService } from "@/types";
import { Activity, CheckCircle, AlertCircle, XCircle } from "lucide-react";

interface SystemHealthProps {
  services: SystemHealthService[];
}

export default function SystemHealth({ services }: SystemHealthProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "degraded":
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "text-green-400 bg-green-500/10 border-green-500/30";
      case "degraded":
        return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30";
      case "error":
        return "text-red-400 bg-red-500/10 border-red-500/30";
      default:
        return "text-slate-400 bg-slate-500/10 border-slate-500/30";
    }
  };

  return (
    <div className="card-dark p-6">
      <div className="flex items-center space-x-2 mb-4">
        <Activity className="w-5 h-5 text-blue-400" />
        <h2 className="text-lg font-semibold text-white">System Health</h2>
      </div>

      <div className="space-y-3">
        {services.map((service) => (
          <div
            key={service.name}
            className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg border border-slate-700/30 hover:border-slate-600/50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              {getStatusIcon(service.status)}
              <span className="text-sm font-medium text-slate-300">{service.name}</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(service.status)}`}>
              {service.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
