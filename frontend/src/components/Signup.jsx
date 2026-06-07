import { useState } from "react";
import { signup } from "../api.js";

export default function Signup({ onDone, onShowLogin }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "admin" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await signup(form);
      setSuccess("Signup successful. Please log in.");
      setTimeout(onDone, 500);
    } catch (err) {
      setError(err.message || "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div>
          <h1>Create Account</h1>
          <p>The first user becomes admin automatically.</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        {success && <div className="success-banner">{success}</div>}
        <label>Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
        <label>Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
        <label>Password<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></label>
        <p className="muted">Password must be at least 8 characters and include at least one letter and one number.</p>
        <label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}><option>admin</option><option>engineer</option><option>reviewer</option><option>viewer</option></select></label>
        <button className="primary-button" type="submit" disabled={loading}>{loading ? "Creating..." : "Signup"}</button>
        <button className="link-button" type="button" onClick={onShowLogin}>Back to login</button>
      </form>
    </main>
  );
}
