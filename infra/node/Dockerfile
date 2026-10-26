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

ARG TAU_TESTNET_REF=99a9e928d4aa67718cda2c4214c5da4de3c3a58c

FROM python:3.14-trixie AS tau-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG TAU_LANG_REPO=https://github.com/IDNI/tau-lang.git
ARG TAU_LANG_REF=c3ea334cd1e6612930ea9f404933211858f0009f
ARG TAU_BUILD_JOBS=2

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash bison build-essential ca-certificates clang cmake curl git \
    libboost-all-dev libcurl4-openssl-dev libgmp-dev lld ninja-build \
    pkg-config unzip wget \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/tau-build-venv
ENV PATH=/opt/tau-build-venv/bin:$PATH \
    TAU_PYTHON=/opt/tau-build-venv/bin/python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir nanobind

WORKDIR /app
RUN set -eux; \
    git clone --filter=blob:none "${TAU_LANG_REPO}" tau-lang; \
    cd tau-lang; \
    git checkout "${TAU_LANG_REF}"; \
    git submodule update --init --recursive

WORKDIR /app/tau-lang
RUN set -eux; \
    ./dev build Release \
      -DTAU_BUILD_JOBS="${TAU_BUILD_JOBS}" \
      -DTAU_BUILD_EXECUTABLE=ON \
      -DTAU_BUILD_BINDING_PYTHON_NANOBIND=ON \
      -DPython_EXECUTABLE=/opt/tau-build-venv/bin/python \
      -DTAU_BUILD_TESTS=OFF; \
    find /app/tau-lang/build* -name 'tau*.so' -path '*nanobind*' | grep -q .


FROM python:3.14-trixie AS testnet-src
ARG TAU_TESTNET_REF
RUN git clone --filter=blob:none https://github.com/IDNI/tau-testnet.git /src && \
    git -C /src checkout "${TAU_TESTNET_REF}" && rm -rf /src/.git


FROM python:3.14-slim-trixie AS runtime

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

COPY --from=testnet-src /src /app/tau-testnet
COPY --from=testnet-src /src/docker/entrypoint.sh /usr/local/bin/tau-node-entrypoint
COPY --from=tau-builder /app/tau-lang /app/tau-lang
COPY --from=tau-builder /root/.tau /root/.tau

# Register every shared-library directory of the built dependencies (cvc5,
# Boost, Spot) with the dynamic linker, whatever layout the dependency store uses.
RUN chmod +x /usr/local/bin/tau-node-entrypoint && mkdir -p /data && \
    find /root/.tau /app/tau-lang -name '*.so*' -type f -printf '%h\n' | sort -u > /etc/ld.so.conf.d/tau.conf && \
    ldconfig

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
