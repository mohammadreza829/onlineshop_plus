"use client";
import { useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { X } from "lucide-react";
export function Sheet({
  title,
  trigger,
  children,
}: {
  title: string;
  trigger: ReactNode;
  children: ReactNode | ((close: () => void) => ReactNode);
}) {
  const [open, setOpen] = useState(false),
    reduced = useReducedMotion();
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay forceMount asChild>
              <motion.div
                className="overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: reduced ? 0 : 0.2 }}
              />
            </Dialog.Overlay>
            <Dialog.Content forceMount asChild aria-describedby={undefined}>
              <motion.div
                dir="rtl"
                className="sheet"
                initial={{ x: reduced ? 0 : "100%" }}
                animate={{ x: 0 }}
                exit={{ x: reduced ? 0 : "100%" }}
                transition={{ duration: reduced ? 0 : 0.24, ease: "easeOut" }}
              >
                <div className="sheet-head">
                  <Dialog.Title className="sheet-title">{title}</Dialog.Title>
                  <Dialog.Close asChild>
                    <button className="icon-button" aria-label="بستن">
                      <X size={22} />
                    </button>
                  </Dialog.Close>
                </div>
                {typeof children === "function"
                  ? children(() => setOpen(false))
                  : children}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
