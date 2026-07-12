import { Link } from "react-router-dom";

export default function Logo({ to = "/", className = "" }: { to?: string; className?: string }) {
  return (
    <Link to={to} className={`logo-mark ${className}`}>
      <QueueIcon className="logo-queue" />
      <span>QueueFlow</span>
    </Link>
  );
}

function QueueIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" aria-hidden="true">
      <rect width="48" height="48" rx="12" fill="url(#logo-queue-gradient)" />
      <circle className="logo-queue-dot" cx="14" cy="24" r="4.2" fill="#fff" style={{ animationDelay: "0s" }} />
      <circle className="logo-queue-dot" cx="24" cy="24" r="4.2" fill="#fff" style={{ animationDelay: "0.3s" }} />
      <circle className="logo-queue-dot" cx="34" cy="24" r="4.2" fill="#fff" style={{ animationDelay: "0.6s" }} />
      <defs>
        <linearGradient id="logo-queue-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f9a8d4" />
          <stop offset="55%" stopColor="#ec4899" />
          <stop offset="100%" stopColor="#fb7185" />
        </linearGradient>
      </defs>
    </svg>
  );
}
