import './HowItWorks.css'

type Stage = {
  n: string
  title: string
  who: string
  body: string
}

const stages: Stage[] = [
  {
    n: '01',
    title: 'Prove who you are',
    who: 'contributor',
    body: 'Each contributor links their wallet to their GitHub account by publishing a one-time code in a public gist. The contract fetches it and confirms the match itself, so no one can claim another person\u2019s work.',
  },
  {
    n: '02',
    title: 'Lock the terms',
    who: 'project',
    body: 'The project fixes the repo, the approved contributors, the reward pool, and a measurable rubric, set before any work is judged and un-editable afterward.',
  },
  {
    n: '03',
    title: 'Fund the pool',
    who: 'project',
    body: 'Real GEN is deposited into the vault up front. Nothing is promised that isn\u2019t already funded.',
  },
  {
    n: '04',
    title: 'Settle the epoch',
    who: 'anyone',
    body: 'Anyone can trigger settlement. The contract fetches the merged pull requests itself, and independent validators score each contributor per rubric dimension and divide the pool by consensus.',
  },
  {
    n: '05',
    title: 'Read the verdict',
    who: 'the vault',
    body: 'The vault reads the split straight from the assessor. No manager, no relay, no one supplying amounts. It records each contributor\u2019s share as claimable.',
  },
  {
    n: '06',
    title: 'Accrue and claim',
    who: 'contributor',
    body: 'Each contributor pulls their own earned share in native GEN. Anything unallocated returns to reserve. Every figure is on-chain and auditable.',
  },
]

function HowItWorks() {
  return (
    <section className="hiw" id="how">
      <div className="hiw-inner">
        <p className="hiw-eyebrow">How it works</p>
        <h2 className="hiw-head">
          Six steps from a merged pull request<br />to earned compensation.
        </h2>
        <ol className="hiw-grid">
          {stages.map((s) => (
            <li className="hiw-stage" key={s.n}>
              <div className="hiw-stage-top">
                <span className="hiw-n">{s.n}</span>
                <span className="hiw-who">{s.who}</span>
              </div>
              <h3 className="hiw-stage-title">{s.title}</h3>
              <p className="hiw-stage-body">{s.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export default HowItWorks
