import './ClosingFaq.css'
import { Link } from 'react-router-dom'

const faqs = [
  {
    q: 'Is this employment payroll?',
    a: 'No. Accrue is opt-in compensation for open-source contributors, not a replacement for legal wages, HR, or an employment agreement. It divides a funded pool by observed contribution.',
  },
  {
    q: 'What counts as evidence?',
    a: 'Merged pull requests in one public repository, fetched by the contract itself each epoch. Private or offline work is out of scope and is not judged.',
  },
  {
    q: 'Who can settle an epoch?',
    a: 'Anyone, after the epoch. Settlement is a permissionless call. There is no scheduler and no privileged trigger, and the caller never supplies the verdict.',
  },
  {
    q: 'What happens when validators disagree?',
    a: 'If they cannot converge, the epoch stays unsettled rather than paying out a guess. No consensus, no money moves. Where they do converge, the dissent is still recorded as a minority note.',
  },
  {
    q: 'Is the money real?',
    a: 'Yes. The vault holds and pays native GEN. Funding in and claims out are real transfers, not a mock ledger. Every allocation and claim is on-chain and auditable.',
  },
]

function ClosingFaq() {
  return (
    <>
      <section className="fq">
        <div className="fq-inner">
          <p className="fq-eyebrow">Honest limitations</p>
          <h2 className="fq-head">What Accrue is, and what it is not.</h2>
          <dl className="fq-list">
            {faqs.map((f) => (
              <div className="fq-item" key={f.q}>
                <dt className="fq-q">{f.q}</dt>
                <dd className="fq-a">{f.a}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="cta">
        <div className="cta-inner">
          <h2 className="cta-head">
            Let the work<br /><em>speak for itself.</em>
          </h2>
          <p className="cta-sub">
            A funded pool, divided by consensus over who earned it. See the live epoch,
            or settle and claim your own.
          </p>
          <Link to="/app" className="cta-btn">Launch the app →</Link>
          <p className="cta-foot">
            Accrue · consensus-settled contributor compensation · built on GenLayer
          </p>
        </div>
      </section>
    </>
  )
}

export default ClosingFaq
