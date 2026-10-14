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
import { AnimatePresence, motion, MotionConfig } from "motion/react";
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
      <MotionConfig reducedMotion="user">
        <ToastContext.Provider value={toast}>
          {children}
          <div className="toasts" aria-live="polite">
            <AnimatePresence>
              {message && (
                <motion.div
                  className="toast"
                  initial={{ y: 12, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ opacity: 0 }}
                  key={message}
                >
                  {message}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </ToastContext.Provider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
