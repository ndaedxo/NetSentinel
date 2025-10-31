import React from "react";
import { useAuth } from "@/hooks";
import { Shield, LogOut, Bell, User, Menu, X, Activity } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { HelpButton } from "./HelpGuide";
import PerformanceMonitor from "./PerformanceMonitor";

interface HeaderProps {
  onToggleSidebar?: () => void;
  isSidebarCollapsed?: boolean;
}

export default function Header({ onToggleSidebar, isSidebarCollapsed }: HeaderProps) {
  const { user, logout, isPending } = useAuth();
  const navigate = useNavigate();
  const [showMenu, setShowMenu] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);
  const [showPerformanceMonitor, setShowPerformanceMonitor] = useState(false);
  const location = useLocation();

  const handleNotificationsClick = () => {
    navigate('/notifications');
    setShowMobileNav(false); // Close mobile nav if open
  };

  const isActive = (path: string) => location.pathname === path;

  const navLinks = [
    { path: "/", label: "Dashboard" },
    { path: "/threats", label: "Threats" },
    { path: "/network", label: "Network" },
    { path: "/incidents", label: "Incidents" },
    { path: "/honeypots", label: "Honeypots" },
    { path: "/ml-models", label: "ML Models" },
    { path: "/alerts", label: "Alerts" },
    { path: "/reports", label: "Reports" },
    { path: "/profile", label: "Profile" },
    { path: "/notifications", label: "Notifications" },
    { path: "/correlation", label: "Correlation" },
    { path: "/logs", label: "Logs" },
  ];

  return (
    <>
    <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-50">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <div className="flex items-center">
              <button
                onClick={onToggleSidebar}
                className="hidden md:inline-flex mr-3 p-2 hover:bg-slate-800 rounded-lg transition-colors"
                data-testid="sidebar-toggle"
                title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                <Menu className="w-5 h-5 text-slate-400" />
              </button>
              <Link to="/" className="flex items-center space-x-3" data-tour="dashboard">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 blur-lg opacity-30"></div>
                <Shield className="relative w-8 h-8 text-blue-400" strokeWidth={1.5} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gradient">Netsentinel</h1>
                <p className="text-xs text-slate-500">Security Operations Center</p>
              </div>
              </Link>
            </div>

            {/* Desktop Navigation moved to Sidebar */}
          </div>

        <div className="flex items-center space-x-4">
            {/* Mobile menu button */}
            <button
              onClick={() => setShowMobileNav(!showMobileNav)}
              className="md:hidden p-3 hover:bg-slate-800 rounded-lg transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              data-testid="mobile-menu-toggle"
              aria-label={showMobileNav ? "Close menu" : "Open menu"}
            >
              {showMobileNav ? (
                <X className="w-6 h-6 text-slate-400" />
              ) : (
                <Menu className="w-6 h-6 text-slate-400" />
              )}
            </button>

            <button
              onClick={handleNotificationsClick}
              className={`p-3 hover:bg-slate-800 rounded-lg transition-colors relative min-w-[44px] min-h-[44px] flex items-center justify-center ${
                isActive('/notifications') ? 'bg-blue-500/20 border border-blue-500/30' : ''
              }`}
              title="Notifications"
              aria-label="View notifications"
            >
              <Bell className={`w-5 h-5 ${isActive('/notifications') ? 'text-blue-300' : 'text-slate-400'}`} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>

            <HelpButton />

            <button
              onClick={() => setShowPerformanceMonitor(true)}
              className="p-3 hover:bg-slate-800 rounded-lg transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              title="Performance Monitor"
              aria-label="Performance Monitor"
            >
              <Activity className="w-5 h-5 text-slate-400" />
            </button>

          <div className="relative" data-tour="user-menu">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="flex items-center space-x-3 p-3 hover:bg-slate-800 rounded-lg transition-colors min-h-[44px]"
                aria-label="User menu"
              >
                <div className="text-right hidden md:block">
                  <p className="text-sm font-medium text-slate-300">{user?.name || user?.email}</p>
                  <p className="text-xs text-slate-500">{user?.role || 'Security Analyst'}</p>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                  <User className="w-4 h-4 text-slate-400" />
                </div>
              </button>

              {showMenu && (
                <div className="absolute right-0 mt-2 w-48 card-dark p-2 shadow-xl">
                  <button
                    onClick={async () => {
                      await logout();
                      setShowMenu(false);
                      navigate("/login");
                    }}
                    disabled={isPending}
                    className="w-full flex items-center space-x-2 px-3 py-2 hover:bg-slate-700/50 rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <LogOut className="w-4 h-4 text-slate-400" />
                    <span className="text-sm text-slate-300">Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {showMobileNav && (
          <nav className="md:hidden mt-4 pb-4 border-t border-slate-700/50 pt-4">
            <div className="space-y-2">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setShowMobileNav(false)}
                  className={`block px-4 py-4 rounded-lg text-base font-medium transition-colors min-h-[48px] flex items-center ${
                    isActive(link.path)
                      ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                      : "text-slate-400 hover:text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </nav>
        )}
      </div>
    </header>

    {/* Performance Monitor */}
    <PerformanceMonitor
      isOpen={showPerformanceMonitor}
      onClose={() => setShowPerformanceMonitor(false)}
    />
  </>
  );
}
