import './MinorityHero.css'

function MinorityHero() {
  return (
    <section className="mn">
      <div className="mn-inner">
        <p className="mn-eyebrow">Contested attribution</p>
        <h2 className="mn-head">
          When validators disagree on credit,<br />the disagreement is the finding.
        </h2>
        <p className="mn-lede">
          Most systems hide dissent behind one confident number. Accrue does the opposite.
          Every settlement records the majority split and the strongest good-faith case
          against it, both on-chain, both permanent.
        </p>

        <div className="mn-card">
          <div className="mn-side mn-verdict">
            <span className="mn-side-label">Consensus · epoch-1</span>
            <ul className="mn-verdict-rows">
              <li>
                <span className="mn-vh">DaveDave-infosec</span>
                <span className="mn-va">0.500</span>
              </li>
              <li>
                <span className="mn-vh">Drizzy606</span>
                <span className="mn-va">0.116</span>
              </li>
            </ul>
            <span className="mn-side-foot">the split that moved the money</span>
          </div>

          <div className="mn-rule" aria-hidden="true" />

          <div className="mn-side mn-dissent">
            <span className="mn-side-label">Minority note · recorded on-chain</span>
            <blockquote className="mn-quote">
              One could argue Drizzy606 deserves more if the docs work meaningfully
              supported the other pull requests, but the evidence shows only a file title,
              with no detail on its content or impact.
            </blockquote>
            <span className="mn-side-foot">the case against, preserved</span>
          </div>
        </div>
      </div>
    </section>
  )
}

export default MinorityHero
