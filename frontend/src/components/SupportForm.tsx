"use client";

import { useState } from "react";
import { z } from "zod";
import { submitSupportForm, type SupportFormData } from "@/lib/api";
import { showToast } from "./Toast";

const CATEGORIES = [
  { value: "billing-inquiry", label: "Billing Inquiry" },
  { value: "technical-issue", label: "Technical Issue" },
  { value: "feature-request", label: "Feature Request" },
  { value: "account-help", label: "Account Help" },
  { value: "general-question", label: "General Question" },
];

const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  email: z.string().email("Please enter a valid email address"),
  category: z.enum([
    "billing-inquiry",
    "technical-issue",
    "feature-request",
    "account-help",
    "general-question",
  ]),
  message: z.string().min(1, "Message is required").max(10000),
});

interface SupportFormProps {
  onSubmitted: (ticketId: string, message: string) => void;
}

export default function SupportForm({ onSubmitted }: SupportFormProps) {
  const [formData, setFormData] = useState<SupportFormData>({
    name: "",
    email: "",
    category: "general-question",
    message: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const result = formSchema.safeParse(formData);
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as string;
        if (!fieldErrors[key]) {
          fieldErrors[key] = issue.message;
        }
      }
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setSubmitting(true);

    try {
      const response = await submitSupportForm(formData);
      showToast("Ticket created! Processing your request...", "info");
      onSubmitted(response.ticket_id, formData.message);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to submit form"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="glass-card">
      <form onSubmit={handleSubmit} className="support-form">
        <div className="form-group">
          <label htmlFor="name">Your Name</label>
          <input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            placeholder="Enter your full name"
            disabled={submitting}
          />
          {errors.name && <span className="error">{errors.name}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="you@example.com"
            disabled={submitting}
          />
          {errors.email && <span className="error">{errors.email}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="category">Issue Category</label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
            disabled={submitting}
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
          {errors.category && <span className="error">{errors.category}</span>}
        </div>

        <div className="form-group">
          <label htmlFor="message">Your Message</label>
          <textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleChange}
            placeholder="Describe your issue or question in detail..."
            rows={5}
            disabled={submitting}
          />
          <span className="char-count">{formData.message.length} / 10,000</span>
          {errors.message && <span className="error">{errors.message}</span>}
        </div>

        {submitError && <div className="submit-error">{submitError}</div>}

        <button type="submit" className="submit-btn" disabled={submitting}>
          <span className="btn-content">
            {submitting ? (
              <>
                <span className="btn-spinner" />
                Processing...
              </>
            ) : (
              "Send Message"
            )}
          </span>
        </button>
      </form>
    </div>
  );
}
