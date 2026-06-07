import { LogOut } from "lucide-react";

export default function UserProfile({ user, workspace, onLogout }) {
  return (
    <div className="user-profile">
      <div>
        <strong>{user.name}</strong>
        <span>{user.email}</span>
      </div>
      <span className={`role-badge ${user.role}`}>{user.role}</span>
      <span className="workspace-chip">{workspace?.name || "No workspace"}</span>
      <button className="secondary-button icon-button" onClick={onLogout} title="Logout"><LogOut size={17} /></button>
    </div>
  );
}
