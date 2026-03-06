"use client";

import { useEffect, useState, useCallback } from "react";

export interface ToastMessage {
  id: number;
  text: string;
  type: "success" | "info" | "error";
}

let toastId = 0;
let listeners: Array<(t: ToastMessage) => void> = [];

export function showToast(text: string, type: ToastMessage["type"] = "success") {
  const msg: ToastMessage = { id: ++toastId, text, type };
  listeners.forEach((fn) => fn(msg));
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((t: ToastMessage) => {
    setToasts((prev) => [...prev, t]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== t.id));
    }, 3000);
  }, []);

  useEffect(() => {
    listeners.push(addToast);
    return () => {
      listeners = listeners.filter((fn) => fn !== addToast);
    };
  }, [addToast]);

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span className="toast-icon">
            {t.type === "success" && "✓"}
            {t.type === "info" && "ℹ"}
            {t.type === "error" && "✕"}
          </span>
          {t.text}
        </div>
      ))}
    </div>
  );
}
