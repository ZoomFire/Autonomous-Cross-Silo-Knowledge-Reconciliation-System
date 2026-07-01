export default function UserProfile({ user, workspace }) {
  return (
    <div className="user-profile">
      <div>
        <strong>{user.name}</strong>
        <span>{user.email}</span>
      </div>
      <span className={`role-badge ${user.role}`}>{user.role}</span>
      <span className="workspace-chip">{workspace?.name || "No workspace"}</span>
    </div>
  );
}
