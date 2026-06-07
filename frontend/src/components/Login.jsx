import { useState } from "react";
import { login } from "../api.js";

export default function Login({ onLogin, onShowSignup }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await login(form);
      onLogin(response.user);
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div>
          <h1>DriftGuard AI</h1>
          <p>Sign in to your workspace.</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <label>Email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
        <label>Password<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></label>
        <button className="primary-button" type="submit" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
        <button className="link-button" type="button" onClick={onShowSignup}>Create first/admin account</button>
      </form>
    </main>
  );
}
