import { useState } from 'react'
import './CreateAgreement.css'
import { createAgreement } from './lib/accrue'

type Props = { account: string; onCreated: (aid: string) => void; onCancel: () => void }

function CreateAgreement({ account, onCreated, onCancel }: Props) {
  const [label, setLabel] = useState('')
  const [repoOwner, setRepoOwner] = useState('')
  const [repoName, setRepoName] = useState('')
  const [c1, setC1] = useState(account)
  const [c2, setC2] = useState('')
  const [c3, setC3] = useState('')
  const [wImpl, setWImpl] = useState('60')
  const [wDocs, setWDocs] = useState('25')
  const [wCons, setWCons] = useState('15')
  const [poolGen, setPoolGen] = useState('1')
  const [maxGen, setMaxGen] = useState('0.5')
  const [epochDays, setEpochDays] = useState('7')
  const [challengeHours, setChallengeHours] = useState('24')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')

  const weightTotal = (parseInt(wImpl || '0') + parseInt(wDocs || '0') + parseInt(wCons || '0'))

  async function submit() {
    if (!repoOwner.trim() || !repoName.trim()) { setStatus('Repository owner and name are required.'); return }
    if (!c1.trim() || !c2.trim() || !c3.trim()) { setStatus('Three contributor wallets are required.'); return }
    if (weightTotal !== 100) { setStatus('Rubric weights must add up to 100.'); return }
    const pool = Math.round(parseFloat(poolGen || '0') * 1000)
    const maxPer = Math.round(parseFloat(maxGen || '0') * 1000)
    if (pool <= 0) { setStatus('Pool must be greater than zero.'); return }

    setBusy(true); setStatus('Creating, approve in your wallet...')
    try {
      const res = await createAgreement(account, {
        label: label.trim() || (repoOwner.trim() + '/' + repoName.trim()),
        repoOwner: repoOwner.trim(),
        repoName: repoName.trim(),
        c1: c1.trim().toLowerCase(),
        c2: c2.trim().toLowerCase(),
        c3: c3.trim().toLowerCase(),
        rubricJson: JSON.stringify({
          implementation: parseInt(wImpl), review_docs: parseInt(wDocs), consistency: parseInt(wCons),
        }),
        eligibilityJson: JSON.stringify({ min_merged_prs: 1 }),
        epochLengthSeconds: Math.round(parseFloat(epochDays || '7') * 86400),
        poolPerEpoch: pool,
        maxPerContributor: maxPer,
        challengeWindowSeconds: Math.round(parseFloat(challengeHours || '24') * 3600),
        reserveRule: 'return_to_reserve',
      })
      const aid = String(res?.receipt?.returnValue ?? res?.returnValue ?? '')
      setStatus('Created.')
      onCreated(aid)
    } catch (e: any) {
      setStatus('Failed: ' + (e?.message || String(e)).slice(0, 180))
    } finally { setBusy(false) }
  }

  return (
    <div className="ca">
      <div className="ca-head">
        <div>
          <p className="ca-eyebrow">New agreement</p>
          <h2 className="ca-title">Set up your own repository.</h2>
          <p className="ca-lede">
            Terms lock on creation and cannot be edited afterward, not even by you.
            Consensus divides the pool, so creating an agreement gives you no power
            over who gets paid.
          </p>
        </div>
        <button className="ap-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>

      <div className="ca-grid">
        <label className="ca-field">
          <span className="ca-k">Label</span>
          <input className="ap-input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Optional name for this agreement" disabled={busy} />
        </label>

        <label className="ca-field">
          <span className="ca-k">Repository owner</span>
          <input className="ap-input" value={repoOwner} onChange={(e) => setRepoOwner(e.target.value)} placeholder="github-username" disabled={busy} />
        </label>

        <label className="ca-field">
          <span className="ca-k">Repository name</span>
          <input className="ap-input" value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="my-public-repo" disabled={busy} />
        </label>

        <label className="ca-field ca-wide">
          <span className="ca-k">Contributor wallets (exactly three)</span>
          <input className="ap-input ca-mb" value={c1} onChange={(e) => setC1(e.target.value)} placeholder="0x..." disabled={busy} />
          <input className="ap-input ca-mb" value={c2} onChange={(e) => setC2(e.target.value)} placeholder="0x..." disabled={busy} />
          <input className="ap-input" value={c3} onChange={(e) => setC3(e.target.value)} placeholder="0x..." disabled={busy} />
          <span className="ca-hint">
            Each contributor verifies their own GitHub account separately. Only
            verified work earns a share.
          </span>
        </label>

        <label className="ca-field ca-wide">
          <span className="ca-k">Rubric weights (must total 100)</span>
          <div className="ca-weights">
            <span className="ca-w"><input className="ap-input ap-input-sm" value={wImpl} onChange={(e) => setWImpl(e.target.value)} disabled={busy} /> implementation</span>
            <span className="ca-w"><input className="ap-input ap-input-sm" value={wDocs} onChange={(e) => setWDocs(e.target.value)} disabled={busy} /> review and docs</span>
            <span className="ca-w"><input className="ap-input ap-input-sm" value={wCons} onChange={(e) => setWCons(e.target.value)} disabled={busy} /> consistency</span>
          </div>
          <span className={`ca-hint ${weightTotal === 100 ? '' : 'is-bad'}`}>total {weightTotal}</span>
        </label>

        <label className="ca-field">
          <span className="ca-k">Pool per epoch (GEN)</span>
          <input className="ap-input" value={poolGen} onChange={(e) => setPoolGen(e.target.value)} disabled={busy} />
        </label>

        <label className="ca-field">
          <span className="ca-k">Max per contributor (GEN)</span>
          <input className="ap-input" value={maxGen} onChange={(e) => setMaxGen(e.target.value)} disabled={busy} />
        </label>

        <label className="ca-field">
          <span className="ca-k">Epoch length (days)</span>
          <input className="ap-input" value={epochDays} onChange={(e) => setEpochDays(e.target.value)} disabled={busy} />
        </label>

        <label className="ca-field">
          <span className="ca-k">Challenge window (hours)</span>
          <input className="ap-input" value={challengeHours} onChange={(e) => setChallengeHours(e.target.value)} disabled={busy} />
        </label>
      </div>

      <div className="ca-foot">
        <button className="ap-btn ap-btn-primary ca-submit" onClick={submit} disabled={busy}>
          {busy ? 'Creating...' : 'Create agreement'}
        </button>
        {status && <p className="ap-status">{status}</p>}
      </div>
    </div>
  )
}

export default CreateAgreement
