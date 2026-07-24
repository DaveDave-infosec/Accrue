import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { getAddress } from "viem";
import { STUDIO_CHAIN_HEX } from "./constants";

// Read-only client at module level — no account needed for view methods.
export const publicClient: any = createClient({ chain: studionet } as any);

// Write-client factory — genlayer-js 1.x requires the account at createClient
// time (never per-call). One client per connected account.
let cachedWriteClient: any = null;
let cachedAccount: string | null = null;

export function getWalletClient(account: string): any {
  // viem rejects lowercase addresses on writes with a misleading error —
  // normalize to EIP-55 checksum (proven fix from prior builds).
  const acct = getAddress(account);
  if (cachedWriteClient && cachedAccount === acct) {
    return cachedWriteClient;
  }
  cachedWriteClient = createClient({
    chain: studionet,
    account: acct as `0x${string}`,
  } as any);
  cachedAccount = acct;
  return cachedWriteClient;
}

function getInjectedProvider(): any {
  const eth = (window as any).ethereum;
  if (!eth) {
    throw new Error(
      "No wallet detected. Install a browser wallet (e.g. MetaMask) to continue."
    );
  }
  return eth;
}

// Connect wallet + ensure Studio network. Returns the lowercased address.
export async function connectWallet(): Promise<string> {
  const eth = getInjectedProvider();
  const accounts: string[] = await eth.request({
    method: "eth_requestAccounts",
  });
  if (!accounts || accounts.length === 0) {
    throw new Error("No account returned from wallet.");
  }
  await ensureStudioChain();
  return accounts[0].toLowerCase();
}

// Prompt the wallet to switch/select an authorized account from the UI.
// Uses wallet_requestPermissions so the account picker opens; falls back to a
// plain eth_requestAccounts if the wallet does not support it.
export async function requestAccountSwitch(): Promise<string | null> {
  const eth = getInjectedProvider();
  try {
    await eth.request({
      method: "wallet_requestPermissions",
      params: [{ eth_accounts: {} }],
    });
  } catch {
    // some wallets reject/no-op this; fall through to reading accounts
  }
  const accounts: string[] = await eth.request({ method: "eth_requestAccounts" });
  await ensureStudioChain();
  if (accounts && accounts.length > 0) return accounts[0].toLowerCase();
  return null;
}

export async function getCurrentAccount(): Promise<string | null> {
  const eth = (window as any).ethereum;
  if (!eth) return null;
  try {
    const accounts: string[] = await eth.request({ method: "eth_accounts" });
    if (accounts && accounts.length > 0) return accounts[0].toLowerCase();
  } catch {
    // ignore
  }
  return null;
}

export function onAccountChange(cb: (account: string | null) => void): () => void {
  const eth = (window as any).ethereum;
  if (!eth || !eth.on) return () => {};
  const handler = (accounts: string[]) => {
    if (accounts && accounts.length > 0) cb(accounts[0].toLowerCase());
    else cb(null);
  };
  eth.on("accountsChanged", handler);
  return () => {
    if (eth.removeListener) eth.removeListener("accountsChanged", handler);
  };
}

async function ensureStudioChain(): Promise<void> {
  const eth = getInjectedProvider();
  try {
    await eth.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: STUDIO_CHAIN_HEX }],
    });
  } catch (err: any) {
    if (err && err.code === 4902) {
      await eth.request({
        method: "wallet_addEthereumChain",
        params: [
          {
            chainId: STUDIO_CHAIN_HEX,
            chainName: "GenLayer Studio Network",
            nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
            rpcUrls: ["https://studio.genlayer.com/api"],
          },
        ],
      });
    } else {
      throw err;
    }
  }
}

// Read concurrency limiter — the Studio node has 8 execution slots shared by
// everyone. Cap our in-flight reads at 4; queue the rest.
const MAX_CONCURRENT_READS = 4;
let activeReads = 0;
const readQueue: (() => void)[] = [];

function acquireReadSlot(): Promise<void> {
  return new Promise((resolve) => {
    if (activeReads < MAX_CONCURRENT_READS) {
      activeReads++;
      resolve();
    } else {
      readQueue.push(() => {
        activeReads++;
        resolve();
      });
    }
  });
}

function releaseReadSlot(): void {
  activeReads--;
  const next = readQueue.shift();
  if (next) next();
}

const READ_ATTEMPTS = 6;
const BACKOFF_BASE_MS = 400;
const BACKOFF_CAP_MS = 5000;

export async function readContract(params: {
  address: string;
  functionName: string;
  args?: any[];
}): Promise<any> {
  const { address, functionName, args = [] } = params;
  let lastErr: any = null;
  for (let attempt = 0; attempt < READ_ATTEMPTS; attempt++) {
    await acquireReadSlot();
    try {
      const result = await publicClient.readContract({
        address: address as `0x${string}`,
        functionName,
        args,
      });
      return result;
    } catch (err) {
      lastErr = err;
    } finally {
      releaseReadSlot();
    }
    const backoff = Math.min(BACKOFF_BASE_MS * Math.pow(2, attempt), BACKOFF_CAP_MS);
    const jitter = Math.random() * 250;
    await sleep(backoff + jitter);
  }
  throw lastErr;
}

// Write a method: send the tx, then poll the receipt until ACCEPTED.
// value is optional — 0 for normal writes, non-zero for payable fund_pool.
export async function writeContract(params: {
  account: string;
  address: string;
  functionName: string;
  args?: any[];
  value?: bigint;
}): Promise<any> {
  const { account, address, functionName, args = [], value = 0n } = params;
  const wallet = getWalletClient(account);

  // genlayer-js 1.x carries native value in the call options, not as a bare
  // top-level field (viem style). Pass it both ways so whichever the pinned
  // version reads picks it up; a 0 value stays a plain non-payable call.
  const call: any = {
    address: address as `0x${string}`,
    functionName,
    args,
  };
  if (value && value > 0n) {
    call.value = value;
    call.transactionOptions = { value };
  }

  const txHash = await wallet.writeContract(call);

  const receipt = await publicClient.waitForTransactionReceipt({
    hash: txHash,
    status: "ACCEPTED",
    retries: 40,
    interval: 3000,
  });

  // Consensus ACCEPTED only means validators AGREED on the outcome. If the
  // contract reverted, they agreed it reverted, and execution_result is ERROR.
  // Surface that as a real failure with the contract's own message.
  const execError = findExecutionError(receipt);
  if (execError) {
    throw new Error(execError);
  }

  return { txHash, receipt };
}

// Returns a human-readable error if the transaction executed with an error,
// otherwise null.
function findExecutionError(receipt: any): string | null {
  const leader = receipt?.consensus_data?.leader_receipt;
  const entries = Array.isArray(leader) ? leader : leader ? [leader] : [];
  // Only the leader's own execution is authoritative. Studio cancels the
  // remaining validators once quorum is reached, and those cancelled entries
  // report an error even though the transaction itself succeeded.
  const first = entries[0];
  if (!first) return null;
  const result = String(first?.execution_result || "").toUpperCase();
  if (result !== "ERROR") return null;

  const stderr = String(first?.genvm_result?.stderr || "");
  const message = extractContractMessage(stderr);

  // A genuine contract revert surfaces as an assertion from our own code.
  // Anything else is a node-level condition, where the transaction may still
  // have gone through, so say so plainly instead of claiming it failed.
  if (/assertion/i.test(stderr) || /AssertionError/.test(stderr)) {
    return message || "the contract rejected this transaction";
  }
  if (/cancel|timeout|quorum/i.test(stderr) || /cancel|timeout|quorum/i.test(message || "")) {
    return "the node reported: " + (message || "execution interrupted") +
      ". This may be temporary, refresh to check whether it went through.";
  }
  return message || "the contract rejected this transaction";
}

// Pull the meaningful line out of a Python traceback, e.g.
// "AssertionError: agreement pool underfunded for this settlement".
function extractContractMessage(stderr: string): string | null {
  if (!stderr) return null;
  const lines = stderr.split("\n").map((l) => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    const match = line.match(/^[A-Za-z_.]*(Error|Exception)\s*:\s*(.+)$/);
    if (match && match[2]) return match[2].trim();
  }
  const last = lines[lines.length - 1];
  return last ? last.slice(0, 160) : null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
