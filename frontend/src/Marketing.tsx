import './Marketing.css'
import { Link } from 'react-router-dom'
import HowItWorks from './HowItWorks'
import RubricOutcomes from './RubricOutcomes'
import MinorityHero from './MinorityHero'
import TrustModel from './TrustModel'
import ClosingFaq from './ClosingFaq'

type Row = {
  handle: string
  amount: number
  pct: number
  toneClass: string
  note: string
}

const rows: Row[] = [
  { handle: 'DaveDave-infosec', amount: 0.5, pct: 50.0, toneClass: 'is-sage', note: '2 merged implementation PRs' },
  { handle: 'Drizzy606', amount: 0.116, pct: 11.6, toneClass: 'is-walnut', note: '1 docs PR' },
  { handle: 'idle contributor', amount: 0.0, pct: 0.0, toneClass: 'is-idle', note: 'no merged work' },
  { handle: 'reserve', amount: 0.384, pct: 38.4, toneClass: 'is-reserve', note: 'unallocated, returned to pool' },
]

const rowStyle = (pct: number, i: number) =>
  ({ '--pct': pct + '%', '--i': i } as React.CSSProperties)

function Marketing() {
  return (
    <div className="mk">
      <header className="mk-nav">
        <span className="mk-word">Accrue</span>
        <nav className="mk-nav-links">
          <a href="#how" className="mk-nav-link">How it works</a>
          <Link to="/app" className="mk-launch">Launch the app →</Link>
        </nav>
      </header>

      <section className="mk-hero">
        <div className="mk-hero-copy">
          <p className="mk-eyebrow">Consensus-settled contributor compensation</p>
          <h1 className="mk-title">
            Contribution<br />becomes<br /><em>compensation.</em>
          </h1>
          <p className="mk-lede">
            A funded pool, divided by consensus over who actually did the work.
            No manager sets the split. Independent validators read the evidence,
            score it against a locked rubric, and the pool accrues to the people
            who earned it.
          </p>
          <Link to="/app" className="mk-cta">Launch the app →</Link>
        </div>

        <figure
          className="mk-ledger"
          aria-label="The Attribution Ledger: a 1 GEN pool divided into 0.5 to DaveDave-infosec, 0.116 to Drizzy606, 0 to an idle contributor, and 0.384 to reserve."
        >
          <div className="mk-ledger-head">
            <span className="mk-ledger-title">The Attribution Ledger</span>
            <span className="mk-ledger-pool">pool <b>1.000</b> GEN</span>
          </div>
          <ul className="mk-rows">
            {rows.map((r, i) => (
              <li className={`mk-row ${r.toneClass}`} key={r.handle} style={rowStyle(r.pct, i)}>
                <span className="mk-row-handle">{r.handle}</span>
                <span className="mk-row-track">
                  <span className="mk-row-fill" />
                </span>
                <span className="mk-row-amt">{r.amount.toFixed(3)}</span>
                <span className="mk-row-note">{r.note}</span>
              </li>
            ))}
          </ul>
          <figcaption className="mk-ledger-foot">
            <span className="mk-live"><span className="mk-live-dot" /> live · epoch-1 · on-chain</span>
          </figcaption>
        </figure>
      </section>
      <HowItWorks />
      <RubricOutcomes />
      <MinorityHero />
      <TrustModel />
      <ClosingFaq />
    </div>
  )
}

export default Marketing
