import { useState, useEffect } from "react";
import { NotificationItem, NotificationType, NotificationPriority } from "@/mock";
import { useApi } from "@/hooks";
import { PageLayout, ConfirmationModal } from "@/components";
import {
  Bell,
  CheckCircle,
  AlertTriangle,
  Trash2,
  Filter,
  Search,
  CheckCheck,
  Clock,
  Shield,
  Activity,
  FileText,
  Settings,
  Zap
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function NotificationsPage() {
  const { data: notificationsResponse } = useApi<{ notifications: NotificationItem[], total: number, unread: number }>(
    "/api/notifications",
    30000
  );

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [filteredNotifications, setFilteredNotifications] = useState<NotificationItem[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<NotificationType | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<NotificationPriority | 'all'>('all');
  const [readFilter, setReadFilter] = useState<'all' | 'read' | 'unread'>('all');
  const [confirmDelete, setConfirmDelete] = useState<{ isOpen: boolean; notificationId: string; notificationTitle: string }>({
    isOpen: false,
    notificationId: '',
    notificationTitle: ''
  });

  useEffect(() => {
    if (notificationsResponse) {
      setNotifications(notificationsResponse.notifications);
    }
  }, [notificationsResponse]);

  useEffect(() => {
    let filtered = notifications;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(n =>
        n.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        n.message.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(n => n.type === typeFilter);
    }

    // Apply priority filter
    if (priorityFilter !== 'all') {
      filtered = filtered.filter(n => n.priority === priorityFilter);
    }

    // Apply read status filter
    if (readFilter !== 'all') {
      filtered = filtered.filter(n => readFilter === 'read' ? n.read : !n.read);
    }

    setFilteredNotifications(filtered);
  }, [notifications, searchTerm, typeFilter, priorityFilter, readFilter]);

  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case 'threat': return <Shield className="w-4 h-4" />;
      case 'system': return <Settings className="w-4 h-4" />;
      case 'alert': return <AlertTriangle className="w-4 h-4" />;
      case 'report': return <FileText className="w-4 h-4" />;
      case 'maintenance': return <Activity className="w-4 h-4" />;
      case 'security': return <Shield className="w-4 h-4" />;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  const getPriorityColor = (priority: NotificationPriority) => {
    switch (priority) {
      case 'critical': return 'text-red-400 bg-red-500/20 border-red-500/30';
      case 'high': return 'text-orange-400 bg-orange-500/20 border-orange-500/30';
      case 'medium': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      case 'low': return 'text-blue-400 bg-blue-500/20 border-blue-500/30';
    }
  };

  const markAsRead = async (id: string) => {
    try {
      // Mock API call
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, read: true } : n)
      );
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      // Mock API call
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  };

  const onDeleteClick = (id: string, title: string) => {
    setConfirmDelete({ isOpen: true, notificationId: id, notificationTitle: title });
  };

  const onConfirmDelete = async () => {
    try {
      // Mock API call
      setNotifications(prev => prev.filter(n => n.id !== confirmDelete.notificationId));
      setConfirmDelete({ isOpen: false, notificationId: '', notificationTitle: '' });
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  };

  const onCancelDelete = () => {
    setConfirmDelete({ isOpen: false, notificationId: '', notificationTitle: '' });
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  if (!notificationsResponse) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-slate-400">Loading notifications...</p>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500 blur-lg opacity-30"></div>
              <Bell className="relative w-8 h-8 text-blue-400" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Notifications</h1>
              <p className="text-slate-400">Stay updated with system alerts and activities</p>
            </div>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              <CheckCheck className="w-4 h-4" />
              <span>Mark All Read</span>
            </button>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card-dark p-6 bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Total</p>
              <Bell className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white">{notifications.length}</p>
          </div>
          <div className="card-dark p-6 bg-gradient-to-br from-red-500/20 to-red-600/10 border-red-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Unread</p>
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <p className="text-3xl font-bold text-white">{unreadCount}</p>
          </div>
          <div className="card-dark p-6 bg-gradient-to-br from-orange-500/20 to-orange-600/10 border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">High Priority</p>
              <Zap className="w-5 h-5 text-orange-400" />
            </div>
            <p className="text-3xl font-bold text-white">
              {notifications.filter(n => n.priority === 'high' || n.priority === 'critical').length}
            </p>
          </div>
          <div className="card-dark p-6 bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Today</p>
              <Clock className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white">
              {notifications.filter(n => {
                const today = new Date();
                const notificationDate = new Date(n.createdAt);
                return notificationDate.toDateString() === today.toDateString();
              }).length}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="card-dark p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search notifications..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-slate-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as NotificationType | 'all')}
                className="px-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              >
                <option value="all">All Types</option>
                <option value="threat">Threat</option>
                <option value="system">System</option>
                <option value="alert">Alert</option>
                <option value="report">Report</option>
                <option value="maintenance">Maintenance</option>
                <option value="security">Security</option>
              </select>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as NotificationPriority | 'all')}
                className="px-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              >
                <option value="all">All Priorities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select
                value={readFilter}
                onChange={(e) => setReadFilter(e.target.value as 'all' | 'read' | 'unread')}
                className="px-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              >
                <option value="all">All Status</option>
                <option value="unread">Unread</option>
                <option value="read">Read</option>
              </select>
            </div>
          </div>
        </div>

        {/* Notifications List */}
        <div className="space-y-4">
          {filteredNotifications.length === 0 ? (
            <div className="card-dark p-12 text-center">
              <Bell className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-400 mb-2">No notifications found</h3>
              <p className="text-slate-500">Try adjusting your filters or check back later.</p>
            </div>
          ) : (
            filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className={`card-dark p-6 border-l-4 transition-all hover:bg-slate-800/50 ${
                  notification.read ? 'opacity-75' : ''
                } ${
                  notification.priority === 'critical' ? 'border-l-red-500' :
                  notification.priority === 'high' ? 'border-l-orange-500' :
                  notification.priority === 'medium' ? 'border-l-yellow-500' :
                  'border-l-blue-500'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className={`p-2 rounded-lg ${getPriorityColor(notification.priority)}`}>
                      {getTypeIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="text-lg font-semibold text-white truncate">
                          {notification.title}
                        </h3>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        )}
                      </div>
                      <p className="text-slate-400 mb-2">{notification.message}</p>
                      <div className="flex items-center space-x-4 text-xs text-slate-500">
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}</span>
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${
                          notification.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                          notification.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                          notification.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-blue-500/20 text-blue-400'
                        }`}>
                          {notification.priority}
                        </span>
                        <span className="capitalize text-slate-500">
                          {notification.type.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    {!notification.read && (
                      <button
                        onClick={() => markAsRead(notification.id)}
                        className="p-2 text-slate-400 hover:text-blue-400 transition-colors"
                        title="Mark as read"
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => onDeleteClick(notification.id, notification.title)}
                      className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete notification"
                      aria-label={`Delete notification: ${notification.title}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {notification.metadata?.actionUrl && (
                  <div className="mt-4 pt-4 border-t border-slate-700">
                    <a
                      href={notification.metadata.actionUrl}
                      className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                    >
                      View Details →
                    </a>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Load More (if needed) */}
        {filteredNotifications.length > 0 && (
          <div className="text-center">
            <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors">
              Load More Notifications
            </button>
          </div>
        )}
      </div>

      <ConfirmationModal
        isOpen={confirmDelete.isOpen}
        onClose={onCancelDelete}
        onConfirm={onConfirmDelete}
        title="Delete Notification"
        message={`Are you sure you want to delete the notification "${confirmDelete.notificationTitle}"? This action cannot be undone.`}
        confirmText="Delete Notification"
        cancelText="Cancel"
        type="delete"
      />
    </PageLayout>
  );
}
