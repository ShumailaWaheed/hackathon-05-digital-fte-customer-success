"use client";

interface StatusIndicatorProps {
  status: "processing" | "responded" | "escalated";
  currentStep?: number;
}

const STEPS = [
  { label: "Ticket Created", icon: "1" },
  { label: "Analyzing", icon: "2" },
  { label: "Searching KB", icon: "3" },
  { label: "Generating", icon: "4" },
];

export default function StatusIndicator({ status, currentStep = 0 }: StatusIndicatorProps) {
  const isDone = status === "responded" || status === "escalated";
  const activeStep = isDone ? 4 : currentStep;
  const progressPercent = isDone ? 100 : Math.min((activeStep / 3) * 100, 100);

  return (
    <div>
      {/* Progress Stepper - only during processing */}
      {status === "processing" && (
        <div className="progress-stepper">
          <div
            className="progress-line"
            style={{ width: `calc(${progressPercent}% - 40px)` }}
          />
          {STEPS.map((step, idx) => {
            let stepClass = "step step-pending";
            if (idx < activeStep) stepClass = "step step-done";
            else if (idx === activeStep) stepClass = "step step-active";

            return (
              <div key={step.label} className={stepClass}>
                <div className="step-circle">
                  {idx < activeStep ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  ) : (
                    step.icon
                  )}
                </div>
                <span className="step-label">{step.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Status Badge */}
      <div className={`status-indicator status-${status}`}>
        <span className="status-badge">
          {status === "processing" && <span className="spinner" />}
          {status === "responded" && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          )}
          {status === "escalated" && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 9v4M12 17h.01" />
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          )}
          {status === "processing" && "Processing your request..."}
          {status === "responded" && "Response Ready"}
          {status === "escalated" && "Escalated to Human Agent"}
        </span>
      </div>
    </div>
  );
}
