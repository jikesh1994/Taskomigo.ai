// Small line icons for the landing page (24px grid, stroke = currentColor).
import type { ReactNode } from "react";

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="size-5"
    >
      {children}
    </svg>
  );
}

export const icons = {
  copy: (
    <Icon>
      <rect x="8" y="8" width="12" height="12" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </Icon>
  ),
  search: (
    <Icon>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </Icon>
  ),
  robot: (
    <Icon>
      <rect x="4" y="8" width="16" height="12" rx="3" />
      <path d="M12 8V4M9 14h.01M15 14h.01" />
    </Icon>
  ),
  user: (
    <Icon>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </Icon>
  ),
  target: (
    <Icon>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.5" />
    </Icon>
  ),
  form: (
    <Icon>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 8h6M9 12h6M9 16h3" />
    </Icon>
  ),
  hand: (
    <Icon>
      <path d="M8 11V5a1.5 1.5 0 0 1 3 0v5M11 10V4a1.5 1.5 0 0 1 3 0v6M14 10V6a1.5 1.5 0 0 1 3 0v7a7 7 0 0 1-7 7h-.5A6.5 6.5 0 0 1 4 14.5V12a1.5 1.5 0 0 1 3 0v1" />
    </Icon>
  ),
  shield: (
    <Icon>
      <path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" />
      <path d="m9 12 2 2 4-4" />
    </Icon>
  ),
  pause: (
    <Icon>
      <circle cx="12" cy="12" r="9" />
      <path d="M10 9v6M14 9v6" />
    </Icon>
  ),
  check: (
    <Icon>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </Icon>
  ),
  stop: (
    <Icon>
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </Icon>
  ),
  lock: (
    <Icon>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </Icon>
  ),
  chat: (
    <Icon>
      <path d="M4 5h16v11H9l-5 4z" />
      <path d="M8 10h8" />
    </Icon>
  ),
};
