import React from "react";
import { AlertType } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { Bell, AlertTriangle } from "lucide-react";
import { getThreatBorderColor } from "@/utils";

interface AlertFeedProps {
  alerts: AlertType[];
}

export default function AlertFeed({ alerts }: AlertFeedProps) {

  const getSeverityIcon = (severity: string) => {
    if (severity === "critical" || severity === "high") {
      return <AlertTriangle className="w-4 h-4 text-red-400" />;
    }
    return <Bell className="w-4 h-4 text-yellow-400" />;
  };

  return (
    <div className="card-dark p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Bell className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Active Alerts</h2>
        </div>
        <span className="px-2 py-1 bg-red-500/20 text-red-300 text-xs font-medium rounded border border-red-500/30">
          {alerts.length} Active
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`p-4 rounded-lg border-l-4 ${getThreatBorderColor(alert.severity)} transition-all hover:scale-[1.01]`}
          >
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-0.5">
                {getSeverityIcon(alert.severity)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-semibold text-white truncate">{alert.title}</h3>
                  <span className="text-xs text-slate-500 ml-2 flex-shrink-0">
                    {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                  </span>
                </div>
                {alert.description && (
                  <p className="text-xs text-slate-400 line-clamp-2">{alert.description}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
