import { useEffect, useState } from "react";
import { fetchAnalyticsSummary, type AnalyticsSummary } from "../api/analytics";
import { fetchHealth, type HealthStatus } from "../api/health";
import { listAppointments, type Appointment } from "../api/appointments";
import { listContacts, type Contact } from "../api/contacts";
import { listReminders, type Reminder, type ReminderStatus } from "../api/reminders";
import { useAuth } from "../context/AuthContext";

const REFRESH_INTERVAL_MS = 10_000;

const STATUS_COLORS: Record<ReminderStatus, string> = {
  sent: "#219a5c",
  dead_letter: "#e5484d",
  pending: "#b78103",
  queued: "#b78103",
};

const STATUS_ORDER: ReminderStatus[] = ["sent", "pending", "queued", "dead_letter"];

export default function Dashboard() {
  const { business } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [stats, setStats] = useState<AnalyticsSummary | null>(null);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);

  useEffect(() => {
    function refresh() {
      fetchHealth().then(setHealth).catch(() => setHealth(null));
      fetchAnalyticsSummary().then(setStats).catch(() => setStats(null));
      listReminders().then(setReminders).catch(() => setReminders([]));
      listAppointments().then(setAppointments).catch(() => setAppointments([]));
      listContacts().then(setContacts).catch(() => setContacts([]));
    }
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  function contactName(id: string): string {
    return contacts.find((c) => c.id === id)?.name ?? "—";
  }

  function appointmentTitle(id: string): string {
    return appointments.find((a) => a.id === id)?.title ?? "—";
  }

  const statusCounts = STATUS_ORDER.reduce(
    (acc, status) => {
      acc[status] = reminders.filter((r) => r.status === status).length;
      return acc;
    },
    {} as Record<ReminderStatus, number>,
  );

  const recentReminders = [...reminders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8);

  const now = Date.now();
  const upcomingAppointments = [...appointments]
    .filter((a) => new Date(a.scheduled_at).getTime() > now)
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
    .slice(0, 5);

  return (
    <div className="dashboard-wide">
      <div className="dashboard-welcome">
        <h2>Welcome back{business ? `, ${business.name}` : ""}</h2>
        <p>Here's what's happening with your reminders right now.</p>
      </div>

      <section className="status-grid">
        <StatusCard label="Database" status={health?.database} />
        <StatusCard label="Redis" status={health?.redis} />
        <StatusCard label="Worker" status={stats ? (stats.worker_healthy ? "up" : "down") : undefined} />
      </section>

      <section className="metrics-grid">
        <MetricCard label="Today's reminders" value={fmtInt(stats?.today_reminders)} />
        <MetricCard label="Upcoming reminders" value={fmtInt(stats?.upcoming_reminders)} />
        <MetricCard label="Delivery %" value={fmtPercent(stats?.delivery_rate)} />
        <MetricCard label="Avg retry count" value={fmtDecimal(stats?.avg_retry_count)} />
        <MetricCard label="Queue size" value={fmtInt(stats?.queue_size)} />
      </section>

      {stats && stats.dead_letter_reminders > 0 && (
        <p className="dlq-note">
          <WarningIcon className="dlq-icon" />
          {stats.dead_letter_reminders} reminder{stats.dead_letter_reminders === 1 ? "" : "s"} in the dead letter
          queue — needs manual attention.
        </p>
      )}

      <section className="dashboard-grid">
        <div className="panel">
          <h3>Reminder status breakdown</h3>
          {reminders.length === 0 ? (
            <p className="placeholder-note">No reminders yet.</p>
          ) : (
            <div className="donut-row">
              <DonutChart counts={statusCounts} total={reminders.length} />
              <ul className="donut-legend">
                {STATUS_ORDER.filter((s) => statusCounts[s] > 0).map((status) => (
                  <li key={status}>
                    <span className="legend-dot" style={{ background: STATUS_COLORS[status] }} />
                    <span className="legend-label">{status.replace("_", " ")}</span>
                    <span className="legend-count">{statusCounts[status]}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="panel">
          <h3>Upcoming appointments</h3>
          {upcomingAppointments.length === 0 ? (
            <p className="placeholder-note">Nothing scheduled.</p>
          ) : (
            <ul className="mini-list">
              {upcomingAppointments.map((a) => (
                <li key={a.id}>
                  <div>
                    <strong>{a.title}</strong>
                    <span>{contactName(a.contact_id)}</span>
                  </div>
                  <span className="mini-list-date">{new Date(a.scheduled_at).toLocaleDateString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="panel panel-wide">
          <h3>Recent reminders</h3>
          {recentReminders.length === 0 ? (
            <p className="placeholder-note">No reminders yet.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Message</th>
                  <th>Appointment</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentReminders.map((r) => (
                  <tr key={r.id}>
                    <td className="truncate-cell">{r.message}</td>
                    <td>{appointmentTitle(r.appointment_id)}</td>
                    <td>
                      <span className={`status-badge ${r.status}`}>{r.status.replace("_", " ")}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

function DonutChart({ counts, total }: { counts: Record<ReminderStatus, number>; total: number }) {
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  let offsetSoFar = 0;

  return (
    <svg viewBox="0 0 120 120" className="donut-chart">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--border)" strokeWidth="14" />
      {STATUS_ORDER.filter((s) => counts[s] > 0).map((status) => {
        const fraction = counts[status] / total;
        const dash = fraction * circumference;
        const circle = (
          <circle
            key={status}
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={STATUS_COLORS[status]}
            strokeWidth="14"
            strokeDasharray={`${dash} ${circumference - dash}`}
            strokeDashoffset={-offsetSoFar}
            transform="rotate(-90 60 60)"
            strokeLinecap="butt"
          />
        );
        offsetSoFar += dash;
        return circle;
      })}
      <text x="60" y="64" textAnchor="middle" className="donut-total">
        {total}
      </text>
    </svg>
  );
}

function fmtInt(value: number | undefined): string {
  return value === undefined ? "—" : String(value);
}

function fmtDecimal(value: number | undefined): string {
  return value === undefined ? "—" : value.toFixed(2);
}

function fmtPercent(value: number | null | undefined): string {
  if (value === undefined) return "—";
  if (value === null) return "n/a";
  return `${value}%`;
}

function StatusCard({ label, status }: { label: string; status?: "up" | "down" }) {
  return (
    <div className={`status-card ${status ?? "unknown"}`}>
      <span className="dot" />
      <span>{label}</span>
      <strong>{status ?? "checking..."}</strong>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3.5l9.5 16.5H2.5L12 3.5z" />
      <path d="M12 10v4M12 17.5h.01" />
    </svg>
  );
}
