"use client";
import { useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
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
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content
          data-lenis-prevent
          dir="rtl"
          className="sheet"
          aria-describedby={undefined}
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
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
