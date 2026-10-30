"""The islanders' voices: the server reads the same lines the game speaks (rabbit/voices.json, made from rico.js),
names the clips the same way, and every line a place speaks in game.js is in the list with the right speaker."""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import types

import make

ls = make.lines()
assert len(ls) == len(set(ls)), "a line twice"
texts = {t for w, t in ls}
assert ("rico", "Pact news: Hana and Baako shook hands at La Ola. Lola counted the fingers afterwards.") in ls
assert ("rico", "Day 3 of 5. If you still don't know who to vote for, neither do the gulls.") in ls
assert ("rico", "Baako took 40 coins from the North Wind Embassy!") in ls
assert ("salado", "35 coins, today. All we ask is that you propose “A road round the island” before the election. A small thing between friends.") in ls
assert ("tobias", "After what you did? Buy yourself a lemonade.") in ls
assert not any("{" in t or "${" in t for t in texts), "a placeholder left in a spoken line"
assert not any(re.search(r"\d{3,}", t) for t in texts), "a block height or big number in a spoken line"
assert {w for w, t in ls} == set(make.CAST), "someone speaks without a voice description, or the other way round"
assert make.key("rico", "Chain weather.") == hashlib.sha1("rico|Chain weather.".encode()).hexdigest()[:16]
print(f"{len(ls)} lines, {sum(len(t) for w, t in ls)} characters")

# every line the game asks for exists, said by whoever the game shows
src = open(os.path.join(make.REPO, "rabbit", "rico.js"), encoding="utf-8").read()
game = open(os.path.join(make.REPO, "rabbit", "game.js"), encoding="utf-8").read()
keys = set(re.findall(r'^\s*(\w+): "', re.search(r"const L = \{(.*?)\n  \};", src, re.S).group(1), re.M))
for k in re.findall(r'\bV\("(\w+)"', game):
    assert k in keys, f"game.js speaks {k}, which rico.js does not have"
for k in re.findall(r'V\(sim \? "(\w+)" : "(\w+)"\)', game)[0]:
    assert k in keys, k
said = lambda who, t: (who, t) in ls
for m in re.finditer(r'scene\(box, "(\w+)", T\("[^"]*"\), T\("([^"]+)"\)', game):
    assert said(m.group(1), m.group(2)), f"{m.group(1)} says a line with no clip: {m.group(2)[:60]}"
for t in re.findall(r'\bS\("([^"]+)"\)', game):
    assert t in texts, f"a spoken part with no clip: {t[:60]}"
for t in re.findall(r'T\(G\.trust\[c\] < 20 \? "([^"]+)" : "([^"]+)"\)', game)[0] + ("Fine. I vote for yours, you vote for mine. Lola is our witness, and the Book is our memory.",):
    assert all(said(c, t) for c in ("marisol", "tobias", "baako", "hana")), t
for t in re.findall(r'"([^"]+)"', re.search(r"const LIES = \{([^}]*)\}", game).group(1)):
    assert said("rico", t + "!"), f"Rico cannot call out the rumour {t!r}"
emb = re.search(r"const EMB = \{(.*?)\n  \};", game, re.S).group(1)
for who, name, coins in re.findall(r'who: "(\w+)", name: "([^"]+)", wants: "\w+", coins: (\d+)', emb):
    assert said("rico", f"Marisol took {coins} coins from the {name}!"), name
    assert any(w == who and t.startswith(f"{coins} coins, today.") for w, t in ls), who

# voices.json is what rico.js all() builds in the browser
node = shutil.which("node")
if node:
    subprocess.run([node, os.path.join(make.REPO, "tests", "voices.mjs")], check=True, capture_output=True)
print("ok")

# design and keep, against a stand-in for ElevenLabs
calls = []
def fake(path, body=None, accept="application/json", missing_ok=False):
    calls.append(path)
    if path == "/text-to-voice/design":
        assert 100 <= len(body["text"]) <= 1000 and 20 <= len(body["voice_description"]) <= 1000
        return json.dumps({"previews": [{"audio_base_64": base64.b64encode(b"mp3-%d" % i).decode(), "generated_voice_id": f"g{i}"} for i in range(3)]}).encode()
    if path == "/text-to-voice":
        return json.dumps({"voice_id": "v-" + body["voice_name"].split()[0].lower() + body["generated_voice_id"]}).encode()
    if path.startswith("/shared-voices"):
        assert "gender=male" in path
        return json.dumps({"voices": [{"public_owner_id": "o", "voice_id": f"v-lib{i}", "name": f"Lib {i}", "preview_url": "https://x/p.mp3"} for i in range(3)]}).encode()
    if path.startswith("/text-to-speech/v-"):
        return b"clip"
    raise AssertionError(path)
make.call = fake
with tempfile.TemporaryDirectory() as out:
    json.dump({"voice": "v-old", "name": "Rico", "clips": ["abc"]}, open(os.path.join(out, "index.json"), "w"))   # the first index
    make.cmd_design(types.SimpleNamespace(out=out, who="all", description=None))
    assert open(os.path.join(out, "samples", "design-lola-2.mp3"), "rb").read() == b"mp3-1"
    page = open(os.path.join(out, "samples", "index.html")).read()
    assert "lola=3" in page and "Ambassador Frost" in page
    make.cmd_keep(types.SimpleNamespace(out=out, picks=["rico=2", "lola=1"]))
    idx = json.load(open(os.path.join(out, "index.json")))
    assert idx["voices"]["rico"]["id"] == "v-ricog1" and idx["voices"]["lola"]["id"] == "v-lolag0"
    assert len(idx["clips"]) == sum(1 for w, t in ls if w in ("rico", "lola")) and "abc" not in idx["clips"]
    n = len(calls)
    make.cmd_make(types.SimpleNamespace(out=out, voice=None))
    assert len(calls) == n, "made a clip twice"
    make.cmd_library(types.SimpleNamespace(out=out, who="rico", search=None))
    assert "rico=L3" in open(os.path.join(out, "samples", "library.html")).read()
    make.cmd_keep(types.SimpleNamespace(out=out, picks=["rico=L2"]))
    idx = json.load(open(os.path.join(out, "index.json")))
    assert idx["voices"]["rico"]["id"] == "v-lib1" and not any(c.startswith("/voices/add") for c in calls)
print("design ok")
