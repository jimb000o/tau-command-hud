# TAU//NET Command HUD

**Unofficial community project.** Not affiliated with, endorsed by or maintained by IDNI or the Tau team.

A Jarvis-style live view of the [Tau Testnet Alpha](https://github.com/IDNI/tau-testnet): every block checked by Tau logic, rule changes that activate only when validators agree, rules that accounts write and share with each other, and the composite user policy the node builds from them.

**Open it:** https://tauhud.com (mirror: https://jimb000o.github.io/tau-command-hud/)

## Modes

- **Simulation** (default): runs in your browser and follows the documented protocol. It is not the real chain.
- **Live node**: connects to your own Tau node over WebSocket (`ws://localhost:65433`). The public testnet only exposes P2P, so run a read node first (see the tau-testnet README, "Join the Tau Testnet") and allow this page's origin:

```bash
docker run --rm -it -p 127.0.0.1:65432:65432 -p 127.0.0.1:65433:65433 -p 4001:4001 \
  -v tau_data:/data \
  -e TAU_NETWORK_ID=tau-testnet-v2 \
  -e TAU_BOOTSTRAP_PEERS='[{"peer_id":"12D3KooWDpWEYxBy8y84AssrPSLaq9DxC7Lncmn5wERJnAWZFnYC","addrs":["/ip4/34.251.82.246/tcp/4001"]}]' \
  -e TAU_MINING_ENABLED=false \
  -e TAU_WS_ALLOWED_ORIGINS=https://tauhud.com,https://jimb000o.github.io \
  tau-testnet-standalone \
  bash -c 'mkdir -p data && cp networks/tau-testnet-v2/genesis.json data/genesis.json && python server.py'
```

## Support

If this is useful to you, AGRS or ETH donations are welcome at `0x23fB76A33A8d70f5c51aB558b85e4b93040003eb`.

## Feedback

Use the **Feedback** button on the page or [open an issue](../../issues/new?template=feedback.yml). Ideas with the most 👍 get built first.

## Development

One static file, `index.html`, no build step. GitHub Pages serves it from the `main` branch root.
