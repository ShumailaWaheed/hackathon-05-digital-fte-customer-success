"use client";

import { useEffect, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { getTicketStatus, type TicketStatus } from "@/lib/api";
import { playNotificationSound } from "@/lib/sound";
import StatusIndicator from "./StatusIndicator";
import SatisfactionRating from "./SatisfactionRating";
import { showToast } from "./Toast";
import { saveConversation } from "./ConversationHistory";

interface ResponseDisplayProps {
  ticketId: string;
  userMessage?: string;
}

const POLL_INTERVAL = 2000;
const MAX_POLLS = 150;

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Typewriter hook: reveals text character by character */
function useTypewriter(text: string, speed: number = 14) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!text) return;
    setDisplayed("");
    setDone(false);
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(timer);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);

  return { displayed, done };
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      showToast("Ticket ID copied!", "success");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button onClick={handleCopy} className={`copy-btn ${copied ? "copied" : ""}`}>
      {copied ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><path d="M20 6L9 17l-5-5" /></svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg>
      )}
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

export default function ResponseDisplay({ ticketId, userMessage }: ResponseDisplayProps) {
  const [status, setStatus] = useState<TicketStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const submitTime = useRef(new Date());
  const responseTime = useRef<Date | null>(null);
  const hasNotified = useRef(false);

  // Simulate progress steps during processing
  useEffect(() => {
    if (status?.status !== "processing" && status !== null) return;
    const timers = [
      setTimeout(() => setStep(1), 800),
      setTimeout(() => setStep(2), 2500),
      setTimeout(() => setStep(3), 5000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [status]);

  // Toast + sound notification when response arrives, save to history
  useEffect(() => {
    if (!hasNotified.current && status?.status === "responded") {
      hasNotified.current = true;
      responseTime.current = new Date();
      showToast("AI response received!", "success");
      playNotificationSound();
      saveConversation({
        ticketId,
        message: userMessage || "",
        category: "",
        status: "responded",
        response: status.response,
        timestamp: Date.now(),
      });
    }
    if (!hasNotified.current && status?.status === "escalated") {
      hasNotified.current = true;
      responseTime.current = new Date();
      showToast("Escalated to human agent", "info");
      playNotificationSound();
      saveConversation({
        ticketId,
        message: userMessage || "",
        category: "",
        status: "escalated",
        response: status.response,
        timestamp: Date.now(),
      });
    }
  }, [status?.status, ticketId, userMessage]);

  // Polling
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;
    let polls = 0;

    const poll = async () => {
      if (cancelled) return;
      try {
        const data = await getTicketStatus(ticketId);
        if (cancelled) return;
        setStatus(data);
        polls += 1;
        if (data.status === "processing" && polls < MAX_POLLS) {
          timer = setTimeout(poll, POLL_INTERVAL);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to get status");
      }
    };

    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [ticketId]);

  const responseText = status?.response || "";
  const { displayed: typedText, done: typingDone } = useTypewriter(
    status?.status === "responded" ? responseText : ""
  );

  const isFinished = status?.status === "responded" || status?.status === "escalated";

  if (error) {
    return (
      <div className="glass-card">
        <div className="submit-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="glass-card response-display">
      <StatusIndicator
        status={status?.status || "processing"}
        currentStep={step}
      />

      <div className="chat-container">
        {/* User message bubble */}
        {userMessage && (
          <div className="chat-bubble user">
            <div className="chat-timestamp">{formatTime(submitTime.current)}</div>
            {userMessage}
          </div>
        )}

        {/* AI response bubble */}
        {status?.status === "responded" && (
          <div className="chat-bubble ai">
            <div className="chat-bubble-header">
              <div className="ai-avatar">AI</div>
              <span className="chat-label">AI Assistant</span>
            </div>
            <div className="ai-response-body">
              <ReactMarkdown>{typedText}</ReactMarkdown>
            </div>
            {!typingDone && (
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            )}
            <div className="chat-timestamp">
              {responseTime.current ? formatTime(responseTime.current) : formatTime(new Date())}
            </div>
          </div>
        )}

        {/* Processing - typing indicator */}
        {status?.status === "processing" && (
          <div className="chat-bubble ai">
            <div className="chat-bubble-header">
              <div className="ai-avatar">AI</div>
              <span className="chat-label">AI Assistant</span>
            </div>
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}

        {/* Escalation notice */}
        {status?.status === "escalated" && (
          <div className="escalation-notice">
            <h3>Escalated to Human Agent</h3>
            <p>
              {status.response ||
                "Your request has been escalated to a human agent who will follow up with you shortly. We want to make sure you get the best possible help."}
            </p>
          </div>
        )}
      </div>

      {/* Satisfaction rating - show when response is complete */}
      {isFinished && typingDone && (
        <SatisfactionRating ticketId={ticketId} />
      )}

      <div className="ticket-ref">
        Ticket: {ticketId.slice(0, 8)}...
        <CopyButton text={ticketId} />
      </div>
    </div>
  );
}
