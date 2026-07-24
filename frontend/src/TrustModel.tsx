import './TrustModel.css'

const points = [
  {
    k: 'No payroll admin',
    v: 'No one sets or edits a contributor\u2019s share. The owner funds the pool and locks the terms up front, and has zero authority over the split.',
  },
  {
    k: 'Permissionless settlement',
    v: 'Anyone can settle an epoch and anyone can finalize it. The verdict comes from validator consensus over the evidence, never from the caller.',
  },
  {
    k: 'Read straight from consensus',
    v: 'The vault reads the allocation directly from the assessor at finalize. No relay, no owner call, no supplied amounts. Real GEN, real transfers.',
  },
]

const RECEIPT =
  'https://explorer-studio.genlayer.com/tx/0x07ce3a5b68347a908b324dccfd224ab042d0ba034017c4a82a0c801af97315bb'

function TrustModel() {
  return (
    <section className="tm">
      <div className="tm-inner">
        <p className="tm-eyebrow">The trust model</p>
        <h2 className="tm-head">Nobody has to be trusted, and it is provable.</h2>

        <div className="tm-grid">
          {points.map((p) => (
            <div className="tm-point" key={p.k}>
              <h3 className="tm-point-k">{p.k}</h3>
              <p className="tm-point-v">{p.v}</p>
            </div>
          ))}
        </div>

        <a className="tm-proof" href={RECEIPT} target="_blank" rel="noopener noreferrer">
          <div className="tm-proof-main">
            <span className="tm-proof-label">Proof · on-chain</span>
            <span className="tm-proof-title">A total stranger finalized a payout epoch.</span>
            <span className="tm-proof-sub">
              Wallet <span className="tm-mono">0xD7cd...7cc3</span>, which owns nothing here,
              ran a full settlement and finalization. This is that transaction.
            </span>
          </div>
          <span className="tm-proof-go">View the receipt <span className="tm-arrow">→</span></span>
        </a>
      </div>
    </section>
  )
}

export default TrustModel
