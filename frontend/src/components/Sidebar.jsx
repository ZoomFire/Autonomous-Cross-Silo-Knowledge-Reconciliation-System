import { Activity, BarChart3, Bot, Brain, BriefcaseBusiness, ClipboardList, Cpu, DatabaseZap, FileSearch, FlaskConical, Gauge, History, LockKeyhole, Plug, Search, ServerCog, ShieldAlert, ShieldCheck, Users, Workflow } from "lucide-react";
import PermissionGuard from "./PermissionGuard.jsx";

export default function Sidebar({ activePage, onNavigate, user }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon"><ShieldCheck size={24} /></div>
        <div>
          <h1>DriftGuard AI</h1>
          <span>Knowledge Reconciliation</span>
        </div>
      </div>

      <nav className="nav-list">
        <button className={activePage === "manual" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("manual")}>
          <ClipboardList size={18} />
          <span>Manual Analysis</span>
        </button>
        <button className={activePage === "dataset" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("dataset")}>
          <BarChart3 size={18} />
          <span>Dataset Evaluation</span>
        </button>
        <button className={activePage === "training-data" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("training-data")}>
          <DatabaseZap size={18} />
          <span>Training Data</span>
        </button>
        <button className={activePage === "models" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("models")}>
          <Cpu size={18} />
          <span>Models</span>
        </button>
        <button className={activePage === "executive" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("executive")}>
          <BriefcaseBusiness size={18} />
          <span>Executive</span>
        </button>
        {["admin", "engineer", "reviewer"].includes(user?.role) && (
          <button className={activePage === "validation" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("validation")}>
            <FlaskConical size={18} />
            <span>Validation</span>
          </button>
        )}
        <button className={activePage === "connectors" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("connectors")}>
          <Plug size={18} />
          <span>Connectors</span>
        </button>
        <button className={activePage === "search" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("search")}>
          <Search size={18} />
          <span>Search</span>
        </button>
        <button className={activePage === "agent" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("agent")}>
          <Bot size={18} />
          <span>Agent</span>
        </button>
        {user?.role !== "viewer" && (
          <button className={activePage === "ai-settings" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("ai-settings")}>
            <Brain size={18} />
            <span>AI Settings</span>
          </button>
        )}
        <button className={activePage === "monitoring" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("monitoring")}>
          <Activity size={18} />
          <span>Monitoring</span>
        </button>
        <button className={activePage === "incidents" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("incidents")}>
          <ShieldAlert size={18} />
          <span>Incidents</span>
        </button>
        {["admin", "engineer"].includes(user?.role) && (
          <button className={activePage === "integrations" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("integrations")}>
            <Workflow size={18} />
            <span>Integrations</span>
          </button>
        )}
        <button className={activePage === "history" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("history")}>
          <History size={18} />
          <span>Drift History</span>
        </button>
        <PermissionGuard user={user} permission="manage_users">
          <button className={activePage === "audit" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("audit")}>
            <FileSearch size={18} />
            <span>Audit</span>
          </button>
          <button className={activePage === "observability" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("observability")}>
            <Gauge size={18} />
            <span>Observability</span>
          </button>
          <button className={activePage === "security" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("security")}>
            <LockKeyhole size={18} />
            <span>Security</span>
          </button>
          <button className={activePage === "users" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("users")}>
            <Users size={18} />
            <span>User Management</span>
          </button>
          <button className={activePage === "system" ? "nav-item active" : "nav-item"} onClick={() => onNavigate("system")}>
            <ServerCog size={18} />
            <span>System Admin</span>
          </button>
        </PermissionGuard>
      </nav>

      <div className="sidebar-footer">Level 4.7</div>
    </aside>
  );
}
