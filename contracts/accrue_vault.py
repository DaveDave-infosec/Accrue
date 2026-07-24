# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

# Each pool "unit" from an assessor allocation = this many wei of native GEN.
# A 1000-unit pool therefore equals 1 GEN.
WEI_PER_UNIT = 1000000000000000  # 10^15 wei = 0.001 GEN


class AccrueVault(gl.Contract):
    # MULTI-TENANT. Every agreement holds its OWN pool, funded and claimed
    # separately, so no agreement can ever spend another's money.
    # finalize_epoch is PERMISSIONLESS and reads the split straight from the
    # assessor. The vault has ZERO power over who is paid or how much.
    assessor: Address

    ag_pool_wei: TreeMap[str, u256]        # aid -> unallocated funds held
    ag_funded_wei: TreeMap[str, u256]      # aid -> lifetime funded
    ag_reserve_wei: TreeMap[str, u256]     # aid -> lifetime returned to reserve
    claimable: TreeMap[str, u256]          # "aid:wallet" -> claimable wei
    claimed: TreeMap[str, u256]            # "aid:wallet" -> lifetime claimed wei
    epoch_finalized: TreeMap[str, bool]    # "aid:epoch"
    epoch_outcome_v: TreeMap[str, str]     # "aid:epoch"

    def __init__(self, assessor_address: str):
        self.assessor = Address(assessor_address)

    # ---- fund one agreement's pool with native GEN ----
    @gl.public.write.payable
    def fund_pool(self, agreement_id: str) -> None:
        aid = agreement_id
        amount = int(gl.message.value)
        assert amount > 0, "no value sent"
        proxy = gl.get_contract_at(self.assessor)
        ag = proxy.view().get_agreement(aid)
        assert ag["exists"], "agreement does not exist"
        self.ag_pool_wei[aid] = u256(int(self.ag_pool_wei.get(aid, u256(0))) + amount)
        self.ag_funded_wei[aid] = u256(int(self.ag_funded_wei.get(aid, u256(0))) + amount)

    # ---- PERMISSIONLESS finalize: read the assessor's verdict, record claimables ----
    @gl.public.write
    def finalize_epoch(self, agreement_id: str, epoch_id: str) -> str:
        aid = agreement_id
        ekey = aid + ":" + epoch_id
        assert not self.epoch_finalized.get(ekey, False), "epoch already finalized"

        proxy = gl.get_contract_at(self.assessor)
        ep = proxy.view().get_epoch(aid, epoch_id)
        assert ep["settled"], "assessor has not settled this epoch"
        outcome = str(ep["outcome"])

        contributors = proxy.view().get_contributors(aid)
        pending = []
        total_wei = 0
        for i in range(len(contributors)):
            w = str(contributors[i]).lower()
            if w == "":
                continue
            units = int(proxy.view().get_epoch_allocation(aid, epoch_id, w))
            if units > 0:
                wei = units * WEI_PER_UNIT
                pending.append((w, wei))
                total_wei += wei

        available = int(self.ag_pool_wei.get(aid, u256(0)))
        assert available >= total_wei, "agreement pool underfunded for this settlement"

        for pair in pending:
            key = aid + ":" + pair[0]
            self.claimable[key] = u256(int(self.claimable.get(key, u256(0))) + pair[1])

        self.ag_pool_wei[aid] = u256(available - total_wei)

        reserve_units = int(ep["reserve"])
        self.ag_reserve_wei[aid] = u256(
            int(self.ag_reserve_wei.get(aid, u256(0))) + reserve_units * WEI_PER_UNIT
        )

        self.epoch_finalized[ekey] = True
        self.epoch_outcome_v[ekey] = outcome
        return outcome

    # ---- contributor claims their own accrued GEN for one agreement ----
    @gl.public.write
    def claim(self, agreement_id: str) -> str:
        caller = str(gl.message.sender_address).lower()
        key = agreement_id + ":" + caller
        amt = int(self.claimable.get(key, u256(0)))
        assert amt > 0, "nothing to claim"
        assert int(self.balance) >= amt, "vault underfunded for this claim"
        self.claimable[key] = u256(0)
        self.claimed[key] = u256(int(self.claimed.get(key, u256(0))) + amt)
        gl.get_contract_at(Address(caller)).emit_transfer(value=u256(amt))
        return str(amt)

    # ---- views ----
    @gl.public.view
    def get_claimable(self, agreement_id: str, wallet: str) -> u256:
        return self.claimable.get(agreement_id + ":" + wallet.lower(), u256(0))

    @gl.public.view
    def get_claimed(self, agreement_id: str, wallet: str) -> u256:
        return self.claimed.get(agreement_id + ":" + wallet.lower(), u256(0))

    @gl.public.view
    def get_agreement_pool(self, agreement_id: str) -> u256:
        return self.ag_pool_wei.get(agreement_id, u256(0))

    @gl.public.view
    def get_agreement_funded(self, agreement_id: str) -> u256:
        return self.ag_funded_wei.get(agreement_id, u256(0))

    @gl.public.view
    def get_reserve_total(self, agreement_id: str) -> u256:
        return self.ag_reserve_wei.get(agreement_id, u256(0))

    @gl.public.view
    def get_pool_balance(self) -> u256:
        return self.balance

    @gl.public.view
    def is_finalized(self, agreement_id: str, epoch_id: str) -> bool:
        return self.epoch_finalized.get(agreement_id + ":" + epoch_id, False)

    @gl.public.view
    def get_epoch_outcome(self, agreement_id: str, epoch_id: str) -> str:
        return self.epoch_outcome_v.get(agreement_id + ":" + epoch_id, "")

    @gl.public.view
    def get_assessor(self) -> str:
        return self.assessor.as_hex
