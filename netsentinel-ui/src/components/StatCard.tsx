// @ts-expect-error - React import needed for tests but not used in component due to JSX transform
import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  color?: "blue" | "red" | "green" | "yellow";
}

export default function StatCard({ title, value, icon: Icon, trend, color = "blue" }: StatCardProps) {
  const colorClasses = {
    blue: "from-blue-500/20 to-blue-600/10 border-blue-500/30 glow-blue",
    red: "from-red-500/20 to-red-600/10 border-red-500/30 glow-red",
    green: "from-green-500/20 to-green-600/10 border-green-500/30 glow-green",
    yellow: "from-yellow-500/20 to-yellow-600/10 border-yellow-500/30 glow-yellow",
  };

  const iconColorClasses = {
    blue: "text-blue-400",
    red: "text-red-400",
    green: "text-green-400",
    yellow: "text-yellow-400",
  };

  return (
    <div className={`card-dark p-6 bg-gradient-to-br ${colorClasses[color]} border transition-all duration-300 hover:scale-[1.02]`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-slate-400 font-medium mb-2">{title}</p>
          <p className="text-3xl font-bold text-white mb-2">{value.toLocaleString()}</p>
          {trend && (
            <p className={`text-sm font-medium ${trend.isPositive ? "text-green-400" : "text-red-400"}`}>
              {trend.isPositive ? "↑" : "↓"} {trend.value}
            </p>
          )}
        </div>
        <div className={`p-3 bg-slate-900/50 rounded-lg ${iconColorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
