import { Link } from "react-router-dom";
import Footer from "../components/Footer";
import Logo from "../components/Logo";
import Reveal from "../components/Reveal";
import ThemeToggle from "../components/ThemeToggle";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  { icon: IconShield, title: "Retries that don't give up", body: "Auto-retry with backoff, then a dead letter queue." },
  { icon: IconClock, title: "A scheduler that never forgets", body: "Polls every 10s. No cron jobs to babysit." },
  { icon: IconSparkle, title: "AI-drafted messages", body: "Pick a tone, let AI write the reminder." },
  { icon: IconChart, title: "A dashboard that tells the truth", body: "Live delivery rate, queue depth, worker health." },
  { icon: IconLayers, title: "Queue-backed, not request-backed", body: "10,000 sends won't freeze your API." },
  { icon: IconBuilding, title: "Built for any appointment business", body: "Clinics, gyms, salons, tutors, consultants." },
];

const STEPS = [
  { label: "Create", icon: IconPlus },
  { label: "Schedule", icon: IconClock },
  { label: "Queue", icon: IconLayers },
  { label: "Deliver", icon: IconSend },
];

export default function Landing() {
  const { business } = useAuth();
  const primaryCta = business ? { to: "/dashboard", label: "Go to dashboard" } : { to: "/signup", label: "Get started free" };

  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo className="landing-logo" />
        <nav>
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          {business ? (
            <Link to="/dashboard" className="nav-cta">
              Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/signup" className="nav-cta">
                Sign up
              </Link>
            </>
          )}
          <ThemeToggle />
        </nav>
      </header>

      <section className="hero">
        <div className="hero-blob" aria-hidden="true" />
        <div className="hero-badge fade-in-up" style={{ animationDelay: "0ms" }}>
          Reminder &amp; workflow automation
        </div>
        <h1 className="fade-in-up" style={{ animationDelay: "80ms" }}>
          Reminders that <span className="gradient-text">actually get delivered.</span>
        </h1>
        <p className="hero-sub fade-in-up" style={{ animationDelay: "160ms" }}>
          Your receptionist can't call 400 patients by hand. QueueFlow schedules, queues, sends, retries, and
          tracks every reminder — reliably, with a dashboard that shows exactly what happened.
        </p>
        <div className="hero-actions fade-in-up" style={{ animationDelay: "240ms" }}>
          <Link to={primaryCta.to} className="btn-primary">
            {primaryCta.label}
          </Link>
          <a href="#how-it-works" className="btn-secondary">
            See how it works
          </a>
        </div>
        <div className="hero-pipeline fade-in-up" style={{ animationDelay: "320ms" }} aria-hidden="true">
          {["Create", "Schedule", "Queue", "Deliver"].map((step, i) => (
            <div className="pipeline-step" key={step} style={{ animationDelay: `${900 + i * 260}ms` }}>
              <span className="pipeline-dot">{i + 1}</span>
              <span>{step}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="problem">
        <Reveal className="problem-inner">
          <h2>The problem isn't messaging. It's reliability.</h2>
          <p>QueueFlow isn't an SMS app — it's a job queue with retries and a dead letter safety net built in.</p>
        </Reveal>
      </section>

      <section id="features" className="features">
        <Reveal>
          <h2>Everything a reminder needs to actually land</h2>
        </Reveal>
        <div className="features-grid">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 70} className="feature-card">
              <div className="feature-icon">
                <f.icon />
              </div>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="how-it-works">
        <Reveal>
          <h2>How a reminder moves through the system</h2>
        </Reveal>
        <Reveal className="flow-track" delay={80}>
          <div className="flow-line">
            <div className="flow-pulse" />
          </div>
          {STEPS.map((s, i) => (
            <div className="flow-node" key={s.label} style={{ animationDelay: `${i * 1}s` }}>
              <span className="flow-node-icon">
                <s.icon />
              </span>
              <span className="flow-node-label">{s.label}</span>
            </div>
          ))}
        </Reveal>
      </section>

      <section className="cta-band">
        <Reveal className="cta-inner">
          <h2>Stop losing revenue to no-shows.</h2>
          <p>Set up your first reminder in minutes.</p>
          <Link to={primaryCta.to} className="btn-primary">
            {primaryCta.label}
          </Link>
        </Reveal>
      </section>

      <Footer />
    </div>
  );
}

function IconShield() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

function IconSparkle() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3z" />
      <path d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8-1.8-.7 1.8-.7L19 15z" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20V10M12 20V4M20 20v-7" />
    </svg>
  );
}

function IconLayers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
    </svg>
  );
}

function IconBuilding() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 21V6l8-3 8 3v15" />
      <path d="M9 21v-6h6v6M9 10h.01M15 10h.01M9 14h.01M15 14h.01" />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8.5v7M8.5 12h7" />
    </svg>
  );
}

function IconSend() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 3L10.5 13.5" />
      <path d="M21 3l-6.5 18-4-8-8-4 18.5-6z" />
    </svg>
  );
}
