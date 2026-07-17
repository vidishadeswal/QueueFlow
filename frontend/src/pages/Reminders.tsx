import { useEffect, useRef, useState, type FormEvent } from "react";
import { draftReminderMessage, type ReminderTone } from "../api/ai";
import { listAppointments, type Appointment } from "../api/appointments";
import { fetchMe, updateWebhookUrl } from "../api/auth";
import { listContacts, type Contact } from "../api/contacts";
import {
  createReminder,
  deleteReminder,
  listReminders,
  retryReminder,
  type Reminder,
  type ReminderChannel,
} from "../api/reminders";
import DateTimeField from "../components/DateTimeField";

const TONES: ReminderTone[] = ["friendly", "formal", "promotional"];

export default function Reminders() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [appointmentId, setAppointmentId] = useState("");
  const [message, setMessage] = useState("");
  const [sendAt, setSendAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [tone, setTone] = useState<ReminderTone>("friendly");
  const [customPrompt, setCustomPrompt] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  const [channel, setChannel] = useState<ReminderChannel>("email");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookConfigured, setWebhookConfigured] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [webhookSaved, setWebhookSaved] = useState(false);

  // Held stable across a failed submission's retry so re-clicking "Add" after a
  // dropped request resolves to the same reminder instead of creating a duplicate;
  // cleared once a submission actually succeeds so the next reminder gets a fresh one.
  const submissionKeyRef = useRef<string | null>(null);

  function refresh() {
    listReminders().then(setReminders).catch(() => setReminders([]));
    listAppointments().then(setAppointments).catch(() => setAppointments([]));
    listContacts().then(setContacts).catch(() => setContacts([]));
    fetchMe().then((business) => {
      setWebhookUrl(business.webhook_url ?? "");
      setWebhookConfigured(!!business.webhook_url);
    });
  }

  useEffect(refresh, []);

  async function handleSaveWebhook(e: FormEvent) {
    e.preventDefault();
    setWebhookError(null);
    setWebhookSaved(false);
    setSavingWebhook(true);
    try {
      const business = await updateWebhookUrl(webhookUrl);
      setWebhookConfigured(!!business.webhook_url);
      setWebhookSaved(true);
    } catch (err: any) {
      setWebhookError(err?.response?.data?.detail ?? "Could not save webhook URL.");
    } finally {
      setSavingWebhook(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!sendAt) {
      setError("Pick a date and time to send.");
      return;
    }
    setError(null);
    setSubmitting(true);
    if (!submissionKeyRef.current) {
      submissionKeyRef.current = crypto.randomUUID();
    }
    try {
      await createReminder(
        {
          appointment_id: appointmentId,
          message,
          send_at: new Date(sendAt).toISOString(),
          channel,
        },
        submissionKeyRef.current,
      );
      submissionKeyRef.current = null;
      setMessage("");
      setSendAt("");
      setChannel("email");
      refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not create reminder.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDraft() {
    if (!appointmentId) {
      setDraftError("Select an appointment first.");
      return;
    }
    setDraftError(null);
    setDrafting(true);
    try {
      const drafted = await draftReminderMessage({
        appointment_id: appointmentId,
        tone: customPrompt ? undefined : tone,
        custom_prompt: customPrompt || undefined,
      });
      setMessage(drafted);
    } catch {
      setDraftError("Could not reach the AI drafting service.");
    } finally {
      setDrafting(false);
    }
  }

  async function handleRetry(id: string) {
    await retryReminder(id);
    refresh();
  }

  async function handleDelete(id: string) {
    await deleteReminder(id);
    refresh();
  }

  function appointmentLabel(id: string): string {
    const appt = appointments.find((a) => a.id === id);
    if (!appt) return "—";
    const contact = contacts.find((c) => c.id === appt.contact_id);
    return `${appt.title} (${contact?.name ?? "—"})`;
  }

  return (
    <div>
      <h2>Reminders</h2>

      {appointments.length === 0 ? (
        <p className="placeholder-note">Add an appointment first before creating reminders.</p>
      ) : (
        <>
          <div className="ai-draft-box">
            <span className="ai-draft-label">
              <SparkleIcon className="ai-draft-icon" />
              Draft with AI
            </span>
            <div className="ai-draft-controls">
              <select value={tone} onChange={(e) => setTone(e.target.value as ReminderTone)}>
                {TONES.map((t) => (
                  <option key={t} value={t}>
                    {t[0].toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
              <input
                placeholder="Or describe what you want it to say..."
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
              />
              <button type="button" onClick={handleDraft} disabled={drafting}>
                {drafting ? "Drafting..." : "Draft"}
              </button>
            </div>
            {draftError && <p className="error">{draftError}</p>}
          </div>

          <form className="ai-draft-box" onSubmit={handleSaveWebhook}>
            <span className="ai-draft-label">Webhook delivery</span>
            <div className="ai-draft-controls">
              <input
                placeholder="https://your-system.example.com/hooks/queueflow"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
              />
              <button type="submit" disabled={savingWebhook}>
                {savingWebhook ? "Saving..." : "Save"}
              </button>
            </div>
            {webhookError && <p className="error">{webhookError}</p>}
            {webhookSaved && !webhookError && <p className="placeholder-note">Saved.</p>}
          </form>

          <form className="inline-form" onSubmit={handleSubmit}>
            <select value={appointmentId} onChange={(e) => setAppointmentId(e.target.value)} required>
              <option value="" disabled>
                Select appointment
              </option>
              {appointments.map((a) => (
                <option key={a.id} value={a.id}>
                  {appointmentLabel(a.id)}
                </option>
              ))}
            </select>
            <input
              placeholder="Message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
            />
            <DateTimeField value={sendAt} onChange={setSendAt} placeholder="Send at" />
            <select value={channel} onChange={(e) => setChannel(e.target.value as ReminderChannel)}>
              <option value="email">Email</option>
              <option value="webhook" disabled={!webhookConfigured}>
                Webhook{webhookConfigured ? "" : " (configure a URL above first)"}
              </option>
            </select>
            <button type="submit" disabled={submitting}>
              {submitting ? "Adding..." : "Add reminder"}
            </button>
          </form>
        </>
      )}
      {error && <p className="error">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Message</th>
            <th>Appointment</th>
            <th>Send at</th>
            <th>Channel</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {reminders.map((r) => (
            <tr key={r.id}>
              <td>{r.message}</td>
              <td>{appointmentLabel(r.appointment_id)}</td>
              <td>{new Date(r.send_at).toLocaleString()}</td>
              <td>{r.channel}</td>
              <td>
                <span className={`status-badge ${r.status}`}>{r.status.replace("_", " ")}</span>
                {r.last_error && <div className="last-error">{r.last_error}</div>}
              </td>
              <td>
                {r.status === "dead_letter" && (
                  <button className="link-button" onClick={() => handleRetry(r.id)}>
                    Retry
                  </button>
                )}
                <button className="link-button" onClick={() => handleDelete(r.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {reminders.length === 0 && (
            <tr>
              <td colSpan={6} className="empty-row">
                No reminders yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function SparkleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3z" />
      <path d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8-1.8-.7 1.8-.7L19 15z" />
    </svg>
  );
}
