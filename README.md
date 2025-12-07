# Nawala Checker K39

A tiny reboot of the [Skiddle-ID/blocklist](https://github.com/Skiddle-ID/blocklist) idea: download Kominfo blocklists from multiple sources, split giant files into manageable chunks, and refresh a README summary so you always know how fresh your data is.

## Highlights
- Downloads each list from a configurable URL or local file
- Splits huge files into `50MB`-ish `prefix_001.txt` chunks so Git and GitHub Releases stay happy
- Keeps a reproducible `README` summary in sync with the on-disk data
- Ships with sample sources so you can test everything without hitting the real Kominfo endpoints

<!-- SUMMARY:START -->
### 🧾 Blocklist Summary (Last Updated: 2025-12-05 02:39:29 UTC)

| List | Entries |
|------|---------|
| Situs Judi (Skiddle Mirror) | 3088629 |
| IP Address ISP (Skiddle Mirror) | 100293 |
| Situs Judi (TrustPositif Mirror) | 1583074 |
| TrustPositif Gambling (Full) | 3088629 |
| TrustPositif Gambling 001 | 1000000 |
| TrustPositif Gambling 002 | 1000000 |
| TrustPositif Gambling 003 | 1000000 |
| TrustPositif Gambling 004 | 88555 |
| TrustPositif Gambling (Only Domains) | 204099 |
| TrustPositif Gambling + Porn | 0 |
| TrustPositif Gambling v2 | 1768857 |
| TrustPositif Gambling Source | 0 |
| Komkom Domain Chunk 00 | 2500000 |
| Komkom Domain Chunk 01 | 2500000 |
| Komkom Domain Chunk 02 | 2500000 |
| Komkom Domain Chunk 03 | 666566 |
| Komkom IP Chunk 00 | 100288 |
| Kominfo Official Domains (placeholder) | 0 |

<!-- SUMMARY:END -->

## Getting started
1. Ensure Python 3.10+ is installed.
2. Adjust `config/blocklist.config.json` so every source points to a reachable `url` or local `path`.
3. Run the updater:

```bash
python3 scripts/update_blocklist.py
```

New/updated files land in the `data/` directory and the table above refreshes automatically.

## Configuration
`config/blocklist.config.json` controls everything:

```json
{
  "output_directory": "data",
  "chunk_size_mb": 50,
  "readme_path": "README.md",
  "sources": [
    {
      "name": "domains",
      "display_name": "Domains",
      "path": "sample_sources/domains.txt",
      "output_prefix": "domains"
    }
  ]
}
```

Key fields:
- `output_prefix`: base filename (`domains`, `ipaddress_isp`, etc.) used for generated chunks.
- `url` or `path`: where the raw file comes from. Use `url` for the Kominfo endpoints and keep `path` for local testing.
- `chunk_size_mb`: override globally with `--chunk-size` or per-file by tweaking the config.

### Mirror config
Need real data instead of the sample fixtures? Point the updater at the GitHub mirrors instead (Skiddle, TrustPositif, and the Komkom chunks from lepasid):

```bash
python3 scripts/update_blocklist.py --config config/blocklist.mirrors.json
```

This pulls `situs_judi` and `ipaddress_isp` straight from the latest [Skiddle-ID/blocklist](https://github.com/Skiddle-ID/blocklist) release, the various gambling datasets from [alsyundawy/TrustPositif](https://github.com/alsyundawy/TrustPositif), and the chunked domain/IP mirrors from [lepasid/komkomkomkom](https://github.com/lepasid/komkomkomkom), writing everything into `data/mirrors/`.

## Automating the updates
Hook `python3 scripts/update_blocklist.py` into cron, a systemd timer, or a GitHub Action similar to the upstream project. The script exits with a non-zero status when configuration problems occur, which lets CI fail fast.

## Sample data
The `sample_sources/` folder contains tiny placeholder lists so you can verify the workflow without touching the real service. Swap them out for the production sources once you're ready.

## Operating straight from mirrors
SQLite is optional. If you prefer to keep things lightweight you can let your bot, Telegram worker, or API read the chunked mirror files directly:

1. Pull the mirrors on a schedule:
   ```bash
   python3 scripts/update_blocklist.py --config config/blocklist.mirrors.json
   ```
2. Point your tooling to `data/mirrors/*.txt`. Each file contains plain newline-delimited domains/IPs that can be grepped, diffed, or streamed.
3. Only run `scripts/build_blocklist_db.py` when you need sub-second lookups or FastAPI/Telegram bots powered by SQL indexes. A full build can take a few minutes because it deduplicates and indexes ~10M rows.

Example brute-force check without SQLite:

```bash
rg -Fxf <(printf 'example.com\n1.2.3.4\n') data/mirrors --stats
```

## Dashboard prototype
The `dashboard/` folder hosts a Vite + React + Tailwind prototype for the Trust+ control center UI. To run it locally:

```bash
cd dashboard
npm install
npm run dev
```

Build artifacts land in `dashboard/dist/` via `npm run build`. The mock data shown inside the dashboard mirrors the statistics produced by the updater so you can wire the UI to the API layer later on.

Environment variables:
- `VITE_API_URL` – optional base URL for the FastAPI service. Defaults to `http://127.0.0.1:8000`, so `VITE_API_URL=https://your-api.example.com npm run dev` will immediately hydrate the KPIs and tables.

## Persisting & querying the data
After pulling the mirrors you can build a SQLite database that powers an API/bot:

```bash
python3 scripts/build_blocklist_db.py --mirror-dir data/mirrors --output data/blocklist.db
uvicorn api.main:app --reload
```

Endpoints:
- `GET /health` – simple status check.
- `GET /stats` – counts per source/type.
- `GET /check?q=example.com&q=1.2.3.4` – lookup multiple domain/IP entries.
- `POST /check` with `{ "items": ["a.com", "1.2.3.4"] }` – same as above.

Auth & throttling:
- Set `API_KEY` to require `X-API-Key` on `/check`.
- Set `RATE_LIMIT` (requests/minute/client) to enable rate limiting; 0 or unset disables it.

## Kominfo direct access (placeholder)
`config/blocklist.mirrors.json` includes a disabled entry (`kominfo_domains`) that targets `https://trustpositif.komdigi.go.id/assets/db/domains`. Keep it disabled in Git, then hydrate it at runtime with secrets pulled from your WireGuard session/CSRF/recaptcha tokens:

```bash
export KOMINFO_CSRF_TOKEN=...
export KOMINFO_RECAPTCHA_TOKEN=...
jq '
  .sources[] |=
    (if .name == "kominfo_domains" then
       .headers["X-CSRF-TOKEN"] = env.KOMINFO_CSRF_TOKEN |
       .headers["X-RECAPTCHA-TOKEN"] = env.KOMINFO_RECAPTCHA_TOKEN |
       .enabled = true
     else . end)
' config/blocklist.mirrors.json > /tmp/kominfo.config.json
python3 scripts/update_blocklist.py --config /tmp/kominfo.config.json
```

No credentials live in the repo, yet the updater can ingest the official feed whenever the tokens are available.

## Packaging & releases
Need a distributable tarball for GitHub Releases or Telegram dropboxes? Run:

```bash
python3 scripts/update_blocklist.py --config config/blocklist.mirrors.json
scripts/package_release.sh            # optional timestamp argument
```

Artifacts are written to `dist/releases/blocklist-<timestamp>.tar.gz` and contain the refreshed mirrors plus both config files. The GitHub Action can later be extended to invoke the same script and attach the archive to a release instead of (or in addition to) uploading it as a workflow artifact.

## Automation
A GitHub Action (`.github/workflows/mirror-update.yml`) runs `python3 scripts/update_blocklist.py --config config/blocklist.mirrors.json` every 6 hours (and on manual trigger) then uploads a tarball artifact containing the refreshed mirrors/config. Hook additional steps (commit/push, release uploads, notifications) as needed by adding secrets/tokens.
