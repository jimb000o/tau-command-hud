# syntax=docker/dockerfile:1.7
#
# Tau testnet read node, adapted from IDNI/tau-testnet Dockerfile.standalone.
#
# Why not the upstream file as is: at the tau-lang commit it pins, the explicit
# `./dev dep-cvc5` / `./dev dep-boost` prefetch steps abort with "no compiler;
# pass -DTAU_DEP_CC and -DTAU_DEP_CXX". tau-lang's own docs say configure runs
# those dependency producers itself (with clang), so this file drops the
# prefetch and lets `./dev build Release` resolve cvc5, Boost and Spot. Works on
# x86_64 and arm64 (tau-lang ships linux-arm64 recipes; Spot is built from
# source there).

ARG TAU_TESTNET_REF=b1ebfa479dafe8f64ad741f1f101f2319db5eae4

# Base images pinned by digest: a re-published tag (python:3.14-trixie was
# rebuilt on Docker Hub 2026-10-27 02:13Z) invalidates the whole tau-builder
# stage, i.e. a ~90-minute tau-lang rebuild on the server. Bump deliberately.
# Both digests are the multi-arch manifest lists for 3.14-trixie as of 2026-10-27.
FROM python:3.14-trixie@sha256:99a53439c9ffbd44b13fe09e60f21b2573e852e342513deaf525ad138d3b404f AS tau-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG TAU_LANG_REPO=https://github.com/IDNI/tau-lang.git
ARG TAU_LANG_REF=c3ea334cd1e6612930ea9f404933211858f0009f
ARG TAU_BUILD_JOBS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash bison build-essential ca-certificates ccache clang cmake curl git \
    libboost-all-dev libcurl4-openssl-dev libgmp-dev lld ninja-build \
    patchelf pkg-config unzip wget \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/tau-build-venv
ENV PATH=/opt/tau-build-venv/bin:$PATH \
    TAU_PYTHON=/opt/tau-build-venv/bin/python
# auditwheel: the binding's configure refuses to run unless some interpreter
# has it (bindings/python/nanobind/CMakeLists.txt), although the wheel target
# that would use it is never built here.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir nanobind auditwheel && \
    python -m auditwheel --version

WORKDIR /app
RUN set -eux; \
    git clone --filter=blob:none "${TAU_LANG_REPO}" tau-lang; \
    cd tau-lang; \
    git checkout "${TAU_LANG_REF}"; \
    git submodule update --init --recursive

WORKDIR /app/tau-lang
# The binding defaults to Python 3.12 (TAU_PYTHON_VERSION in
# bindings/python/nanobind/CMakeLists.txt); tau-testnet needs 3.14, so the
# version is passed explicitly, as the tau-testnet README does.
#
# The node uses tau only through the Python module (tau_native), so the tau
# executable and its REPL are left out: one fewer multi-GB link on a 4 GB box.
# One job by default: a single tau translation unit can take over 3 GB; two in
# parallel froze a 2 vCPU / 4 GB server even with swap.
#
# The dependency store (/root/.tau: cvc5, Boost, Spot) takes most of the build
# hour. It lives in a BuildKit cache mount so a failure later in this step, or
# a change to the tau-lang ref, never recompiles it; a copy is taken at the end
# for the runtime image, since cache mounts are not part of the layer.
RUN --mount=type=cache,target=/root/.tau,id=tau-store \
    --mount=type=cache,target=/root/.ccache,id=tau-ccache \
    set -eux; \
    ./dev build Release \
      -DTAU_BUILD_JOBS="${TAU_BUILD_JOBS}" \
      -DTAU_BUILD_EXECUTABLE=OFF \
      -DTAU_BUILD_BINDING_PYTHON_NANOBIND=ON \
      -DTAU_PYTHON_VERSION=3.14 \
      -DPython_EXECUTABLE=/opt/tau-build-venv/bin/python \
      -DCMAKE_C_COMPILER_LAUNCHER=ccache \
      -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
      -DTAU_BUILD_TESTS=OFF; \
    find /app/tau-lang/build* -name 'tau*.so' -path '*nanobind*' | grep -q .; \
    rm -rf /tau-store; cp -a /root/.tau /tau-store


FROM python:3.14-trixie@sha256:99a53439c9ffbd44b13fe09e60f21b2573e852e342513deaf525ad138d3b404f AS testnet-src
ARG TAU_TESTNET_REF
RUN git clone --filter=blob:none https://github.com/IDNI/tau-testnet.git /src && \
    git -C /src checkout "${TAU_TESTNET_REF}" && rm -rf /src/.git
# Local fixes to the pinned sources; each script explains itself and fails the
# build if the source no longer matches.
COPY patches/ /patches/
RUN python3 -I /patches/read-until-eof.py /src
RUN python3 -I /patches/sync-paginate.py /src
RUN python3 -I /patches/sync-diagnostics.py /src
RUN python3 -I /patches/network-tip.py /src
RUN python3 -I /patches/peer-addrs.py /src
RUN python3 -I /patches/chain-reset.py /src
RUN python3 -I /patches/validator-gate.py /src
RUN python3 -I /patches/peer-book.py /src
RUN python3 -I /patches/bootstrap-redial.py /src


FROM python:3.14-slim-trixie@sha256:82abc9f53600280b0757126f83c5a7d47088592d2acb6b4c0b9e97f76865508c AS runtime

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash build-essential ca-certificates libboost-all-dev libcurl4 libffi-dev \
    libgmp-dev libsodium-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app/tau-testnet
COPY --from=testnet-src /src/requirements.txt /app/tau-testnet/requirements.txt
COPY --from=testnet-src /src/scripts/install_coincurve.sh /tmp/install_coincurve.sh
RUN --mount=type=cache,target=/root/.cache/coincurve-wheels \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    COINCURVE_WHEEL_DIR=/root/.cache/coincurve-wheels sh /tmp/install_coincurve.sh && rm /tmp/install_coincurve.sh && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir nanobind

# The built tau-lang and its dependency store are several GB and change only
# when tau-lang is rebuilt; they come BEFORE the node sources so that a node
# patch does not create a fresh multi-GB layer per rebuild (the server's 40 GB
# disk filled up with such copies on 2026-10-27).
COPY --from=tau-builder /app/tau-lang /app/tau-lang
COPY --from=tau-builder /tau-store /root/.tau
# Register every shared-library directory of the built dependencies (cvc5,
# Boost, Spot) with the dynamic linker, whatever layout the dependency store uses.
RUN find /root/.tau /app/tau-lang -name '*.so*' -type f -printf '%h\n' | sort -u > /etc/ld.so.conf.d/tau.conf && \
    ldconfig

COPY --from=testnet-src /src /app/tau-testnet
COPY --from=testnet-src /src/docker/entrypoint.sh /usr/local/bin/tau-node-entrypoint
COPY start.sh /usr/local/bin/tau-node-start
COPY validator-key.py /usr/local/bin/tau-validator-key
RUN chmod +x /usr/local/bin/tau-node-entrypoint /usr/local/bin/tau-node-start /usr/local/bin/tau-validator-key && mkdir -p /data

ENV PYTHONUNBUFFERED=1 \
    TAU_FORCE_TEST=0 \
    TAU_ENV=development \
    TAU_HOST=0.0.0.0 \
    TAU_PORT=65432 \
    TAU_NETWORK_LISTEN=/ip4/0.0.0.0/tcp/4001 \
    TAU_BOOTSTRAP_PEERS=[] \
    TAU_PROGRAM_FILE=/app/tau-testnet/genesis.tau \
    TAU_DB_PATH=/data/node.db \
    TAU_DATA_DIR=/data \
    TAU_IDENTITY_KEY_PATH=/data/identity.key \
    TAU_MINING_ENABLED=false \
    TAU_MINER_PRIVKEY_PATH=/data/test_miner.key \
    TAU_MINER_PUBKEY_PATH=/data/test_miner.pub

# Fail the build, not the node, if the native Tau module cannot load.
RUN python -c "import tau_native; tau_native.load_tau_module()"

EXPOSE 65432 65433 4001
VOLUME ["/data"]
ENTRYPOINT ["/usr/local/bin/tau-node-entrypoint"]
CMD ["python", "server.py"]
