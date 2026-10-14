"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const ToastContext = createContext<(message: string) => void>(() => {});
export const useToast = () => useContext(ToastContext);
export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: 15000,
            refetchOnWindowFocus: false,
          },
          mutations: { retry: false },
        },
      }),
  );
  const [message, setMessage] = useState("");
  const toast = useCallback((value: string) => setMessage(value), []);
  useEffect(() => {
    if (!message) return;
    const id = setTimeout(() => setMessage(""), 5000);
    return () => clearTimeout(id);
  }, [message]);
  useEffect(() => {
    const channel = new BroadcastChannel("osp-auth");
    channel.onmessage = () => {
      void client.cancelQueries().then(() => client.clear());
    };
    return () => channel.close();
  }, [client]);
  return (
    <QueryClientProvider client={client}>
      <ToastContext.Provider value={toast}>
        {children}
        <div className="toasts" aria-live="polite">
          {message && (
            <div className="toast" key={message}>
              {message}
            </div>
          )}
        </div>
      </ToastContext.Provider>
    </QueryClientProvider>
  );
}
