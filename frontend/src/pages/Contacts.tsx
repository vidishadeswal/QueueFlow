import { useEffect, useState, type FormEvent } from "react";
import { createContact, deleteContact, listContacts, type Contact } from "../api/contacts";

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    listContacts().then(setContacts).catch(() => setContacts([]));
  }

  useEffect(refresh, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createContact({ name, email, phone: phone || undefined });
      setName("");
      setEmail("");
      setPhone("");
      refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not create contact.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteContact(id);
    refresh();
  }

  return (
    <div>
      <h2>Contacts</h2>

      <form className="inline-form" onSubmit={handleSubmit}>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input placeholder="Phone (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding..." : "Add contact"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.email}</td>
              <td>{c.phone ?? "—"}</td>
              <td>
                <button className="link-button" onClick={() => handleDelete(c.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {contacts.length === 0 && (
            <tr>
              <td colSpan={4} className="empty-row">
                No contacts yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
