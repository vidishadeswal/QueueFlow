import { useEffect, useState, type FormEvent } from "react";
import { createAppointment, deleteAppointment, listAppointments, type Appointment } from "../api/appointments";
import { listContacts, type Contact } from "../api/contacts";
import DateTimeField from "../components/DateTimeField";

export default function Appointments() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [contactId, setContactId] = useState("");
  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    listAppointments().then(setAppointments).catch(() => setAppointments([]));
    listContacts().then(setContacts).catch(() => setContacts([]));
  }

  useEffect(refresh, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!scheduledAt) {
      setError("Pick a scheduled date and time.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createAppointment({
        contact_id: contactId,
        title,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
      setTitle("");
      setScheduledAt("");
      refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not create appointment.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteAppointment(id);
    refresh();
  }

  function contactName(id: string): string {
    return contacts.find((c) => c.id === id)?.name ?? "—";
  }

  return (
    <div>
      <h2>Appointments</h2>

      {contacts.length === 0 ? (
        <p className="placeholder-note">Add a contact first before creating appointments.</p>
      ) : (
        <form className="inline-form" onSubmit={handleSubmit}>
          <select value={contactId} onChange={(e) => setContactId(e.target.value)} required>
            <option value="" disabled>
              Select contact
            </option>
            {contacts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <DateTimeField value={scheduledAt} onChange={setScheduledAt} placeholder="Scheduled at" />
          <button type="submit" disabled={submitting}>
            {submitting ? "Adding..." : "Add appointment"}
          </button>
        </form>
      )}
      {error && <p className="error">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Contact</th>
            <th>Scheduled</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.id}>
              <td>{a.title}</td>
              <td>{contactName(a.contact_id)}</td>
              <td>{new Date(a.scheduled_at).toLocaleString()}</td>
              <td>
                <button className="link-button" onClick={() => handleDelete(a.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {appointments.length === 0 && (
            <tr>
              <td colSpan={4} className="empty-row">
                No appointments yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
