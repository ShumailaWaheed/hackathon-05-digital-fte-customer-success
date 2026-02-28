/**
 * T035: Polls GET /api/support/{ticket_id}/status every 2s.
 *
 * Shows loading spinner while processing, displays response when ready,
 * shows escalation message if escalated.
 */

"use client";

import { useEffect, useState } from "react";
import { getTicketStatus, type TicketStatus } from "@/lib/api";
import StatusIndicator from "./StatusIndicator";

interface ResponseDisplayProps {
  ticketId: string;
}

const POLL_INTERVAL = 2000; // 2 seconds
const MAX_POLLS = 150; // 5 minutes max (150 * 2s)

export default function ResponseDisplay({ ticketId }: ResponseDisplayProps) {
  const [status, setStatus] = useState<TicketStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;

      try {
        const data = await getTicketStatus(ticketId);
        if (cancelled) return;

        setStatus(data);
        setPollCount((c) => c + 1);

        // Keep polling only if still processing
        if (data.status === "processing" && pollCount < MAX_POLLS) {
          timer = setTimeout(poll, POLL_INTERVAL);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to get status");
      }
    };

    poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [ticketId, pollCount]);

  if (error) {
    return (
      <div className="response-display error">
        <p>Error: {error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="response-display loading">
        <StatusIndicator status="processing" />
      </div>
    );
  }

  return (
    <div className="response-display">
      <StatusIndicator status={status.status} />

      {status.status === "responded" && status.response && (
        <div className="response-content">
          <h3>Response</h3>
          <div className="response-text">{status.response}</div>
        </div>
      )}

      {status.status === "escalated" && (
        <div className="escalation-notice">
          <h3>Escalated to Human Agent</h3>
          <p>
            {status.response ||
              "Your request has been escalated to a human agent who will follow up with you shortly."}
          </p>
        </div>
      )}

      <p className="ticket-ref">Ticket ID: {ticketId}</p>
    </div>
  );
}
