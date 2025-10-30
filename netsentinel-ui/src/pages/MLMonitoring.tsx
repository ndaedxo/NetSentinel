import { Brain, Activity, TrendingUp, Zap, CheckCircle, AlertCircle } from "lucide-react";
import { PageLayout } from "@/components";
import { useApi } from "@/hooks";
import { MLModel } from "@/types";

export default function MLMonitoring() {
  const { data: models } = useApi<MLModel[]>("/api/ml-models", 10000);

  // Loading state
  if (!models) {
    return (
      <PageLayout>
        <div className="animate-pulse">
          <div className="h-8 bg-slate-700 rounded w-64 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="card-dark p-6">
              <div className="h-16 bg-slate-700 rounded"></div>
            </div>
            <div className="card-dark p-6">
              <div className="h-16 bg-slate-700 rounded"></div>
            </div>
            <div className="card-dark p-6">
              <div className="h-16 bg-slate-700 rounded"></div>
            </div>
            <div className="card-dark p-6">
              <div className="h-16 bg-slate-700 rounded"></div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="card-dark p-6">
              <div className="h-32 bg-slate-700 rounded"></div>
            </div>
          </div>
        </div>
      </PageLayout>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-500/20 text-green-300 border-green-500/30";
      case "training":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
      case "inactive":
        return "bg-slate-500/20 text-slate-300 border-slate-500/30";
      default:
        return "bg-slate-500/20 text-slate-300 border-slate-500/30";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "training":
        return <Activity className="w-4 h-4 text-yellow-400 animate-pulse" />;
      case "inactive":
        return <AlertCircle className="w-4 h-4 text-slate-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <PageLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gradient flex items-center space-x-3">
            <Brain className="w-8 h-8 text-blue-400" />
            <span>Machine Learning Models</span>
          </h1>
          <p className="text-slate-400 mt-2">Monitor AI model performance and anomaly detection</p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card-dark p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Active Models</p>
              <Brain className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white">{models.filter(m => m.status === "active").length}</p>
          </div>
          <div className="card-dark p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Avg Accuracy</p>
              <TrendingUp className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white">
              {(models.reduce((sum, m) => sum + m.accuracy, 0) / models.length).toFixed(1)}%
            </p>
          </div>
          <div className="card-dark p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Total Detections</p>
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">
              {models.reduce((sum, m) => sum + m.detections, 0).toLocaleString()}
            </p>
          </div>
          <div className="card-dark p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Avg Latency</p>
              <Zap className="w-5 h-5 text-yellow-400" />
            </div>
            <p className="text-3xl font-bold text-white">
              {(models.reduce((sum, m) => sum + m.latency, 0) / models.length).toFixed(0)}ms
            </p>
          </div>
        </div>

        {/* Model Cards */}
        <div className="space-y-4">
          {models.map((model) => (
            <div key={model.id} className="card-dark p-6">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <div className="p-3 bg-blue-500/20 rounded-lg">
                    <Brain className="w-6 h-6 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">{model.name}</h3>
                    <p className="text-sm text-slate-400 mt-1">Deep Learning Anomaly Detection</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span className={`inline-flex items-center space-x-2 px-3 py-1 rounded-lg text-sm font-medium border ${getStatusColor(model.status)}`}>
                    {getStatusIcon(model.status)}
                    <span>{model.status.charAt(0).toUpperCase() + model.status.slice(1)}</span>
                  </span>
                  <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium">
                    Configure
                  </button>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Accuracy</p>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-slate-700/50 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-green-500"
                        style={{ width: `${model.accuracy}%` }}
                      ></div>
                    </div>
                    <span className="text-lg font-bold text-white">{model.accuracy}%</span>
                  </div>
                </div>
                <div className="p-4 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Detections</p>
                  <p className="text-lg font-bold text-white">{model.detections.toLocaleString()}</p>
                </div>
                <div className="p-4 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Latency</p>
                  <p className="text-lg font-bold text-white">{model.latency}ms</p>
                </div>
                <div className="p-4 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">False Positive Rate</p>
                  <p className="text-lg font-bold text-white">{model.falsePositiveRate}%</p>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex items-center space-x-3">
                <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors text-sm font-medium">
                  View Details
                </button>
                <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium">
                  Retrain Model
                </button>
                <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm font-medium">
                  Export Metrics
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Performance Chart Placeholder */}
        <div className="card-dark p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Detection Performance (Last 24 Hours)</h2>
          <div className="h-64 flex items-center justify-center bg-slate-900/50 rounded-lg border border-slate-700/50">
            <p className="text-slate-500">Performance chart visualization coming soon</p>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
