import { Link } from "react-router-dom";

export default function Logo({ to = "/", className = "" }: { to?: string; className?: string }) {
  return (
    <Link to={to} className={`logo-mark ${className}`}>
      <HeartIcon className="logo-heart" />
      <span>QueueFlow</span>
    </Link>
  );
}

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 21s-7.5-4.6-10.2-9.3C0.1 8.7 1.4 5 5 4.1c2.1-0.5 4.1 0.4 5.4 2.3l1.6 2.3 1.6-2.3C14.9 4.5 16.9 3.6 19 4.1c3.6 0.9 4.9 4.6 3.2 7.6C19.5 16.4 12 21 12 21z" />
    </svg>
  );
}
