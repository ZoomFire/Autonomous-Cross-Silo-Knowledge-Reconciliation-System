export default function ClaimTable({ claims }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Extracted Claims</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Claim ID</th>
              <th>Source</th>
              <th>Entity</th>
              <th>Claim Type</th>
              <th>Claim Text</th>
              <th>Confidence</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>{claim.claim_id}</td>
                <td>{claim.source}</td>
                <td>{claim.entity}</td>
                <td>{claim.claim_type}</td>
                <td>{claim.claim_text}</td>
                <td>{Math.round(claim.confidence_score * 100)}%</td>
                <td>{claim.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
