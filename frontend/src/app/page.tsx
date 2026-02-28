/**
 * T037: Main page composing SupportForm + ResponseDisplay + StatusIndicator.
 */

"use client";

import { useState } from "react";
import SupportForm from "@/components/SupportForm";
import ResponseDisplay from "@/components/ResponseDisplay";

export default function Home() {
  const [ticketId, setTicketId] = useState<string | null>(null);

  return (
    <main className="container">
      <header>
        <h1>Customer Support</h1>
        <p>How can we help you today?</p>
      </header>

      {!ticketId ? (
        <SupportForm onSubmitted={setTicketId} />
      ) : (
        <div className="result-section">
          <ResponseDisplay ticketId={ticketId} />
          <button
            className="new-request-btn"
            onClick={() => setTicketId(null)}
          >
            Submit Another Request
          </button>
        </div>
      )}
    </main>
  );
}
