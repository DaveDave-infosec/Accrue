import { readContract, writeContract } from "./genlayer";
import { ASSESSOR_CONTRACT_ADDRESS, VAULT_CONTRACT_ADDRESS } from "./constants";

const A = ASSESSOR_CONTRACT_ADDRESS;
const V = VAULT_CONTRACT_ADDRESS;

// ---------- assessor: agreements ----------
export async function getAgreementCount(): Promise<any> {
  return readContract({ address: A, functionName: "get_agreement_count" });
}
export async function getAgreement(agreementId: string): Promise<any> {
  return readContract({ address: A, functionName: "get_agreement", args: [agreementId] });
}
export async function getContributors(agreementId: string): Promise<string[]> {
  return readContract({ address: A, functionName: "get_contributors", args: [agreementId] });
}
export async function getEpochs(agreementId: string): Promise<string[]> {
  return readContract({ address: A, functionName: "get_epochs", args: [agreementId] });
}
export async function getEpoch(agreementId: string, epochId: string): Promise<any> {
  return readContract({ address: A, functionName: "get_epoch", args: [agreementId, epochId] });
}
export async function getEpochAllocation(agreementId: string, epochId: string, wallet: string): Promise<any> {
  return readContract({ address: A, functionName: "get_epoch_allocation", args: [agreementId, epochId, wallet] });
}

// ---------- assessor: identity (global) ----------
export async function isVerified(wallet: string): Promise<boolean> {
  return readContract({ address: A, functionName: "is_verified", args: [wallet] });
}
export async function getHandle(wallet: string): Promise<string> {
  return readContract({ address: A, functionName: "get_handle", args: [wallet] });
}
export async function getPendingNonce(wallet: string): Promise<string> {
  return readContract({ address: A, functionName: "get_pending_nonce", args: [wallet] });
}

// ---------- vault reads ----------
export async function getClaimable(agreementId: string, wallet: string): Promise<any> {
  return readContract({ address: V, functionName: "get_claimable", args: [agreementId, wallet] });
}
export async function getClaimed(agreementId: string, wallet: string): Promise<any> {
  return readContract({ address: V, functionName: "get_claimed", args: [agreementId, wallet] });
}
export async function getAgreementPool(agreementId: string): Promise<any> {
  return readContract({ address: V, functionName: "get_agreement_pool", args: [agreementId] });
}
export async function getAgreementFunded(agreementId: string): Promise<any> {
  return readContract({ address: V, functionName: "get_agreement_funded", args: [agreementId] });
}
export async function getReserveTotal(agreementId: string): Promise<any> {
  return readContract({ address: V, functionName: "get_reserve_total", args: [agreementId] });
}
export async function isFinalized(agreementId: string, epochId: string): Promise<boolean> {
  return readContract({ address: V, functionName: "is_finalized", args: [agreementId, epochId] });
}

// ---------- writes: identity ----------
export async function requestVerification(account: string, githubHandle: string): Promise<any> {
  return writeContract({ account, address: A, functionName: "request_verification", args: [githubHandle] });
}
export async function confirmVerification(account: string, gistUrl: string): Promise<any> {
  return writeContract({ account, address: A, functionName: "confirm_verification", args: [gistUrl] });
}

// ---------- writes: agreements + settlement ----------
export async function createAgreement(account: string, p: {
  label: string; repoOwner: string; repoName: string;
  c1: string; c2: string; c3: string;
  rubricJson: string; eligibilityJson: string;
  epochLengthSeconds: number; poolPerEpoch: number;
  maxPerContributor: number; challengeWindowSeconds: number; reserveRule: string;
}): Promise<any> {
  return writeContract({
    account, address: A, functionName: "create_agreement",
    args: [
      p.label, p.repoOwner, p.repoName, p.c1, p.c2, p.c3,
      p.rubricJson, p.eligibilityJson, p.epochLengthSeconds, p.poolPerEpoch,
      p.maxPerContributor, p.challengeWindowSeconds, p.reserveRule,
    ],
  });
}
export async function settleEpoch(account: string, agreementId: string, epochId: string): Promise<any> {
  return writeContract({ account, address: A, functionName: "settle_epoch", args: [agreementId, epochId] });
}

// ---------- writes: vault ----------
export async function finalizeEpoch(account: string, agreementId: string, epochId: string): Promise<any> {
  return writeContract({ account, address: V, functionName: "finalize_epoch", args: [agreementId, epochId] });
}
export async function claim(account: string, agreementId: string): Promise<any> {
  return writeContract({ account, address: V, functionName: "claim", args: [agreementId] });
}
export async function fundPool(account: string, agreementId: string, value: bigint): Promise<any> {
  return writeContract({ account, address: V, functionName: "fund_pool", args: [agreementId], value });
}
