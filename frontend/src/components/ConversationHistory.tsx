"use client";

import { useEffect, useState } from "react";

export interface ConversationRecord {
  ticketId: string;
  message: string;
  category: string;
  status: "processing" | "responded" | "escalated";
  response: string | null;
  timestamp: number;
}

const STORAGE_KEY = "cs_conversation_history";
const MAX_HISTORY = 20;

export function saveConversation(record: ConversationRecord) {
  try {
    const existing = getConversations();
    const updated = [record, ...existing.filter((r) => r.ticketId !== record.ticketId)].slice(0, MAX_HISTORY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // localStorage unavailable
  }
}

export function getConversations(): ConversationRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function categoryLabel(cat: string): string {
  return cat
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const statusConfig = {
  responded: { label: "Resolved", icon: "\u2713", cls: "history-status-responded" },
  escalated: { label: "Escalated", icon: "!", cls: "history-status-escalated" },
  processing: { label: "Pending", icon: "\u2026", cls: "history-status-processing" },
};

interface ConversationHistoryProps {
  onSelect: (ticketId: string, message: string) => void;
}

export default function ConversationHistory({ onSelect }: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setConversations(getConversations());
  }, []);

  return (
    <div className="history-wrapper">
      <button className="history-toggle" onClick={() => setOpen(!open)}>
        <div className="history-toggle-left">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 8v4l3 3" />
            <circle cx="12" cy="12" r="10" />
          </svg>
          <span>Recent Conversations</span>
          {conversations.length > 0 && (
            <span className="history-count">{conversations.length}</span>
          )}
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          className={`history-chevron ${open ? "open" : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="history-list">
          {conversations.length === 0 ? (
            <div className="history-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <p>No conversations yet</p>
              <span>Your support history will appear here</span>
            </div>
          ) : (
            conversations.map((c, i) => {
              const cfg = statusConfig[c.status];
              return (
                <button
                  key={c.ticketId}
                  className="history-item"
                  onClick={() => onSelect(c.ticketId, c.message)}
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  <div className="history-item-left">
                    <div className={`history-item-icon ${cfg.cls}`}>
                      {cfg.icon}
                    </div>
                  </div>
                  <div className="history-item-body">
                    <div className="history-item-top">
                      <span className={`history-status ${cfg.cls}`}>
                        {cfg.label}
                      </span>
                      {c.category && (
                        <span className="history-category">{categoryLabel(c.category)}</span>
                      )}
                      <span className="history-time">{timeAgo(c.timestamp)}</span>
                    </div>
                    <p className="history-message">
                      {c.message.length > 90 ? c.message.slice(0, 90) + "..." : c.message}
                    </p>
                    <span className="history-ticket">#{c.ticketId.slice(0, 8)}</span>
                  </div>
                  <div className="history-item-arrow">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
