"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getDailyReport,
  getHealthStatus,
  getPendingApprovals,
  approveResponse,
  rejectResponse,
  getAdminTickets,
  getAdminStats,
  type DailyReport,
  type PendingApproval,
  type AdminTicket,
  type AdminStats,
} from "@/lib/api";
import Link from "next/link";
import ThemeToggle, { useTheme } from "@/components/ThemeToggle";
import ToastContainer, { showToast } from "@/components/Toast";

type Tab = "overview" | "approvals" | "tickets";

function StatCard({
  label,
  value,
  sub,
  color,
  icon,
  highlight,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color: string;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={`stat-card ${highlight ? "stat-card-highlight" : ""}`}>
      <div className="stat-icon" style={{ background: color }}>
        {icon}
      </div>
      <div className="stat-info">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
        {sub && <span className="stat-sub">{sub}</span>}
      </div>
    </div>
  );
}

function BarChart({
  data,
  max,
}: {
  data: { label: string; value: number; color: string }[];
  max: number;
}) {
  return (
    <div className="bar-chart">
      {data.map((d) => (
        <div key={d.label} className="bar-row">
          <span className="bar-label">{d.label}</span>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${max > 0 ? (d.value / max) * 100 : 0}%`,
                background: d.color,
              }}
            />
          </div>
          <span className="bar-value">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

function SentimentGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const angle = value * 180 - 90;
  let color = "#f43f5e";
  if (pct >= 70) color = "#10b981";
  else if (pct >= 40) color = "#f59e0b";

  return (
    <div className="gauge-container">
      <svg viewBox="0 0 200 120" className="gauge-svg">
        <path
          d="M20 100 A80 80 0 0 1 180 100"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M20 100 A80 80 0 0 1 180 100"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${value * 251.2} 251.2`}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
        <line
          x1="100"
          y1="100"
          x2={100 + 60 * Math.cos((angle * Math.PI) / 180)}
          y2={100 + 60 * Math.sin((angle * Math.PI) / 180)}
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx="100" cy="100" r="4" fill="white" />
        <text x="100" y="90" textAnchor="middle" fill="white" fontSize="24" fontWeight="bold">
          {pct}%
        </text>
        <text x="100" y="110" textAnchor="middle" fill="#94a3b8" fontSize="11">
          Avg Sentiment
        </text>
      </svg>
    </div>
  );
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function channelIcon(channel: string) {
  switch (channel) {
    case "gmail":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
        </svg>
      );
    case "whatsapp":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
      );
    default:
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      );
  }
}

function priorityClass(priority: string) {
  switch (priority) {
    case "urgent": return "priority-urgent";
    case "high": return "priority-high";
    case "medium": return "priority-medium";
    default: return "priority-low";
  }
}

function statusClass(status: string) {
  switch (status) {
    case "resolved":
    case "closed": return "ticket-status-resolved";
    case "escalated": return "ticket-status-escalated";
    case "pending_approval": return "ticket-status-pending";
    case "open":
    case "in-progress": return "ticket-status-open";
    default: return "ticket-status-open";
  }
}

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [report, setReport] = useState<DailyReport | null>(null);
  const [health, setHealth] = useState<{ status: string; checks: Record<string, string> } | null>(null);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [tickets, setTickets] = useState<AdminTicket[]>([]);
  const [ticketFilter, setTicketFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [expandedApproval, setExpandedApproval] = useState<string | null>(null);
  const { dark, toggle } = useTheme();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        getAdminStats(),
        getDailyReport(),
        getHealthStatus(),
        getPendingApprovals(),
        getAdminTickets(),
      ]);
      if (results[0].status === "fulfilled") setStats(results[0].value);
      if (results[1].status === "fulfilled") setReport(results[1].value);
      if (results[2].status === "fulfilled") setHealth(results[2].value);
      if (results[3].status === "fulfilled") setApprovals(results[3].value);
      if (results[4].status === "fulfilled") setTickets(results[4].value);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleApprove = async (ticketId: string) => {
    setApprovingId(ticketId);
    try {
      await approveResponse(ticketId);
      showToast("Response approved and sent!", "success");
      setApprovals((prev) => prev.filter((a) => a.ticket_id !== ticketId));
      if (stats) setStats({ ...stats, pending_approval: stats.pending_approval - 1, resolved: stats.resolved + 1 });
    } catch (e: unknown) {
      showToast(`Approval failed: ${e instanceof Error ? e.message : "Unknown error"}`, "error");
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (ticketId: string) => {
    setRejectingId(ticketId);
    try {
      await rejectResponse(ticketId);
      showToast("Response rejected", "info");
      setApprovals((prev) => prev.filter((a) => a.ticket_id !== ticketId));
      if (stats) setStats({ ...stats, pending_approval: stats.pending_approval - 1, open: stats.open + 1 });
    } catch (e: unknown) {
      showToast(`Rejection failed: ${e instanceof Error ? e.message : "Unknown error"}`, "error");
    } finally {
      setRejectingId(null);
    }
  };

  const loadFilteredTickets = async (status: string) => {
    setTicketFilter(status);
    try {
      const data = await getAdminTickets(status || undefined);
      setTickets(data);
    } catch {
      /* ignore */
    }
  };

  const channelData = report?.channel_breakdown
    ? Object.entries(report.channel_breakdown).map(([ch, data]) => ({
        label: ch.charAt(0).toUpperCase() + ch.slice(1),
        value: data.count,
        color: ch === "webform" ? "#6366f1" : ch === "gmail" ? "#f43f5e" : "#10b981",
      }))
    : [];
  const channelMax = Math.max(...channelData.map((c) => c.value), 1);

  const issueData = (report?.top_issues || []).map((i, idx) => ({
    label: (i.reason || "Unknown").length > 25 ? (i.reason || "Unknown").slice(0, 25) + "..." : i.reason || "Unknown",
    value: i.count || 0,
    color: ["#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b", "#f43f5e"][idx % 5],
  }));
  const issueMax = Math.max(...issueData.map((i) => i.value), 1);

  return (
    <>
      <ToastContainer />

      <div className="particles" aria-hidden="true">
        <div className="particle" />
        <div className="particle" />
        <div className="particle" />
        <div className="particle" />
        <div className="particle" />
      </div>

      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="navbar-inner">
          <Link href="/" className="navbar-brand">
            <div className="navbar-logo">
              <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <defs>
                  <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#a5b4fc" />
                    <stop offset="100%" stopColor="#22d3ee" />
                  </linearGradient>
                </defs>
                <path d="M12 2C6.48 2 2 6.03 2 10.94c0 2.74 1.41 5.18 3.6 6.8-.16 1.67-.82 3.13-1.72 4.26h.12c2.37 0 4.47-1.02 5.93-2.5.68.1 1.38.16 2.07.16 5.52 0 10-4.03 10-8.72S17.52 2 12 2z" fill="url(#logoGrad)" opacity="0.9" />
                <circle cx="8" cy="11" r="1.25" fill="white" />
                <circle cx="12" cy="11" r="1.25" fill="white" />
                <circle cx="16" cy="11" r="1.25" fill="white" />
              </svg>
            </div>
            <span className="navbar-title">Digital FTE</span>
          </Link>

          <div className="navbar-links">
            <Link href="/" className="nav-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              Support
            </Link>
            <Link href="/admin" className="nav-link active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="m19 9-5 5-4-4-3 3" />
              </svg>
              Dashboard
            </Link>
          </div>

          <ThemeToggle dark={dark} toggle={toggle} />
        </div>
      </nav>

      <main className="container dashboard-container">
        {/* Dashboard Header */}
        <div className="dash-header">
          <div className="dash-header-left">
            <div className="dash-icon">
              <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <defs>
                  <linearGradient id="dashGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#818cf8" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
                <rect x="3" y="3" width="18" height="18" rx="3" fill="url(#dashGrad)" opacity="0.12" stroke="url(#dashGrad)" strokeWidth="1.5" />
                <path d="M8 16V12" stroke="url(#dashGrad)" strokeWidth="2" strokeLinecap="round" />
                <path d="M12 16V8" stroke="url(#dashGrad)" strokeWidth="2" strokeLinecap="round" />
                <path d="M16 16V10" stroke="url(#dashGrad)" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <h1 className="dash-title">Command Center</h1>
              <p className="dash-subtitle">Approvals, tickets & real-time analytics</p>
            </div>
          </div>
          <button className="refresh-btn" onClick={loadData} disabled={loading}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={loading ? "spin-icon" : ""}>
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="tab-bar">
          <button className={`tab-btn ${activeTab === "overview" ? "tab-active" : ""}`} onClick={() => setActiveTab("overview")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" />
            </svg>
            Overview
          </button>
          <button className={`tab-btn ${activeTab === "approvals" ? "tab-active" : ""}`} onClick={() => setActiveTab("approvals")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            Approvals
            {(stats?.pending_approval ?? 0) > 0 && (
              <span className="tab-badge">{stats?.pending_approval}</span>
            )}
          </button>
          <button className={`tab-btn ${activeTab === "tickets" ? "tab-active" : ""}`} onClick={() => setActiveTab("tickets")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            All Tickets
          </button>
        </div>

        {loading && !stats && (
          <div className="glass-card" style={{ textAlign: "center", padding: "3rem" }}>
            <div className="spinner" style={{ width: 28, height: 28, margin: "0 auto 1rem" }} />
            <p style={{ color: "var(--text-muted)" }}>Loading dashboard...</p>
          </div>
        )}

        {/* ====== OVERVIEW TAB ====== */}
        {activeTab === "overview" && !loading && (
          <div className="tab-content">
            {/* Stats Grid */}
            {stats && (
              <div className="stats-grid">
                <StatCard
                  label="Total Tickets"
                  value={stats.total_tickets}
                  color="rgba(99, 102, 241, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /></svg>}
                />
                <StatCard
                  label="Pending Approval"
                  value={stats.pending_approval}
                  highlight={stats.pending_approval > 0}
                  color="rgba(245, 158, 11, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>}
                />
                <StatCard
                  label="Resolved"
                  value={stats.resolved}
                  color="rgba(16, 185, 129, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>}
                />
                <StatCard
                  label="Escalated"
                  value={stats.escalated}
                  color="rgba(244, 63, 94, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>}
                />
                <StatCard
                  label="Open"
                  value={stats.open}
                  color="rgba(6, 182, 212, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></svg>}
                />
                <StatCard
                  label="Last 24h"
                  value={stats.recent_24h}
                  color="rgba(139, 92, 246, 0.15)"
                  icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>}
                />
              </div>
            )}

            {/* System Health */}
            {health && (
              <div className="glass-card health-card">
                <h2 className="section-title">System Health</h2>
                <div className="health-grid">
                  {Object.entries(health.checks || {}).map(([name, status]) => (
                    <div key={name} className={`health-item ${status === "healthy" ? "healthy" : "unhealthy"}`}>
                      <span className="health-dot" />
                      <span className="health-name">{name}</span>
                      <span className="health-status">{status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Charts */}
            {report && (
              <div className="charts-row">
                <div className="glass-card chart-card">
                  <h2 className="section-title">Sentiment Score</h2>
                  <SentimentGauge value={report.average_sentiment} />
                </div>
                <div className="glass-card chart-card">
                  <h2 className="section-title">Channel Breakdown</h2>
                  {channelData.length > 0 ? (
                    <BarChart data={channelData} max={channelMax} />
                  ) : (
                    <p className="no-data">No channel data available</p>
                  )}
                </div>
              </div>
            )}

            {report && issueData.length > 0 && (
              <div className="glass-card">
                <h2 className="section-title">Top Escalation Reasons</h2>
                <BarChart data={issueData} max={issueMax} />
              </div>
            )}
          </div>
        )}

        {/* ====== APPROVALS TAB ====== */}
        {activeTab === "approvals" && (
          <div className="tab-content">
            <div className="approval-header">
              <h2 className="section-title" style={{ margin: 0 }}>
                Pending Approvals ({approvals.length})
              </h2>
              <p className="approval-desc">
                Review AI-generated responses before they are sent to customers
              </p>
            </div>

            {approvals.length === 0 ? (
              <div className="glass-card empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <h3>All caught up!</h3>
                <p>No responses pending approval right now.</p>
              </div>
            ) : (
              <div className="approval-list">
                {approvals.map((item) => (
                  <div key={item.ticket_id} className="approval-card glass-card">
                    <div className="approval-card-top">
                      <div className="approval-meta">
                        <div className="approval-channel">
                          {channelIcon(item.channel)}
                          <span>{item.channel}</span>
                        </div>
                        <span className={`priority-badge ${priorityClass(item.priority)}`}>
                          {item.priority}
                        </span>
                        <span className="approval-time">{timeAgo(item.created_at)}</span>
                      </div>
                    </div>

                    <div className="approval-customer">
                      <strong>{item.customer_name}</strong>
                      {item.customer_email && (
                        <span className="approval-email">{item.customer_email}</span>
                      )}
                    </div>

                    <div className="approval-issue">
                      <div className="approval-label">Customer Message:</div>
                      <p>{item.issue}</p>
                    </div>

                    {item.ai_response && (
                      <div className="approval-response">
                        <div className="approval-label">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
                            <line x1="9" y1="21" x2="15" y2="21" />
                          </svg>
                          AI Generated Response:
                        </div>
                        <div className={`approval-response-text ${expandedApproval === item.ticket_id ? "expanded" : ""}`}>
                          {item.ai_response}
                        </div>
                        {item.ai_response.length > 200 && (
                          <button
                            className="expand-btn"
                            onClick={() => setExpandedApproval(
                              expandedApproval === item.ticket_id ? null : item.ticket_id
                            )}
                          >
                            {expandedApproval === item.ticket_id ? "Show less" : "Show more"}
                          </button>
                        )}
                      </div>
                    )}

                    <div className="approval-actions">
                      <button
                        className="approve-btn"
                        onClick={() => handleApprove(item.ticket_id)}
                        disabled={approvingId === item.ticket_id || rejectingId === item.ticket_id}
                      >
                        {approvingId === item.ticket_id ? (
                          <span className="btn-spinner" />
                        ) : (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        )}
                        Approve & Send
                      </button>
                      <button
                        className="reject-btn"
                        onClick={() => handleReject(item.ticket_id)}
                        disabled={approvingId === item.ticket_id || rejectingId === item.ticket_id}
                      >
                        {rejectingId === item.ticket_id ? (
                          <span className="btn-spinner" />
                        ) : (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        )}
                        Reject
                      </button>
                    </div>

                    <div className="approval-ticket-id">
                      Ticket: {item.ticket_id.slice(0, 8)}...
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ====== TICKETS TAB ====== */}
        {activeTab === "tickets" && (
          <div className="tab-content">
            <div className="tickets-header">
              <h2 className="section-title" style={{ margin: 0 }}>All Tickets</h2>
              <div className="ticket-filters">
                {["", "open", "in-progress", "pending_approval", "resolved", "escalated"].map((f) => (
                  <button
                    key={f}
                    className={`filter-btn ${ticketFilter === f ? "filter-active" : ""}`}
                    onClick={() => loadFilteredTickets(f)}
                  >
                    {f || "All"}
                  </button>
                ))}
              </div>
            </div>

            {tickets.length === 0 ? (
              <div className="glass-card empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <h3>No tickets found</h3>
                <p>Try changing the filter or check back later.</p>
              </div>
            ) : (
              <div className="tickets-table">
                <div className="tickets-table-header">
                  <span>Customer</span>
                  <span>Channel</span>
                  <span>Issue</span>
                  <span>Priority</span>
                  <span>Status</span>
                  <span>Time</span>
                </div>
                {tickets.map((t) => (
                  <div key={t.ticket_id} className="ticket-row">
                    <div className="ticket-customer">
                      <span className="ticket-name">{t.customer_name}</span>
                      {t.customer_email && <span className="ticket-email">{t.customer_email}</span>}
                    </div>
                    <div className="ticket-channel">
                      {channelIcon(t.channel)}
                      <span>{t.channel}</span>
                    </div>
                    <div className="ticket-issue">{t.issue.length > 60 ? t.issue.slice(0, 60) + "..." : t.issue}</div>
                    <span className={`priority-badge ${priorityClass(t.priority)}`}>{t.priority}</span>
                    <span className={`ticket-status-badge ${statusClass(t.status)}`}>{t.status.replace("_", " ")}</span>
                    <span className="ticket-time">{timeAgo(t.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <footer className="app-footer">
          <div className="powered-by">
            Powered by <span className="ai-tag">AI Digital FTE</span>
          </div>
        </footer>
      </main>
    </>
  );
}
