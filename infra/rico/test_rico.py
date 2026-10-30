"""Rico's voice: the server reads the same lines from rabbit/rico.js that the game speaks, and names the clips the same way."""
import os
import re
import shutil
import subprocess
import json

import make

src = open(make.RICO_JS, encoding="utf-8").read()
ls = make.lines(src)
assert len(ls) == len(set(ls)), "a line twice"
assert "Pact news: Hana and Baako shook hands at La Ola. Lola counted the fingers afterwards." in ls
assert "Day 3 of 5. If you still don't know who to vote for, neither do the gulls." in ls
assert not any("{" in t for t in ls), "a placeholder left in a spoken line"
assert not any(re.search(r"\d{2,}", t) for t in ls), "a number in a spoken line"
assert make.key("Chain weather.") == __import__("hashlib").sha1(b"Chain weather.").hexdigest()[:16]
print(f"{len(ls)} lines, {sum(map(len, ls))} characters")

# every line the game asks for exists in rico.js
game = open(os.path.join(make.REPO, "rabbit", "game.js"), encoding="utf-8").read()
keys = set(re.findall(r'^\s*(\w+): "', re.search(r"const L = \{(.*?)\n  \};", src, re.S).group(1), re.M))
for k in re.findall(r'\bV\("(\w+)"', game):
    assert k in keys, f"game.js speaks {k}, which rico.js does not have"
for k in re.findall(r'V\(sim \? "(\w+)" : "(\w+)"\)', game)[0]:
    assert k in keys, k

# the browser builds the same list (rico.js all())
node = shutil.which("node")
if node:
    js = subprocess.run([node, "-e", "global.window={};global.fetch=()=>Promise.reject();" + src + ";console.log(JSON.stringify(window.RICO.all()))"],
                        capture_output=True, text=True, check=True).stdout
    assert json.loads(js) == ls, "rico.js all() and make.py lines() differ"
print("ok")

# design and keep, against a stand-in for ElevenLabs
import base64
import tempfile
import types
calls = []
def fake(path, body=None, accept="application/json", missing_ok=False):
    calls.append(path)
    if path == "/text-to-voice/design":
        return json.dumps({"previews": [{"audio_base_64": base64.b64encode(b"mp3-%d" % i).decode(), "generated_voice_id": f"g{i}"} for i in range(3)]}).encode()
    if path == "/text-to-voice":
        assert body["generated_voice_id"] == "g1" and body["voice_name"] == "Rico"
        return json.dumps({"voice_id": "v-rico"}).encode()
    if path == "/voices":
        return json.dumps({"voices": [{"voice_id": "v-rico", "name": "Rico"}]}).encode()
    if path.startswith("/text-to-speech/v-rico"):
        return b"clip"
    raise AssertionError(path)
make.call = fake
with tempfile.TemporaryDirectory() as out:
    make.cmd_design(types.SimpleNamespace(out=out, description=make.DESIGN))
    assert open(os.path.join(out, "samples", "design-2.mp3"), "rb").read() == b"mp3-1"
    assert "keep 3" in open(os.path.join(out, "samples", "index.html")).read()
    make.cmd_keep(types.SimpleNamespace(out=out, n=2, name="Rico"))
    idx = json.load(open(os.path.join(out, "index.json")))
    assert idx["voice"] == "v-rico" and len(idx["clips"]) == len(ls)
print("design ok")
