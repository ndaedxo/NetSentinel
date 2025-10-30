import React from 'react';
import { Link, useLocation } from 'react-router';
import {
  LayoutDashboard,
  ShieldAlert,
  Network as NetworkIcon,
  Shield,
  Bug,
  Brain,
  Bell,
  FileText,
  User,
  Settings,
} from 'lucide-react';

interface SidebarNavProps {
  collapsed: boolean;
}

const navLinks = [
  { path: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { path: '/threats', label: 'Threats', Icon: ShieldAlert },
  { path: '/network', label: 'Network', Icon: NetworkIcon },
  { path: '/incidents', label: 'Incidents', Icon: Shield },
  { path: '/honeypots', label: 'Honeypots', Icon: Bug },
  { path: '/ml-models', label: 'ML Models', Icon: Brain },
  { path: '/alerts', label: 'Alerts', Icon: Bell },
  { path: '/reports', label: 'Reports', Icon: FileText },
  { path: '/profile', label: 'Profile', Icon: User },
  { path: '/notifications', label: 'Notifications', Icon: Settings },
  { path: '/settings/notifications', label: 'Notif Settings', Icon: Bell },
  { path: '/settings/api-keys', label: 'API Keys', Icon: FileText },
  { path: '/correlation', label: 'Correlation', Icon: Brain },
  { path: '/logs', label: 'Logs', Icon: FileText },
];

export default function SidebarNav({ collapsed }: SidebarNavProps) {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  return (
    <aside
      className={`hidden md:flex shrink-0 flex-col border-r border-slate-700/50 bg-slate-900/70 backdrop-blur-md h-screen sticky top-0 z-40 transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex-1 overflow-y-auto">
        <div className={`px-4 pt-4 pb-2 ${collapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'} transition-opacity duration-300`}>
          <p className="text-xs uppercase tracking-wider text-slate-500">Navigation</p>
        </div>
        <nav className="px-2 pb-4 space-y-1">
          {navLinks.map(({ path, label, Icon }) => {
            const active = isActive(path);
            return (
              <Link
                key={path}
                to={path}
                title={label}
                data-testid={`nav-${path === '/' ? 'dashboard' : path.replace('/', '')}`}
                aria-current={active ? 'page' : undefined}
                className={`group relative flex items-center gap-3 ${
                  collapsed ? 'justify-center px-0' : 'px-3'
                } py-2 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
                }`}
              >
                {/* Active indicator bar */}
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-0.5 bg-blue-400 rounded-full" />
                )}
                <Icon className="w-4 h-4 text-slate-400 group-hover:text-slate-300" />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}


