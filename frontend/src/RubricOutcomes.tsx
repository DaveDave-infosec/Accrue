import './RubricOutcomes.css'

const dimensions = [
  { name: 'Implementation', weight: '60%', body: 'Substance and volume of merged pull requests. The core of the work.' },
  { name: 'Review & docs', weight: '25%', body: 'Documentation, tests, and review that raw commit counts miss.' },
  { name: 'Consistency', weight: '15%', body: 'How steadily the merged work is spread across the epoch.' },
]

const outcomes = [
  { name: 'Allocate', tone: 'is-accrued', body: 'Shares are approved and accrue to contributors by their weighted score.' },
  { name: 'Return to reserve', tone: 'is-reserve', body: 'No qualifying work this epoch, so the unallocated pool returns to reserve.' },
  { name: 'Hold', tone: 'is-held', body: 'Evidence is missing or would overpay, so the amount is locked rather than guessed.' },
  { name: 'Reassign', tone: 'is-slate', body: 'Work by an unverified or wrong account earns nothing. Only verified contributors are credited.' },
  { name: 'Escalate', tone: 'is-clay', body: 'Validators cannot converge, so the epoch stays unsettled. No consensus, no money moves.' },
]

function RubricOutcomes() {
  return (
    <section className="ro">
      <div className="ro-inner">
        <div className="ro-col">
          <p className="ro-eyebrow">The rubric</p>
          <h2 className="ro-head">Judgment, constrained to something measurable.</h2>
          <p className="ro-lede">
            Subjective questions fracture consensus. A locked, weighted rubric is what lets
            independent validators land close enough to agree. They score each dimension
            against the evidence, then combine by the weights.
          </p>
          <ul className="ro-dims">
            {dimensions.map((d) => (
              <li className="ro-dim" key={d.name}>
                <span className="ro-dim-bar" />
                <span className="ro-dim-name">{d.name}</span>
                <span className="ro-dim-weight">{d.weight}</span>
                <span className="ro-dim-body">{d.body}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="ro-col">
          <p className="ro-eyebrow">The five outcomes</p>
          <h2 className="ro-head">Every epoch resolves one way, including the safe ones.</h2>
          <ul className="ro-outs">
            {outcomes.map((o) => (
              <li className={`ro-out ${o.tone}`} key={o.name}>
                <span className="ro-out-dot" />
                <span className="ro-out-name">{o.name}</span>
                <span className="ro-out-body">{o.body}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export default RubricOutcomes
