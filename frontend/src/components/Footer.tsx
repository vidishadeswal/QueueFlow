import { Link } from "react-router-dom";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Logo className="footer-logo" />
          <p>Reliable job scheduling for businesses that can't afford a missed appointment.</p>
        </div>

        <div className="footer-col">
          <h4>Product</h4>
          <Link to="/#features">Features</Link>
          <Link to="/#how-it-works">How it works</Link>
          <Link to="/signup">Get started</Link>
        </div>

        <div className="footer-col">
          <h4>Use cases</h4>
          <span>Dental &amp; medical clinics</span>
          <span>Gyms &amp; studios</span>
          <span>Salons &amp; spas</span>
          <span>Consultants &amp; tutors</span>
        </div>

        <div className="footer-col">
          <h4>Stack</h4>
          <span>FastAPI + PostgreSQL</span>
          <span>Redis queue + workers</span>
          <span>React + Docker</span>
        </div>
      </div>

      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} QueueFlow. Built as a systems-design portfolio project.</span>
      </div>
    </footer>
  );
}
