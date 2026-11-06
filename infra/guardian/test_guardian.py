"""Guardian (guardian.py) against a stand-in node, with IDNI's own bot code and the node's own signature check.

Needs a tau-testnet checkout (TAU_TESTNET_DIR, the commit our node runs; the CI job fetches it) and py-ecc + blake3.
Without them the test says so and passes, so a laptop without the checkout is not blocked.
"""
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GIVEN = "TAU_TESTNET_DIR" in os.environ   # set by the CI job: then a missing piece is a failure, not a skip
SRC = os.environ.get("TAU_TESTNET_DIR", os.path.join(HERE, "..", "..", "..", "tau-testnet"))
os.environ["TAU_TESTNET_DIR"] = SRC
sys.path.insert(0, HERE)
try:
    import guardian  # noqa: E402
    from approval_bot_totp import totp_at  # noqa: E402
    from consensus.tx_signing import verify_tx_signature  # noqa: E402
    from py_ecc.bls import G2Basic  # noqa: E402
except ImportError as exc:   # no checkout here
    if GIVEN:
        raise
    print(f"skipped: {exc} (set TAU_TESTNET_DIR to a tau-testnet checkout)")
    raise SystemExit(0)

OWNER_SK = 1234567
OWNER = G2Basic.SkToPk(OWNER_SK).hex()
STRANGER_SK = 7654321
STRANGER = G2Basic.SkToPk(STRANGER_SK).hex()
RID = "ab" * 32


def proof(sk, action, account, at):
    return G2Basic.Sign(sk, hashlib.sha256(guardian.proof_text(action, account, at)).digest()).hex()


class Node:
    """The node's RPC as far as the Guardian uses it; every vote is checked with the node's own verify."""

    def __init__(self):
        self.requests, self.sent, self.seq, self.refuse = [], [], 0, False

    def data(self, cmd):
        res = self.rpc(cmd)
        if res.get("status") != "ok":
            raise guardian.idni_common.RpcError(json.dumps(res))
        return res["data"]

    def rpc(self, cmd):
        name, _, rest = cmd.partition(" ")
        if name == "getsequence":
            return {"status": "ok", "data": {"sequence_number": self.seq, "tip_height": 900}}
        if name == "getapprovalrequests":
            pk = rest.split()[0]
            return {"status": "ok", "data": {"incoming": [r for r in self.requests
                                                          if any(a["pubkey"] == pk for a in r["approvers"].values())]}}
        if name == "sendtx":
            tx = json.loads(rest.strip("'"))
            ok, why = verify_tx_signature(tx)
            assert ok, why
            if self.refuse:
                return {"status": "error", "error": {"code": "TX_REJECTED", "message": "busy"}}
            self.sent.append(tx)
            self.seq += 1
            for r in self.requests:
                if r["request_id"] == tx["request_id"]:
                    for a in r["approvers"].values():
                        if a["pubkey"] == tx["sender_pubkey"]:
                            a["state"] = "approved"
            return {"status": "ok", "data": {"tx_hash": "cd" * 32}}
        raise AssertionError(cmd)


class GuardianTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.node = Node()
        self.g = guardian.Guardian(self.dir, client=self.node)

    def enrol(self, account=OWNER, sk=OWNER_SK):
        at = int(time.time())
        r = self.g.enroll({"account": account, "at": at, "signature": proof(sk, "enroll", account, at)}, "1.1.1.1")
        self.assertIn("otpauth://totp/", r["uri"])
        self.assertIn("issuer=Tau%20HUD%20Guardian", r["uri"])
        return r["secret"]

    def park(self, sender=OWNER, rid=RID):
        self.node.requests.append({"request_id": rid, "sender_pubkey": sender, "recipient_pubkey": STRANGER, "amount": 5000,
                                   "status": "open", "approvers": {"18": {"pubkey": self.g.pubkey, "state": "awaiting"}}})

    def test_key_made_once_and_kept_private(self):
        path = os.path.join(self.dir, "guardian.key")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        again = guardian.Guardian(self.dir, client=self.node)
        self.assertEqual(again.pubkey, self.g.pubkey)
        self.assertEqual(len(self.g.pubkey), 96)

    def test_enrolment_needs_the_account_key_and_a_first_code(self):
        at = int(time.time())
        with self.assertRaises(guardian.Refused) as c:   # someone else's key cannot connect a phone to this account
            self.g.enroll({"account": OWNER, "at": at, "signature": proof(STRANGER_SK, "enroll", OWNER, at)}, "1.1.1.1")
        self.assertEqual(c.exception.status, 403)
        with self.assertRaises(guardian.Refused):          # an old signature
            self.g.enroll({"account": OWNER, "at": at - 3600, "signature": proof(OWNER_SK, "enroll", OWNER, at - 3600)}, "1.1.1.2")
        secret = self.enrol()
        self.assertFalse(self.g.account(OWNER)["enrolled"])   # the QR code alone does not count yet
        with self.assertRaises(guardian.Refused):
            self.g.confirm({"account": OWNER, "code": "000000" if totp_at(secret, time.time()) != "000000" else "111111"}, "1.1.1.1")
        self.assertEqual(self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time())}, "1.1.1.1"), {"enrolled": True})
        self.assertTrue(self.g.account(OWNER)["enrolled"])
        store = os.path.join(self.dir, "enroll", "enrollments.json")
        self.assertEqual(os.stat(store).st_mode & 0o777, 0o600)
        with open(os.path.join(self.dir, "guardian.json")) as f:
            self.assertNotIn(secret, f.read())   # the stats file holds no secret

    def test_moving_to_a_new_phone_needs_the_old_code(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time())}, "1.1.1.1")
        at = int(time.time())
        with self.assertRaises(guardian.Refused) as c:
            self.g.enroll({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "enroll", OWNER, at)}, "1.1.1.3")
        self.assertEqual(c.exception.status, 403)

    def test_a_right_code_cosigns_with_a_valid_feeless_vote(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.park()
        r = self.g.approve({"request_id": RID, "code": totp_at(secret, time.time())}, "1.1.1.1")
        self.assertTrue(r["approved"])
        vote = self.node.sent[0]
        self.assertEqual(vote["tx_type"], "transfer_vote")
        self.assertEqual(vote["fee_limit"], "0")
        self.assertIs(vote["approve"], True)
        self.assertEqual(vote["sender_pubkey"], self.g.pubkey)
        self.assertNotIn(totp_at(secret, time.time()), json.dumps(vote))   # the code never goes on chain
        self.assertEqual(self.g.account(OWNER)["approvals"], 1)
        try:   # the same fields as IDNI's own builder, where the full node code is importable
            from tau_testnet_cli.tx import build_transfer_vote_tx
        except Exception:
            return
        ref = build_transfer_vote_tx(sender_pubkey=vote["sender_pubkey"], sequence_number=vote["sequence_number"],
                                     expiration_time=vote["expiration_time"], expire_at_height=vote["expire_at_height"],
                                     request_id=vote["request_id"], approve=True, reason=vote["reason"])
        self.assertEqual(ref, {k: v for k, v in vote.items() if k != "signature"})

    def test_wrong_codes_lock_the_account_and_codes_are_one_use(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.park()
        right = totp_at(secret, time.time())
        bad = [c for c in ("000001", "000002", "000003", "000004", "000005", "000006") if c != right][:5]
        for i, c in enumerate(bad):
            with self.assertRaises(guardian.Refused):
                self.g.approve({"request_id": RID, "code": c}, f"2.2.2.{i}")
        with self.assertRaises(guardian.Refused) as locked:
            self.g.approve({"request_id": RID, "code": right}, "2.2.3.1")
        self.assertEqual(locked.exception.status, 429)
        self.assertEqual(self.node.sent, [])

    def test_only_payments_that_name_the_guardian_and_only_enrolled_accounts(self):
        self.park()   # OWNER not enrolled
        with self.assertRaises(guardian.Refused) as c:
            self.g.approve({"request_id": RID, "code": "123456"}, "3.3.3.3")
        self.assertEqual(c.exception.status, 403)
        with self.assertRaises(guardian.Refused) as c:
            self.g.approve({"request_id": "ef" * 32, "code": "123456"}, "3.3.3.4")
        self.assertEqual(c.exception.status, 404)
        self.assertEqual(self.node.sent, [])

    def test_a_refused_vote_is_sent_again_by_the_poll(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.park()
        self.node.refuse = True
        with self.assertRaises(guardian.Refused) as c:
            self.g.approve({"request_id": RID, "code": totp_at(secret, time.time())}, "1.1.1.1")
        self.assertEqual(c.exception.status, 502)
        self.node.refuse = False
        self.g.bot.tick()   # IDNI's poll: the accepted code is still good for this request
        self.assertEqual(len(self.node.sent), 1)

    def test_remove_needs_key_and_code(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        at = int(time.time())
        with self.assertRaises(guardian.Refused):
            self.g.remove({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "remove", OWNER, at), "code": "12"}, "4.4.4.4")
        r = self.g.remove({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "remove", OWNER, at),
                           "code": totp_at(secret, time.time())}, "4.4.4.5")
        self.assertEqual(r, {"removed": True})
        self.assertFalse(self.g.account(OWNER)["enrolled"])

    def test_capacity(self):
        old = guardian.MAX_ACCOUNTS
        guardian.MAX_ACCOUNTS = 1
        try:
            secret = self.enrol()
            self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time())}, "1.1.1.1")
            at = int(time.time())
            with self.assertRaises(guardian.Refused) as c:
                self.g.enroll({"account": STRANGER, "at": at, "signature": proof(STRANGER_SK, "enroll", STRANGER, at)}, "5.5.5.5")
            self.assertEqual(c.exception.status, 409)
        finally:
            guardian.MAX_ACCOUNTS = old

    def settings(self, auto, secret, ip="6.6.6.6", t=None):
        at = int(time.time())
        return self.g.settings({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "settings", OWNER, at),
                                "code": totp_at(secret, t or time.time()), "auto": auto}, ip)

    def test_settings_need_key_and_code(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        at = int(time.time())
        with self.assertRaises(guardian.Refused) as c:   # a stranger's key
            self.g.settings({"account": OWNER, "at": at, "signature": proof(STRANGER_SK, "settings", OWNER, at),
                             "code": totp_at(secret, time.time()), "auto": {"per": 100, "day": 500}}, "6.6.6.1")
        self.assertEqual(c.exception.status, 403)
        with self.assertRaises(guardian.Refused):          # the key, but a wrong code
            self.g.settings({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "settings", OWNER, at),
                             "code": "000000" if totp_at(secret, time.time()) != "000000" else "111111", "auto": None}, "6.6.6.2")
        with self.assertRaises(guardian.Refused):          # per above day
            self.settings({"per": 600, "day": 500}, secret)
        self.assertEqual(self.settings({"per": 100, "day": 500}, secret, t=time.time() + 30), {"auto": {"per": 100, "day": 500}})
        self.assertEqual(self.g.account(OWNER)["auto"], {"per": 100, "day": 500})
        self.assertEqual(self.g.account(OWNER)["today"]["sum"], 0)

    def test_allowance_signs_small_payments_by_itself_until_the_day_is_spent(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.settings({"per": 100, "day": 250}, secret)
        self.park(rid="01" * 32); self.node.requests[-1]["amount"] = 100
        self.park(rid="02" * 32); self.node.requests[-1]["amount"] = 101   # above per: waits for a code
        self.park(rid="03" * 32); self.node.requests[-1]["amount"] = 100
        self.park(rid="04" * 32); self.node.requests[-1]["amount"] = 100   # 300 > 250: waits for a code
        self.g.bot.tick()
        self.assertEqual([t["request_id"] for t in self.node.sent], ["01" * 32, "03" * 32])
        self.assertTrue(all(t["reason"] == guardian.AUTO_REASON for t in self.node.sent))
        today = self.g.account(OWNER)["today"]
        self.assertEqual((today["sum"], today["count"]), (200, 2))
        self.g.bot.tick()
        self.assertEqual(len(self.node.sent), 2)   # nothing signed twice, the two others still wait
        r = self.g.approve({"request_id": "02" * 32, "code": totp_at(secret, time.time() + 30)}, "1.1.1.1")   # the code still works for them
        self.assertTrue(r["approved"])
        self.assertEqual(self.g.account(OWNER)["today"]["sum"], 200)   # a code-confirmed payment does not use the allowance

    def test_a_new_day_starts_the_allowance_afresh_and_always_mode_never_signs_alone(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.settings({"per": 100, "day": 100}, secret)
        self.park(rid="05" * 32); self.node.requests[-1]["amount"] = 100
        self.g.bot.tick()
        self.assertEqual(len(self.node.sent), 1)
        self.g.clock = lambda: time.time() + 86400   # tomorrow (UTC)
        self.park(rid="06" * 32); self.node.requests[-1]["amount"] = 100
        self.g.bot.tick()
        self.assertEqual(len(self.node.sent), 2)
        self.g.clock = time.time
        self.settings(None, secret, t=time.time() + 30)   # every payment wants a code now
        self.park(rid="07" * 32); self.node.requests[-1]["amount"] = 1
        self.g.bot.tick()
        self.assertEqual(len(self.node.sent), 2)

    def test_no_allowance_for_an_account_that_left(self):
        secret = self.enrol()
        self.g.confirm({"account": OWNER, "code": totp_at(secret, time.time() - 30)}, "1.1.1.1")
        self.settings({"per": 100, "day": 100}, secret)
        at = int(time.time())
        self.g.remove({"account": OWNER, "at": at, "signature": proof(OWNER_SK, "remove", OWNER, at), "code": totp_at(secret, time.time() + 30)}, "4.4.4.5")
        self.park(rid="08" * 32); self.node.requests[-1]["amount"] = 10
        self.g.bot.tick()
        self.assertEqual(self.node.sent, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
