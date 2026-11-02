"""Does the alerts image hold every module the service imports? (No network, no docker: reads the Dockerfile.)
On 31 October 2026 a new module (firsts.py) was imported but not copied into the image, and the service died on its
first import for two days without a post or a failure in any channel.

Run: python test_image.py
"""
import glob
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
docker = open(os.path.join(here, "Dockerfile")).read()
copied = set()
for line in docker.splitlines():
    if line.startswith("COPY "):
        for pat in line.split()[1:-1]:
            copied |= {os.path.basename(f) for f in glob.glob(os.path.join(here, pat))}
missing = []
for f in sorted(glob.glob(os.path.join(here, "*.py"))):
    if os.path.basename(f).startswith("test_"):
        continue
    for m in re.findall(r"^(?:import|from) ([a-z_]+)", open(f).read(), re.M):
        if os.path.exists(os.path.join(here, m + ".py")) and m + ".py" not in copied:
            missing.append(f"{os.path.basename(f)} imports {m}.py, which the Dockerfile does not copy")
for m in sorted(set(missing)):
    print("FAIL " + m)
print("ok   every module the services import is in the image" if not missing else "FAILED")
sys.exit(1 if missing else 0)
