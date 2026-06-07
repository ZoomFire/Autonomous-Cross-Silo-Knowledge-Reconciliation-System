export const ROLE_PERMISSIONS = {
  admin: [
    "manage_users",
    "create_workspace",
    "save_dataset",
    "delete_dataset",
    "run_evaluation",
    "create_monitoring_rule",
    "delete_monitoring_rule",
    "manage_alerts",
    "add_feedback",
    "export_reports",
    "view_dashboard",
    "delete_history",
    "manage_connectors",
    "sync_connectors",
    "generate_connector_datasets",
    "delete_connectors",
    "view_connectors",
  ],
  engineer: ["save_dataset", "run_evaluation", "create_monitoring_rule", "manage_alerts", "export_reports", "view_dashboard", "manage_connectors", "sync_connectors", "generate_connector_datasets", "view_connectors"],
  reviewer: ["add_feedback", "export_reports", "view_dashboard", "view_connectors"],
  viewer: ["view_dashboard", "view_connectors"],
};

export function hasPermission(user, permission) {
  return ROLE_PERMISSIONS[user?.role]?.includes(permission) || false;
}

export default function PermissionGuard({ user, permission, children, fallback = null }) {
  if (!hasPermission(user, permission)) return fallback;
  return children;
}
