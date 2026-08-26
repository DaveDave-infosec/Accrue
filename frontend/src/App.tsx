import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import './App.css'
import {
  connectWallet, getCurrentAccount, onAccountChange, requestAccountSwitch,
} from './lib/genlayer'
import {
  getAgreementCount, getAgreement, getContributors, getEpochs, getEpoch,
  getEpochAllocation, getSettlementProgress, getHandle, isVerified, getClaimable, getClaimed,
  getAgreementPool,
  openSettlement, collectBatch, finalizeSettlement, finalizeEpoch, claim as claimShare, fundPool,
} from './lib/accrue'
import { ASSESSOR_CONTRACT_ADDRESS, VAULT_CONTRACT_ADDRESS } from './lib/constants'
import IdentityPanel from './IdentityPanel'
import CreateAgreement from './CreateAgreement'




const EXPLORER = 'https://explorer-studio.genlayer.com/address/'
const tones = ['is-sage', 'is-walnut', 'is-slate']




function shortAddr(a: string) { return a.slice(0, 6) + '...' + a.slice(-4) }
function fmtGen(n: number) { return n.toFixed(3) }
function genFromWei(w: bigint) { return Number(w) / 1e18 }




type AgSummary = { id: string; label: string; repo: string }
type Contributor = {
  wallet: string; handle: string; verified: boolean
  allocUnits: number; claimableWei: bigint; claimedWei: bigint
}




function App() {
  const [account, setAccount] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [creating, setCreating] = useState(false)




  const [agreements, setAgreements] = useState<AgSummary[]>([])
  const [agsLoaded, setAgsLoaded] = useState(false)
  const [aid, setAid] = useState('')




  const [repo, setRepo] = useState('')
  const [poolUnits, setPoolUnits] = useState(0)
  const [epochLen, setEpochLen] = useState('')
  const [rubric, setRubric] = useState<[string, number][]>([])
  const [agPoolWei, setAgPoolWei] = useState<bigint>(0n)




  const [epochs, setEpochs] = useState<string[]>([])
  const [selectedEpoch, setSelectedEpoch] = useState('')
  const [outcome, setOutcome] = useState('')
  const [reserveUnits, setReserveUnits] = useState(0)
  const [minority, setMinority] = useState('')
  const [prCount, setPrCount] = useState('')
  const [contribs, setContribs] = useState<Contributor[]>([])




  const [settleId, setSettleId] = useState('0')
  const [progress, setProgress] = useState<any>(null)
  const [finalId, setFinalId] = useState('0')
  const [fundAmt, setFundAmt] = useState('1')
  const [epochInput, setEpochInput] = useState('')
  const [action, setAction] = useState('')




  const loadAgreements = useCallback(async (): Promise<AgSummary[]> => {
    try {
      const count = Number(await getAgreementCount())
      const ids = Array.from({ length: count }, (_, i) => String(i + 1))
      const rows = await Promise.all(ids.map(async (id) => {
        try {
          const ag = await getAgreement(id)
          if (!ag || !ag.exists) return null
          return {
            id,
            label: String(ag.label || '') || (ag.repo_owner + '/' + ag.repo_name),
            repo: ag.repo_owner + '/' + ag.repo_name,
          } as AgSummary
        } catch { return null }
      }))
      return rows.filter((x): x is AgSummary => x !== null)
    } catch { return [] }
  }, [])




  const loadLedger = useCallback(async (agId: string, epochId: string) => {
    setLoading(true); setErr('')
    try {
      const [ag, cs, agPool] = await Promise.all([
        getAgreement(agId), getContributors(agId), getAgreementPool(agId),
      ])
      setRepo(ag.repo_owner + '/' + ag.repo_name)
      setPoolUnits(Number(ag.pool_per_epoch))
      setEpochLen(ag.epoch_length_seconds)
      setAgPoolWei(agPool as bigint)
      try {
        const rj = JSON.parse(ag.rubric_json)
        setRubric(Object.entries(rj).map(([k, v]) => [k, Number(v)]) as [string, number][])
      } catch { setRubric([]) }




      if (!epochId) {
        setOutcome(''); setReserveUnits(0); setMinority(''); setPrCount(''); setProgress(null)
        const blank = await Promise.all((cs as string[]).filter(Boolean).map(async (w) => {
          const [handle, verified, claimable, claimed] = await Promise.all([
            getHandle(w), isVerified(w), getClaimable(agId, w), getClaimed(agId, w),
          ])
          return {
            wallet: w, handle: (handle as string) || '', verified: verified as boolean,
            allocUnits: 0, claimableWei: claimable as bigint, claimedWei: claimed as bigint,
          }
        }))
        setContribs(blank)
        return
      }




      const ep = await getEpoch(agId, epochId)
      setOutcome(ep.outcome)
      setReserveUnits(Number(ep.reserve))
      setMinority(ep.minority_note)
      setPrCount(ep.pr_count)
      try { setProgress(await getSettlementProgress(agId, epochId)) } catch { setProgress(null) }




      const rows: Contributor[] = await Promise.all(
        (cs as string[]).filter(Boolean).map(async (w) => {
          const [alloc, handle, verified, claimable, claimed] = await Promise.all([
            getEpochAllocation(agId, epochId, w), getHandle(w), isVerified(w),
            getClaimable(agId, w), getClaimed(agId, w),
          ])
          return {
            wallet: w, handle: (handle as string) || '', verified: verified as boolean,
            allocUnits: Number(alloc), claimableWei: claimable as bigint, claimedWei: claimed as bigint,
          }
        })
      )
      setContribs(rows)
    } catch (e: any) {
      setErr(e?.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [])




  const refreshAll = useCallback(async (wantAid?: string, wantEpoch?: string) => {
    const list = await loadAgreements()
    setAgreements(list)
    setAgsLoaded(true)
    if (list.length === 0) { setAid(''); setContribs([]); setEpochs([]); return }
    const pickAid = (wantAid && list.some((a) => a.id === wantAid)) ? wantAid
      : (aid && list.some((a) => a.id === aid)) ? aid : list[list.length - 1].id
    setAid(pickAid)
    let eps: string[] = []
    try { eps = (await getEpochs(pickAid)) as string[] } catch { eps = [] }
    setEpochs(eps)
    const pickEpoch = (wantEpoch && eps.includes(wantEpoch)) ? wantEpoch
      : (selectedEpoch && eps.includes(selectedEpoch)) ? selectedEpoch
      : (eps.length ? eps[eps.length - 1] : '')
    setSelectedEpoch(pickEpoch)
    await loadLedger(pickAid, pickEpoch)
  }, [loadAgreements, loadLedger, aid, selectedEpoch])




  useEffect(() => {
    getCurrentAccount().then((a) => { if (a) { setAccount(a); refreshAll() } })
    const unsub = onAccountChange((a) => { setAccount(a); if (a) refreshAll() })
    return unsub
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])




  async function connect() {
    try { setErr(''); const a = await connectWallet(); setAccount(a); await refreshAll() }
    catch (e: any) { setErr(e?.message || String(e)) }
  }
  async function switchAccount() {
    try {
      setErr(''); setAction('')
      const a = await requestAccountSwitch()
      if (a) { setAccount(a); await refreshAll() }
    } catch (e: any) { setErr(e?.message || String(e)) }
  }
  function disconnect() {
    setAccount(null); setContribs([]); setEpochs([]); setAgreements([])
    setAgsLoaded(false); setAid(''); setAction(''); setErr('')
  }




  async function selectAgreement(id: string) {
    setErr(''); setAction('')
    setAid(id); setSelectedEpoch('')
    let eps: string[] = []
    try { eps = (await getEpochs(id)) as string[] } catch { eps = [] }
    setEpochs(eps)
    const pick = eps.length ? eps[eps.length - 1] : ''
    setSelectedEpoch(pick)
    await loadLedger(id, pick)
  }
  function selectEpoch(id: string) { setErr(''); setAction(''); setSelectedEpoch(id); loadLedger(aid, id) }
  function loadTypedEpoch() {
    const id = epochInput.trim()
    if (id) { setSelectedEpoch(id); loadLedger(aid, id) }
  }




  async function run(label: string, fn: () => Promise<any>, wantEpoch?: string) {
    if (!account) { setErr('Connect a wallet first.'); return }
    setBusy(true)
    setAction(label + ' · sending, approve in your wallet...')
    try {
      await fn()
      setAction(label + ' · confirmed')
      await refreshAll(aid, wantEpoch)
      for (const wait of [3000, 6000, 10000]) {
        setTimeout(async () => {
          try { if (aid) setAgPoolWei(await getAgreementPool(aid) as bigint) } catch { /* ignore */ }
        }, wait)
      }
    } catch (e: any) {
      setAction(label + ' · failed: ' + (e?.message || String(e)).slice(0, 150))
    } finally {
      setBusy(false)
    }
  }




  const connectedRow = contribs.find((c) => c.wallet.toLowerCase() === (account || '').toLowerCase())
  const myClaimable = connectedRow ? genFromWei(connectedRow.claimableWei) : 0
  const disabled = busy || loading




  return (
    <div className="ap">
      <header className="ap-head">
        <Link to="/" className="ap-word">Accrue</Link>
        <div className="ap-wallet">
          {account ? (
            <>
              <span className="ap-acct"><span className="ap-dot" />{shortAddr(account)}</span>
              <button className="ap-ghost" onClick={switchAccount} disabled={busy}>Switch</button>
              <button className="ap-ghost" onClick={disconnect} disabled={busy}>Disconnect</button>
            </>
          ) : (
            <button className="ap-connect" onClick={connect}>Connect wallet</button>
          )}
        </div>
      </header>




      {err && <div className="ap-err">{err}</div>}




      {!account && (
        <div className="ap-empty">
          <h1 className="ap-empty-h">Read the live ledger.</h1>
          <p className="ap-empty-p">
            Connect a wallet to browse agreements, set one up for your own repository,
            and settle, finalize, or claim. Every action here is permissionless.
          </p>
          <button className="ap-connect ap-connect-lg" onClick={connect}>Connect wallet</button>
        </div>
      )}




      {account && creating && (
        <main className="ap-main">
          <CreateAgreement
            account={account}
            onCancel={() => setCreating(false)}
            onCreated={async (newAid) => { setCreating(false); await refreshAll(newAid || undefined) }}
          />
        </main>
      )}




      {account && !creating && !agsLoaded && agreements.length === 0 && (
        <main className="ap-main">
          <div className="ap-empty">
            <p className="ap-empty-p">Reading agreements from the chain...</p>
          </div>
        </main>
      )}




      {account && !creating && agsLoaded && agreements.length === 0 && (
        <main className="ap-main">
          <div className="ap-empty">
            <h1 className="ap-empty-h">No agreements yet.</h1>
            <p className="ap-empty-p">
              Set one up for any public GitHub repository. Terms lock on creation,
              and consensus divides the pool, so creating one gives you no power over
              who gets paid.
            </p>
            <button className="ap-connect ap-connect-lg" onClick={() => setCreating(true)}>
              Create the first agreement
            </button>
          </div>
        </main>
      )}




      {account && !creating && agsLoaded && agreements.length > 0 && (
        <main className="ap-main">
          <section className="ap-agpick">
            <span className="ap-k">Agreement</span>
            <select
              className="ap-select"
              value={aid}
              onChange={(e) => selectAgreement(e.target.value)}
              disabled={disabled}
            >
              {agreements.map((a) => (
                <option key={a.id} value={a.id}>{a.label} — {a.repo}</option>
              ))}
            </select>
            <button className="ap-btn ap-btn-sm" onClick={() => setCreating(true)} disabled={busy}>New agreement</button>
          </section>




          <section className="ap-agree">
            <div className="ap-agree-item"><span className="ap-k">Repository</span><span className="ap-v">{repo || '—'}</span></div>
            <div className="ap-agree-item"><span className="ap-k">Pool / epoch</span><span className="ap-v">{fmtGen(poolUnits / 1000)} GEN</span></div>
            <div className="ap-agree-item"><span className="ap-k">Epoch length</span><span className="ap-v">{epochLen ? Math.round(Number(epochLen) / 86400) + ' days' : '—'}</span></div>
            <div className="ap-agree-item ap-agree-rubric">
              <span className="ap-k">Rubric</span>
              <span className="ap-rubric">
                {rubric.map(([k, v]) => <span key={k} className="ap-rchip">{k} <b>{v}%</b></span>)}
              </span>
            </div>
          </section>




          <div className="ap-epochs">
            <span className="ap-epochs-label">Epochs</span>
            <div className="ap-epochs-chips">
              {epochs.map((id) => (
                <button
                  key={id}
                  className={`ap-chip ${id === selectedEpoch ? 'is-on' : ''}`}
                  onClick={() => selectEpoch(id)}
                  disabled={disabled}
                >{id}</button>
              ))}
              {epochs.length === 0 && <span className="ap-epochs-none">none settled yet</span>}
            </div>
            <div className="ap-epochs-load">
              <input
                className="ap-input ap-input-sm"
                value={epochInput}
                onChange={(e) => setEpochInput(e.target.value)}
                placeholder="load any id"
                onKeyDown={(e) => { if (e.key === 'Enter' && !disabled) loadTypedEpoch() }}
                disabled={disabled}
              />
              <button className="ap-btn ap-btn-sm" onClick={loadTypedEpoch} disabled={disabled}>Load</button>
            </div>
          </div>




          <div className="ap-grid">
            <section className="ap-ledger">
              <div className="ap-ledger-head">
                <span className="ap-ledger-title">Attribution Ledger</span>
                <span className="ap-ledger-meta">
                  {selectedEpoch || 'no epoch'} · <span className={`ap-outcome ap-outcome-${(outcome || '').toLowerCase()}`}>{outcome || 'not settled'}</span>
                  {prCount ? ' · ' + prCount + ' PRs' : ''}
                </span>
              </div>




              <ul className="ap-rows">
                {contribs.map((c, i) => {
                  const gen = c.allocUnits / 1000
                  const pct = poolUnits ? (c.allocUnits / poolUnits) * 100 : 0
                  const claimed = c.claimedWei > 0n
                  const claimable = c.claimableWei > 0n
                  const idle = c.allocUnits === 0
                  return (
                    <li className={`ap-row ${idle ? 'is-idle' : tones[i % tones.length]}`} key={c.wallet}>
                      <span className="ap-row-top">
                        <span className="ap-row-handle">
                          {c.handle ? '@' + c.handle : shortAddr(c.wallet)}
                          {c.verified && <span className="ap-verif" title="verified">✓</span>}
                        </span>
                        <span className="ap-row-amt">{fmtGen(gen)} <span className="ap-gen">GEN</span></span>
                      </span>
                      <span className="ap-row-track"><span className="ap-row-fill" style={{ width: pct + '%' }} /></span>
                      <span className="ap-row-state">
                        <span>{!c.verified ? 'not verified yet' : idle ? 'no merged work' : claimed ? `claimed ${fmtGen(genFromWei(c.claimedWei))} GEN` : claimable ? `${fmtGen(genFromWei(c.claimableWei))} GEN claimable` : 'pending finalize'}</span>
                        <span className="ap-row-units">{c.allocUnits} / {poolUnits} units</span>
                      </span>
                    </li>
                  )
                })}
                <li className="ap-row is-reserve">
                  <span className="ap-row-top">
                    <span className="ap-row-handle">reserve</span>
                    <span className="ap-row-amt">{fmtGen(reserveUnits / 1000)} <span className="ap-gen">GEN</span></span>
                  </span>
                  <span className="ap-row-track"><span className="ap-row-fill" style={{ width: (poolUnits ? (reserveUnits / poolUnits) * 100 : 0) + '%' }} /></span>
                  <span className="ap-row-state"><span>unallocated, held in pool</span><span className="ap-row-units">{reserveUnits} / {poolUnits} units</span></span>
                </li>
              </ul>




              <div className="ap-ledger-foot">this agreement holds <b>{fmtGen(genFromWei(agPoolWei))} GEN</b></div>
            </section>




            <aside className="ap-side">
              <IdentityPanel account={account} onVerified={() => { refreshAll(aid) }} />




              <div className="ap-minority">
                <span className="ap-side-label">Minority note · on-chain</span>
                <blockquote className="ap-quote">{minority || 'No dissent recorded for this epoch.'}</blockquote>
              </div>




              <div className="ap-actions">
                <span className="ap-side-label">Actions · permissionless</span>
                <div className="ap-action ap-action-col">
                  <input className="ap-input" value={settleId} onChange={(e) => setSettleId(e.target.value)} placeholder="epoch index (0, 1, 2 ...)" disabled={disabled} />
                  <button className="ap-btn" onClick={() => run('Open epoch ' + settleId, () => openSettlement(account!, aid, settleId), settleId)} disabled={disabled}>Open settlement</button>
                  <button className="ap-btn" onClick={() => run('Collect ' + settleId, () => collectBatch(account!, aid, settleId), settleId)} disabled={disabled}>
                    {progress && progress.opened ? `Collect batch · ${progress.collected}/${progress.to_collect}` : 'Collect batch'}
                  </button>
                  <button className="ap-btn" onClick={() => run('Finalize settlement ' + settleId, () => finalizeSettlement(account!, aid, settleId), settleId)} disabled={disabled}>Finalize settlement</button>
                  {progress && progress.opened && (
                    <span className="ap-progress">window {progress.window_start} to {progress.window_end} · collected {progress.collected}/{progress.to_collect}{progress.settled ? ' · settled' : ''}</span>
                  )}
                </div>
                <div className="ap-action">
                  <input className="ap-input" value={finalId} onChange={(e) => setFinalId(e.target.value)} placeholder="epoch id" disabled={disabled} />
                  <button className="ap-btn" onClick={() => run('Finalize ' + finalId, () => finalizeEpoch(account!, aid, finalId), finalId)} disabled={disabled}>Release funds (vault)</button>
                </div>
                <div className="ap-action">
                  <input className="ap-input" value={fundAmt} onChange={(e) => setFundAmt(e.target.value)} placeholder="GEN" disabled={disabled} />
                  <button className="ap-btn" onClick={() => run('Fund ' + fundAmt + ' GEN', () => fundPool(account!, aid, BigInt(Math.round(parseFloat(fundAmt || '0') * 1e18))))} disabled={disabled}>Fund pool</button>
                </div>
                <button className="ap-btn ap-btn-primary" disabled={disabled || myClaimable <= 0} onClick={() => run('Claim', () => claimShare(account!, aid))}>
                  {myClaimable > 0 ? `Claim ${fmtGen(myClaimable)} GEN` : 'Nothing to claim'}
                </button>
                {action && <p className="ap-status">{action}</p>}
                {loading && !action && <p className="ap-status">reading chain...</p>}
              </div>
            </aside>
          </div>




          <footer className="ap-foot">
            <a href={EXPLORER + ASSESSOR_CONTRACT_ADDRESS} target="_blank" rel="noopener noreferrer">assessor {shortAddr(ASSESSOR_CONTRACT_ADDRESS)} ↗</a>
            <a href={EXPLORER + VAULT_CONTRACT_ADDRESS} target="_blank" rel="noopener noreferrer">vault {shortAddr(VAULT_CONTRACT_ADDRESS)} ↗</a>
          </footer>
        </main>
      )}
    </div>
  )
}




export default App
