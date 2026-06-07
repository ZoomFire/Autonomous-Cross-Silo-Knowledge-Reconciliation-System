import { useState } from "react";
import { createWorkspace, setSelectedWorkspaceId } from "../api.js";
import PermissionGuard from "./PermissionGuard.jsx";

export default function WorkspaceSwitcher({ user, workspaces, currentWorkspaceId, onWorkspaceChange, onWorkspaceCreated }) {
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  async function createNewWorkspace() {
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const workspace = await createWorkspace({ name, description: "Created from DriftGuard AI" });
      setName("");
      setSelectedWorkspaceId(workspace.workspace_id);
      onWorkspaceCreated(workspace.workspace_id);
    } catch (err) {
      setError(err.message || "Workspace creation failed.");
    } finally {
      setCreating(false);
    }
  }

  function choose(workspaceId) {
    setSelectedWorkspaceId(workspaceId);
    onWorkspaceChange(workspaceId);
  }

  return (
    <div className="workspace-switcher">
      <label>
        Workspace
        <select value={currentWorkspaceId} onChange={(event) => choose(event.target.value)}>
          <option value="">Select workspace</option>
          {workspaces.map((workspace) => <option key={workspace.workspace_id} value={workspace.workspace_id}>{workspace.name}</option>)}
        </select>
      </label>
      <PermissionGuard user={user} permission="create_workspace">
        <div className="workspace-create">
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="New workspace" />
          <button className="secondary-button" onClick={createNewWorkspace} disabled={creating}>{creating ? "Creating..." : "Create"}</button>
        </div>
      </PermissionGuard>
      {error && <span className="inline-error">{error}</span>}
    </div>
  );
}
