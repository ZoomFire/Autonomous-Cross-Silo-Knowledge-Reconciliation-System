const columns = [
  ["requirement_view", "Requirement View"],
  ["implementation_view", "Implementation View"],
  ["runtime_view", "Runtime View"],
];

export default function TruthTriangle({ triangle }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Truth Triangle</h3>
      </div>
      <div className="triangle-grid">
        {columns.map(([key, title]) => (
          <div className="triangle-column" key={key}>
            <h4>{title}</h4>
            {triangle[key].length === 0 ? (
              <p className="empty-state">No claims extracted.</p>
            ) : (
              triangle[key].map((claim) => (
                <article className="claim-card" key={claim.claim_id}>
                  <span>{claim.source}</span>
                  <strong>{claim.claim_text}</strong>
                  <p>{claim.evidence}</p>
                </article>
              ))
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
