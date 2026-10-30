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
