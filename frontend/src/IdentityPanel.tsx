import { useState, useEffect, useCallback } from 'react'
import './IdentityPanel.css'
import {
  isVerified, getHandle, getPendingNonce,
  requestVerification, confirmVerification,
} from './lib/accrue'

type Props = { account: string; onVerified: () => void }

function IdentityPanel({ account, onVerified }: Props) {
  const [verified, setVerified] = useState(false)
  const [handle, setHandle] = useState('')
  const [nonce, setNonce] = useState('')
  const [handleInput, setHandleInput] = useState('')
  const [gistInput, setGistInput] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    try {
      const v = await isVerified(account)
      setVerified(v as boolean)
      if (v) {
        setHandle((await getHandle(account)) as string)
      } else {
        setNonce(((await getPendingNonce(account)) as string) || '')
      }
    } catch { /* ignore */ }
  }, [account])

  useEffect(() => { load() }, [load])

  const gistLine = nonce ? nonce + ' ' + account : ''

  async function doRequest() {
    const h = handleInput.trim()
    if (!h) { setStatus('Enter your GitHub username first.'); return }
    setBusy(true); setStatus('Requesting your code, approve in your wallet...')
    try {
      await requestVerification(account, h)
      const n = ((await getPendingNonce(account)) as string) || ''
      setNonce(n)
      setStatus(n ? 'Code issued. Publish it in a public gist under @' + h + '.' : 'Code issued.')
    } catch (e: any) {
      setStatus('Failed: ' + (e?.message || String(e)).slice(0, 120))
    } finally { setBusy(false) }
  }

  async function doConfirm() {
    const u = gistInput.trim()
    if (!u) { setStatus('Paste your public gist URL first.'); return }
    setBusy(true); setStatus('Verifying, the contract is fetching your gist...')
    try {
      await confirmVerification(account, u)
      setStatus('Verified.')
      await load()
      onVerified()
    } catch (e: any) {
      setStatus('Failed: ' + (e?.message || String(e)).slice(0, 160))
    } finally { setBusy(false) }
  }

  function copyLine() {
    navigator.clipboard.writeText(gistLine).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    }).catch(() => {})
  }

  if (verified) {
    return (
      <div className="id-panel is-done">
        <span className="ap-side-label">Identity · verified on-chain</span>
        <div className="id-done">
          <span className="id-check">✓</span>
          <div>
            <span className="id-done-handle">@{handle}</span>
            <span className="id-done-sub">This wallet is proven to control the GitHub account.</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="id-panel">
      <span className="ap-side-label">Identity · not verified</span>
      <p className="id-lede">
        Prove this wallet controls your GitHub account. Only work by a verified
        contributor earns a share.
      </p>

      <div className="id-step">
        <span className="id-step-n">1</span>
        <div className="id-step-body">
          <div className="ap-action">
            <input
              className="ap-input"
              value={handleInput}
              onChange={(e) => setHandleInput(e.target.value)}
              placeholder="your GitHub username"
              disabled={busy}
            />
            <button className="ap-btn" onClick={doRequest} disabled={busy}>Get code</button>
          </div>
        </div>
      </div>

      {nonce && (
        <>
          <div className="id-step">
            <span className="id-step-n">2</span>
            <div className="id-step-body">
              <p className="id-instruct">
                Create a <b>public gist</b> under your own GitHub account containing
                exactly this line:
              </p>
              <div className="id-code">
                <code>{gistLine}</code>
                <button className="id-copy" onClick={copyLine}>{copied ? 'copied' : 'copy'}</button>
              </div>
            </div>
          </div>

          <div className="id-step">
            <span className="id-step-n">3</span>
            <div className="id-step-body">
              <div className="ap-action">
                <input
                  className="ap-input"
                  value={gistInput}
                  onChange={(e) => setGistInput(e.target.value)}
                  placeholder="https://gist.github.com/..."
                  disabled={busy}
                />
                <button className="ap-btn" onClick={doConfirm} disabled={busy}>Verify</button>
              </div>
              <p className="id-note">
                The contract fetches that page itself and checks it by consensus. A
                gist under a different account, or one missing this line, is rejected.
              </p>
            </div>
          </div>
        </>
      )}

      {status && <p className="ap-status">{status}</p>}
    </div>
  )
}

export default IdentityPanel
