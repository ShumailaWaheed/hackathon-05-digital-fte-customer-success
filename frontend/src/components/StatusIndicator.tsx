/**
 * T036: Visual ticket status indicator.
 *
 * Shows processing → responded/escalated with appropriate messaging.
 */

"use client";

interface StatusIndicatorProps {
  status: "processing" | "responded" | "escalated";
}

export default function StatusIndicator({ status }: StatusIndicatorProps) {
  const config = {
    processing: {
      label: "Processing",
      className: "status-processing",
      message: "Your request is being analyzed by our AI assistant...",
    },
    responded: {
      label: "Responded",
      className: "status-responded",
      message: "We have a response for you!",
    },
    escalated: {
      label: "Escalated",
      className: "status-escalated",
      message: "Your request has been escalated to a human agent.",
    },
  };

  const { label, className, message } = config[status];

  return (
    <div className={`status-indicator ${className}`}>
      <div className="status-badge">
        {status === "processing" && <span className="spinner" />}
        <span className="status-label">{label}</span>
      </div>
      <p className="status-message">{message}</p>
    </div>
  );
}
