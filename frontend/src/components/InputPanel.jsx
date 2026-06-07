const fields = [
  ["documentation", "Confluence Documentation", "Paste endpoint requirements, access notes, or architecture guidance."],
  ["code", "GitHub Code Snippet", "Paste route decorators, handlers, middleware, or access-control code."],
  ["jira", "Jira Ticket", "Paste requirement, bug, status, or release ticket text."],
  ["commit", "Commit / PR Message", "Paste commit messages or pull request summaries."],
  ["logs", "System Logs", "Paste runtime logs, status codes, or access failure messages."],
  ["database_config", "Database Config", "Paste feature flags, access settings, or visibility configuration."],
];

export default function InputPanel({ form, onChange }) {
  return (
    <div className="input-grid">
      {fields.map(([key, label, placeholder]) => (
        <label className="input-card" key={key}>
          <span>{label}</span>
          <textarea
            value={form[key]}
            placeholder={placeholder}
            onChange={(event) => onChange({ ...form, [key]: event.target.value })}
          />
        </label>
      ))}
    </div>
  );
}
