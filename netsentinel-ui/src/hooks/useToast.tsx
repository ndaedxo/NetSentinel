import { createContext, useContext, useState, ReactNode } from 'react';
import { ToastMessage, ToastContainer } from '../components/Toast';

interface ToastContextType {
  toasts: ToastMessage[];
  showToast: (type: 'success' | 'error' | 'warning', message: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (type: 'success' | 'error' | 'warning', message: string, duration?: number) => {
    const id = Math.random().toString(36).substring(2, 9);
    const toast: ToastMessage = {
      id,
      type,
      message,
      duration
    };

    setToasts(prev => [...prev, toast]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toasts, showToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
