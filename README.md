# OpenMAIC single-user Tencent VPS deployment

This deployment is pinned to OpenMAIC v1.0.3, commit
`e693e11a81644f84c258df73dbda378643520a62`. It is designed to run beside
the finance website on `43.162.115.148` without changing that site's Caddy
configuration or port `8765`.

## Build

Run `.github/workflows/build-openmaic.yml` in this repository. The workflow
builds on GitHub Actions and publishes
`ghcr.io/<GitHub-owner>/openmaic:v1.0.3`. Make the package publicly readable,
then record its immutable `sha256` digest. No LLM key is used at build time.

## Server installation

1. Run `server/preflight.sh` and confirm the existing finance backup is healthy.
2. Install Docker Engine and Compose from Docker's official Ubuntu repository,
   and install Tailscale from its official Ubuntu package repository. Do not
   modify the finance Caddyfile or open any new public inbound port.
3. Place `compose.yml` and `server/` under `/opt/openmaic`, owned by root.
   Run `sudo /opt/openmaic/server/configure-env.py` once. It reads only the
   existing finance model settings and creates `/opt/openmaic/.env` as root-only
   mode `0600`; it does not print or change the finance key. The resulting
   configuration contains:

   ```dotenv
   OPENMAIC_IMAGE=
   POSTGRES_PASSWORD=<random-hex-password>
   DATABASE_URL=postgres://openmaic:<same-password>@postgres:5432/openmaic
   PERSISTENCE_DEV_TOKEN=openmaic-tailnet-single-user-v1
   PERSISTENCE_ALLOW_INSECURE_DEV_AUTH=true
   OPENMAIC_AGENT_RUNTIME_ENABLED=true
   ACCESS_CODE=<long-random-code>
   DEEPSEEK_API_KEY=<copied from finance.env without changing finance.env>
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   DEEPSEEK_MODELS=deepseek-chat
   DEFAULT_MODEL=deepseek:deepseek-chat
   ```

   Set the image with `sudo /opt/openmaic/server/set-image.py
   ghcr.io/iamgalaxyzheng-pixel/openmaic@sha256:<verified-digest>` after the
   GitHub build. The development persistence token is deliberately present in
   browser code.
   **Tailscale is the access boundary**. Do not expose port `3001` or `8443`
   publicly. Only this single-user, private-tailnet deployment may use the
   development authenticator.
4. Run `docker compose -f compose.yml config --quiet`, then
   `docker compose -f compose.yml up -d`. Confirm both containers are healthy,
   the app listens only on `127.0.0.1:3001`, and the finance site still works.
5. Join the VPS and personal devices to the same Tailscale tailnet. Enable
   MagicDNS and HTTPS certificates, then run
   `tailscale serve --bg --https=8443 http://127.0.0.1:3001` on the VPS.
   Verify the returned private `*.ts.net:8443` URL from a connected device.
6. Install `server/openmaic-backup.service` and `.timer` to `/etc/systemd/system/`,
   run a first backup, inspect its archive, and enable the timer. Keep these
   backups separate from finance backups.

## Acceptance and rollback

Verify finance HTTPS, login, and existing health baseline before and after
startup. A pre-existing Yahoo Finance source alert can keep `/api/pulse` at
503; no new alerts or deterioration are acceptable. Test OpenMAIC access code,
a small classroom generation, saved course reload, and a restart. Confirm it is
unreachable without Tailscale. Watch memory, swap, CPU, container restarts, and
finance response times during the test. If the app exceeds its fixed limits or
finance regresses, run `tailscale serve --https=8443 off` and
`docker compose -f /opt/openmaic/compose.yml down` immediately. Do not remove
the volumes. Never raise the limits on this VPS merely to make OpenMAIC pass.
