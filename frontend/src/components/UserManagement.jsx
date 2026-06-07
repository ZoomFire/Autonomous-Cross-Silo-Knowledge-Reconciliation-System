import { useEffect, useState } from "react";
import { deleteUser, getUsers, updateUserRole } from "../api.js";
import PermissionGuard from "./PermissionGuard.jsx";

const roles = ["admin", "engineer", "reviewer", "viewer"];

export default function UserManagement({ user }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadUsers() {
    try {
      setUsers(await getUsers());
    } catch (err) {
      setError(err.message || "Unable to load users.");
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function changeRole(userId, role) {
    setError("");
    setSuccess("");
    try {
      await updateUserRole(userId, role);
      setSuccess("Role updated.");
      loadUsers();
    } catch (err) {
      setError(err.message || "Role update failed.");
    }
  }

  async function removeUser(userId) {
    setError("");
    setSuccess("");
    try {
      await deleteUser(userId);
      setSuccess("User deleted.");
      loadUsers();
    } catch (err) {
      setError(err.message || "Delete failed.");
    }
  }

  return (
    <PermissionGuard user={user} permission="manage_users" fallback={<section className="page"><div className="error-banner">Only admin can manage users.</div></section>}>
      <section className="page">
        <div className="page-header"><div><h2>User Management</h2><p>Manage local DriftGuard users and roles.</p></div></div>
        {error && <div className="error-banner">{error}</div>}
        {success && <div className="success-banner">{success}</div>}
        <section className="panel">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.user_id}>
                    <td>{item.name}</td>
                    <td>{item.email}</td>
                    <td><span className={`role-badge ${item.role}`}>{item.role}</span></td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>
                      <div className="row-actions">
                        <select value={item.role} onChange={(event) => changeRole(item.user_id, event.target.value)}>{roles.map((role) => <option key={role}>{role}</option>)}</select>
                        <button className="secondary-button danger-button" onClick={() => removeUser(item.user_id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </PermissionGuard>
  );
}
