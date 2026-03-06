"use client";

import { useState, useEffect } from "react";
import SupportForm from "@/components/SupportForm";
import ResponseDisplay from "@/components/ResponseDisplay";
import ToastContainer from "@/components/Toast";
import ThemeToggle, { useTheme } from "@/components/ThemeToggle";
import ConversationHistory from "@/components/ConversationHistory";
import Link from "next/link";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

export default function Home() {
  const [ticketId, setTicketId] = useState<string | null>(null);
  const [userMessage, setUserMessage] = useState<string>("");
  const [greeting, setGreeting] = useState("Welcome");
  const [transitioning, setTransitioning] = useState(false);
  const { dark, toggle } = useTheme();

  useEffect(() => {
    setGreeting(getGreeting());
  }, []);

  const handleSubmitted = (id: string, message: string) => {
    setTransitioning(true);
    setTimeout(() => {
      setTicketId(id);
      setUserMessage(message);
      setTransitioning(false);
    }, 300);
  };

  const handleReset = () => {
    setTransitioning(true);
    setTimeout(() => {
      setTicketId(null);
      setUserMessage("");
      setTransitioning(false);
    }, 300);
  };

  const handleHistorySelect = (id: string, message: string) => {
    setTransitioning(true);
    setTimeout(() => {
      setTicketId(id);
      setUserMessage(message);
      setTransitioning(false);
    }, 300);
  };

  return (
    <>
      <ToastContainer />

      {/* Floating particles */}
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
            <Link href="/" className="nav-link active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              Support
            </Link>
            <Link href="/admin" className="nav-link">
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

      <main className="container">
        <header>
          <div className="header-logo">
            <div className="header-logo-ring" />
            <svg viewBox="0 0 48 48" fill="none" className="header-logo-svg">
              <defs>
                <linearGradient id="hg1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#a5b4fc" />
                  <stop offset="100%" stopColor="#22d3ee" />
                </linearGradient>
              </defs>
              <path d="M24 4C13.5 4 5 10.7 5 19.2c0 4.8 2.8 9.1 7.2 12-.3 2.9-1.6 5.5-3.4 7.5h.2c4.7 0 8.9-2 11.8-5 1.3.2 2.7.3 4.1.3 10.5 0 19-6.7 19-15.2S34.5 4 24 4z" fill="url(#hg1)" className="header-bubble" />
              <circle cx="15.5" cy="19.5" r="2.2" fill="white" className="header-dot header-dot-1" />
              <circle cx="24" cy="19.5" r="2.2" fill="white" className="header-dot header-dot-2" />
              <circle cx="32.5" cy="19.5" r="2.2" fill="white" className="header-dot header-dot-3" />
            </svg>
          </div>
          <h1 className="hero-title">
            <span className="hero-word hero-word-1">AI</span>{" "}
            <span className="hero-word hero-word-2">Customer</span>{" "}
            <span className="hero-word hero-word-3">Support</span>
          </h1>
          <p className="header-subtitle">{greeting}! How can we help you today?</p>
          <div className="online-badge">
            <span className="online-dot" />
            AI Assistant Online
          </div>
        </header>

        {/* Conversation History */}
        {!ticketId && (
          <ConversationHistory onSelect={handleHistorySelect} />
        )}

        <div className={`page-transition ${transitioning ? "fade-out" : "fade-in"}`}>
          {!ticketId ? (
            <SupportForm onSubmitted={handleSubmitted} />
          ) : (
            <div className="result-section">
              <ResponseDisplay ticketId={ticketId} userMessage={userMessage} />
              <button className="new-request-btn" onClick={handleReset}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Start New Conversation
              </button>
            </div>
          )}
        </div>

        <footer className="app-footer">
          <div className="powered-by">
            Powered by <span className="ai-tag">AI Digital FTE</span>
          </div>
        </footer>
      </main>
    </>
  );
}
