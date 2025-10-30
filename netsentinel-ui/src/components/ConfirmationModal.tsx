import { X, AlertTriangle, Trash2, Info } from 'lucide-react';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info' | 'delete';
  size?: 'sm' | 'md' | 'lg';
}

export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'warning',
  size = 'md'
}: ConfirmationModalProps) {
  if (!isOpen) return null;

  const getIcon = () => {
    switch (type) {
      case 'danger':
      case 'delete':
        return <Trash2 className="w-6 h-6 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="w-6 h-6 text-yellow-400" />;
      case 'info':
        return <Info className="w-6 h-6 text-blue-400" />;
      default:
        return null;
    }
  };

  const getConfirmButtonClass = () => {
    switch (type) {
      case 'danger':
      case 'delete':
        return 'bg-red-600 hover:bg-red-500 focus:ring-red-500';
      case 'warning':
        return 'bg-yellow-600 hover:bg-yellow-500 focus:ring-yellow-500';
      case 'info':
        return 'bg-blue-600 hover:bg-blue-500 focus:ring-blue-500';
      default:
        return 'bg-slate-600 hover:bg-slate-500 focus:ring-slate-500';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'max-w-sm';
      case 'lg':
        return 'max-w-lg';
      default:
        return 'max-w-md';
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter') {
      onConfirm();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirmation-title"
      aria-describedby="confirmation-message"
    >
      <div className={`bg-slate-800 border border-slate-700 rounded-xl ${getSizeClasses()} w-full shadow-2xl`}>
        {/* Header */}
        <div className="p-6 flex items-center justify-between border-b border-slate-700">
          <div className="flex items-center space-x-3">
            {getIcon()}
            <h2 id="confirmation-title" className="text-lg font-bold text-white">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-500"
            aria-label="Close confirmation dialog"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p id="confirmation-message" className="text-slate-300 leading-relaxed">{message}</p>

          {/* Actions */}
          <div className="flex space-x-3 mt-6">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500 rounded-lg transition-colors text-white"
              autoFocus
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className={`flex-1 px-4 py-2 ${getConfirmButtonClass()} focus:outline-none focus:ring-2 rounded-lg transition-colors text-white`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
