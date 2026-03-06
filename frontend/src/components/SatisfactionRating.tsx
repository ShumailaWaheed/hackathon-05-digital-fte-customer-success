"use client";

import { useState } from "react";

const RATINGS = [
  { emoji: "😞", label: "Poor", value: 1 },
  { emoji: "😐", label: "Fair", value: 2 },
  { emoji: "🙂", label: "Good", value: 3 },
  { emoji: "😊", label: "Great", value: 4 },
  { emoji: "🤩", label: "Excellent", value: 5 },
];

interface SatisfactionRatingProps {
  ticketId: string;
}

export default function SatisfactionRating({ ticketId }: SatisfactionRatingProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  const handleSelect = (value: number) => {
    setSelected(value);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="rating-container rating-submitted">
        <div className="rating-thanks">
          <span className="rating-thanks-emoji">
            {RATINGS.find((r) => r.value === selected)?.emoji}
          </span>
          <p>Thank you for your feedback!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rating-container">
      <p className="rating-title">How was your experience?</p>
      <div className="rating-options">
        {RATINGS.map((r) => (
          <button
            key={r.value}
            className={`rating-btn ${hovered !== null && hovered >= r.value ? "rating-active" : ""}`}
            onClick={() => handleSelect(r.value)}
            onMouseEnter={() => setHovered(r.value)}
            onMouseLeave={() => setHovered(null)}
            title={r.label}
          >
            <span className="rating-emoji">{r.emoji}</span>
            <span className="rating-label">{r.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
