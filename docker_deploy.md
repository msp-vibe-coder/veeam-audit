# Docker Deployment Guide

> Portable guide for deploying a containerized app on the shared server.
> Drop this file into any project repo as a reference.

---

## Server Overview

| Detail     | Value                                 |
|------------|---------------------------------------|
| Hostname   | `PTSCORPVS0WAPP01`                   |
| IP address | `10.69.69.10`                         |
| DNS name   | `ptswebapps`                          |
| OS         | Ubuntu 24.04 LTS                      |
| Docker     | 29.2.1 (Compose v5.0.2 plugin)       |
| Proxy      | Traefik (latest), ports 80 (HTTP→HTTPS redirect) / 443 (HTTPS) |
| Dashboard  | `http://10.69.69.10:8080`            |
| SSH user   | `wapp01admin` (key-based auth, passwordless sudo) |

All web apps run as Docker containers on a shared `traefik-net` bridge network. Traefik reverse-proxies HTTP requests to each container based on `PathPrefix` routing rules defined as Docker labels.

---

## Connecting to the Server

Any project can manage its own Docker containers on the server over SSH. This section covers connection setup and common patterns.

### SSH connection

```bash
ssh wapp01admin@10.69.69.10
```

- **Auth:** Key-based (ed25519). The local key at `~/.ssh/id_ed25519` is authorized on the server. No password needed.
- **Sudo:** Passwordless via `/etc/sudoers.d/wapp01admin`. Not needed for Docker commands (`wapp01admin` is in the `docker` group).

### Running remote commands

Run a single command without opening an interactive session:

```bash
ssh wapp01admin@10.69.69.10 "docker ps"
```

Chain commands with `&&`:

```bash
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && docker compose restart"
```

### Copying files to/from the server

```bash
# Local → server
scp ./my-file.txt wapp01admin@10.69.69.10:/home/wapp01admin/apps/my-app/

# Server → local
scp wapp01admin@10.69.69.10:/home/wapp01admin/apps/my-app/some-file.txt ./
```

### Reading command output (stdout workaround)

Some tools (including Claude Code's Bash tool) don't capture stdout from SSH commands — the command succeeds but the output is silently dropped. Write-only commands (`mkdir`, `docker compose up -d`, file writes) work fine since they have no meaningful output.

**Workaround:** Redirect output to a file on the server, then `scp` it back:

```bash
# 1. Run the command, redirect output to a temp file
ssh wapp01admin@10.69.69.10 "docker ps --filter name=my-app > /tmp/result.txt 2>&1"

# 2. Copy the file locally
scp wapp01admin@10.69.69.10:/tmp/result.txt ./result.txt

# 3. Read result.txt locally, then clean up
```

### Common Docker operations

All apps live under `/home/wapp01admin/apps/<name>/` on the server.

```bash
# Rebuild and restart your app's containers
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && docker compose up -d --build"

# Restart without rebuilding
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && docker compose restart"

# View logs
ssh wapp01admin@10.69.69.10 "docker logs my-app --tail 50 > /tmp/logs.txt 2>&1"
scp wapp01admin@10.69.69.10:/tmp/logs.txt ./logs.txt

# Stop your app
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && docker compose down"

# Pull latest code and redeploy
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && git pull"
scp ./docker-compose.yml wapp01admin@10.69.69.10:/home/wapp01admin/apps/my-app/docker-compose.yml
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && docker compose up -d --build"

# Background build (for long builds that may time out SSH)
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/my-app && nohup docker compose up -d --build > /tmp/build.log 2>&1 &"
```

### Using from another project's CLAUDE.md

To let Claude Code manage your app's container from your own project repo, add this to your project's `CLAUDE.md`:

```markdown
## Server Deployment

This app runs as a Docker container on `10.69.69.10` (ptswebapps).

- **SSH:** `ssh wapp01admin@10.69.69.10` (key-based auth, no password)
- **App directory:** `/home/wapp01admin/apps/<name>/`
- **Container name:** `<name>`
- **Rebuild:** `ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/<name> && docker compose up -d --build"`
- **Logs:** Redirect to temp file and scp back (stdout is not captured over SSH)
```

Replace `<name>` with your app's directory name (e.g., `sow-builder`, `veeam-audit`).

---

## What Your App Needs

### 1. A Dockerfile

Your repo must contain a `Dockerfile` at the root. Any base image works — Node, Python, Go, nginx, etc. The container must listen on a single HTTP port (typically 3000).

### 2. A unique path prefix

Every app gets a unique URL path like `/my-app`. All requests to `https://ptswebapps/my-app/...` are routed to your container by Traefik.

### 3. A docker-compose.yml with Traefik labels

This is provided by the management repo (see [Registration](#registration-in-web-app-server-management) below), but you should understand what it does.

---

## Routing Patterns

There are two ways to handle the path prefix. Choose the one that matches your app.

### Pattern A: StripPrefix (app is unaware of the prefix)

Use this when the app serves content at `/` and has no built-in concept of a sub-path. Traefik strips the prefix before forwarding, so the app sees `/` instead of `/my-app/`.

**When to use:** Static sites, simple file servers, apps with no sub-path configuration (e.g., a `next export` served by `serve`, a plain nginx site, a Flask app without `APPLICATION_ROOT`).

**Real example — cipp-standards** (static Next.js export served by `serve`):

```yaml
services:
  cipp-standards:
    build: .
    container_name: cipp-standards
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cipp-standards.rule=PathPrefix(`/cipp-standards`)"
      - "traefik.http.routers.cipp-standards.entrypoints=websecure"
      - "traefik.http.routers.cipp-standards.tls=true"
      - "traefik.http.middlewares.cipp-standards-strip.stripprefix.prefixes=/cipp-standards"
      - "traefik.http.routers.cipp-standards.middlewares=cipp-standards-strip"
      - "traefik.http.services.cipp-standards.loadbalancer.server.port=3000"
    networks:
      - traefik-net

networks:
  traefik-net:
    external: true
```

**How it works:**
1. Browser requests `https://ptswebapps/cipp-standards/page`
2. Traefik matches `PathPrefix(/cipp-standards)`
3. StripPrefix middleware removes `/cipp-standards` → forwards `/page` to the container
4. The container's file server responds to `/page`

**Important:** Even with StripPrefix, if your app generates HTML with asset links, those links must include the prefix so the browser requests the correct URL. For Next.js static exports, set `basePath: "/cipp-standards"` in `next.config.ts` so generated `<link>` and `<script>` tags point to `/cipp-standards/_next/...`.

---

### Pattern B: basePath (app handles the prefix natively)

Use this when the app is built to serve all routes under a configurable sub-path. Traefik forwards the full path including the prefix, and the app expects it.

**When to use:** Server-rendered Next.js (`next start` with `basePath`), Express apps with a router prefix, Django with `FORCE_SCRIPT_NAME`, etc.

**Real example — sow-builder** (server-rendered Next.js with `basePath`):

`next.config.ts` in the app repo:
```ts
const nextConfig: NextConfig = {
  basePath: "/sow-builder",
  // ...
};
```

`docker-compose.yml`:
```yaml
services:
  sow-builder:
    build: .
    container_name: sow-builder
    restart: unless-stopped
    volumes:
      - sow-data:/app/data
    env_file:
      - .env.docker
    environment:
      NODE_ENV: production
      DATABASE_URL: file:/app/data/production.db
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.sow-builder.rule=PathPrefix(`/sow-builder`)"
      - "traefik.http.routers.sow-builder.entrypoints=websecure"
      - "traefik.http.routers.sow-builder.tls=true"
      - "traefik.http.services.sow-builder.loadbalancer.server.port=3000"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/sow-builder/login"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - traefik-net

networks:
  traefik-net:
    external: true

volumes:
  sow-data:
```

**How it works:**
1. Browser requests `https://ptswebapps/sow-builder/login`
2. Traefik matches `PathPrefix(/sow-builder)` and forwards `/sow-builder/login` to the container
3. Next.js receives `/sow-builder/login` and serves the login page (because `basePath` is set)

**No StripPrefix middleware.** Adding StripPrefix would break the app — Next.js would receive `/login` when it expects `/sow-builder/login`.

---

### Pattern C: Multi-service apps (database + API + frontend)

Use this when your app has multiple containers — e.g., a database, an API backend, and a frontend. Only the user-facing service (frontend) gets Traefik labels. Internal services (db, api) communicate over Docker Compose's default network.

**When to use:** Full-stack apps with a database, backend API, and frontend served by nginx or similar. The frontend proxies API requests to the backend internally.

**Real example — veeam-audit** (PostgreSQL + FastAPI + React/nginx):

```yaml
services:
  db:
    image: postgres:16
    container_name: veeam-audit-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: veeam_audit
      POSTGRES_USER: veeam
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U veeam -d veeam_audit"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./backend
    container_name: veeam-audit-api
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://veeam:${DB_PASSWORD:-changeme}@db:5432/veeam_audit
      REPORTS_DIR: /app/reports
    volumes:
      - reports:/app/reports
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    container_name: veeam-audit
    restart: unless-stopped
    depends_on:
      - api
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.veeam-audit.rule=PathPrefix(`/veeam-audit`)"
      - "traefik.http.routers.veeam-audit.entrypoints=websecure"
      - "traefik.http.routers.veeam-audit.tls=true"
      - "traefik.http.middlewares.veeam-audit-strip.stripprefix.prefixes=/veeam-audit"
      - "traefik.http.routers.veeam-audit.middlewares=veeam-audit-strip"
      - "traefik.http.services.veeam-audit.loadbalancer.server.port=80"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - default
      - traefik-net

networks:
  traefik-net:
    external: true

volumes:
  pgdata:
  reports:
```

**How it works:**
1. Browser requests `https://ptswebapps/veeam-audit/api/v1/dashboard`
2. Traefik matches `PathPrefix(/veeam-audit)`, StripPrefix removes `/veeam-audit` → forwards `/api/v1/dashboard` to the frontend nginx
3. nginx's `location /api/` block proxies to `http://api:8000` (the compose service name `api` resolves on the default network)
4. FastAPI handles `/api/v1/dashboard`

**Key design points:**
- Only the `frontend` service joins `traefik-net`. The `db` and `api` services stay on the default compose network — not exposed to Traefik or other projects.
- Service names (`db`, `api`) are scoped to the project's default network, so they won't conflict with services in other compose projects.
- The nginx `proxy_pass` hostname must match the compose service name (`api`), not the `container_name` (`veeam-audit-api`).
- DB credentials use `${DB_PASSWORD:-changeme}` — create a `.env` file in the project directory on the server with `DB_PASSWORD=<secure-password>`. Docker Compose reads it automatically.

---

## Required Traefik Labels

Every app needs at minimum these five labels (replace `<name>` with your app's identifier and `<path>` with your prefix):

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.<name>.rule=PathPrefix(`<path>`)"
  - "traefik.http.routers.<name>.entrypoints=websecure"
  - "traefik.http.routers.<name>.tls=true"
  - "traefik.http.services.<name>.loadbalancer.server.port=<port>"
```

If using StripPrefix, add two more:

```yaml
  - "traefik.http.middlewares.<name>-strip.stripprefix.prefixes=<path>"
  - "traefik.http.routers.<name>.middlewares=<name>-strip"
```

The `<name>` in labels must be consistent across all labels for the same app. The middleware name (`<name>-strip`) is arbitrary but must match between the middleware definition and the router reference.

All containers must join the external network:

```yaml
networks:
  - traefik-net

# ...at the top level:
networks:
  traefik-net:
    external: true
```

---

## Optional Features

### Volumes (persistent data)

For apps that store data (databases, uploads), use named volumes so data survives container rebuilds:

```yaml
services:
  my-app:
    volumes:
      - my-data:/app/data

volumes:
  my-data:
```

### env_file (secrets and config)

For environment variables that shouldn't be in the image or version control:

```yaml
services:
  my-app:
    env_file:
      - .env.docker
```

Create `.env.docker` on the server at `/home/wapp01admin/apps/<name>/.env.docker`. This file is not part of the git repo — you must `scp` it separately and be aware it can be lost if the app directory is deleted and re-cloned (see [Gotchas](#gotchas--lessons-learned)).

### Health checks

Docker health checks let you monitor container health via `docker ps`:

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:<port><path>/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

If your app uses basePath routing, the health check URL must include the prefix (e.g., `http://localhost:3000/sow-builder/login`, not `http://localhost:3000/login`).

---

## Registration in web-app-server-management

To deploy through the management repo's scripts, register your app:

### 1. Create `apps/<name>/app.conf`

```bash
REPO_URL=https://github.com/msp-vibe-coder/<repo>.git
APP_NAME="My App"
APP_DESCRIPTION="What this app does"
APP_PATH=/my-app        # Unique PathPrefix (must start with /)
APP_PORT=3000           # Port the container listens on
```

### 2. Create `apps/<name>/docker-compose.yml`

Use one of the patterns above. Copy from `apps/example-app/docker-compose.yml` as a starting point.

### 3. Ensure your app repo has the Dockerfile committed

The deploy script clones your repo on the server and runs `docker compose up -d --build`. If the `Dockerfile` is not committed and pushed, the build will fail with `failed to read dockerfile: no such file or directory`.

---

## Deployment

```bash
./scripts/deploy.sh <name>
```

This runs five steps:
1. Checks if the app is already deployed on the server
2. Clones (first deploy) or pulls (redeploy) the app repo
3. Copies `docker-compose.yml` to the server via scp
4. Runs `docker compose up -d --build`
5. Adds the app to the landing page and deploys the updated HTML

### Check status

```bash
./scripts/status.sh
```

Shows all running containers and registered apps.

---

## Verification Checklist

After deploying, verify everything works:

- [ ] `https://ptswebapps/<path>/` loads the app correctly
- [ ] Internal links and assets load (check browser devtools network tab for 404s)
- [ ] If using basePath: `https://ptswebapps/` does NOT serve your app (Traefik routes only matching paths)
- [ ] `docker ps` on the server shows the container as `Up` (and `healthy` if you added a health check)
- [ ] The app appears on the landing page at `https://ptswebapps/`

### Quick verification from the server

```bash
# Test your app responds (replace <path> and <port>)
ssh wapp01admin@10.69.69.10 "curl -o /dev/null -w '%{http_code}' http://localhost:<port><path>/"
```

For basePath apps, verify the prefix is enforced:
```bash
# Should be 404 — root should not serve the app
curl -o /dev/null -w '%{http_code}' http://localhost:3000/
# Should be 200 — correct path serves the app
curl -o /dev/null -w '%{http_code}' http://localhost:3000/sow-builder/login
```

---

## Gotchas & Lessons Learned

### CRLF line endings break shell scripts in containers

**Symptom:** Container fails to start; entrypoint script throws errors like `\r: command not found`.

**Cause:** Files created on Windows are committed with CRLF line endings. When Docker runs them on Linux, the `\r` is treated as part of the command.

**Fix:** Add a `.gitattributes` file to your repo:
```
*.sh text eol=lf
docker-entrypoint.sh text eol=lf
```

**Emergency fix on the server:**
```bash
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/<name> && sed -i 's/\r$//' docker-entrypoint.sh"
```

### next.config.ts must be copied to the runner stage

**Symptom:** Next.js app builds successfully but ignores `basePath` at runtime — pages serve at `/` instead of `/my-app/`.

**Cause:** In a multi-stage Dockerfile, the `runner` stage copies `.next` and `node_modules` but omits `next.config.ts`. Even though `basePath` is compiled into `.next/required-server-files.json`, `next start` reads the config file at startup and falls back to defaults if it's missing.

**Fix:** Add this line to your Dockerfile's runner stage:
```dockerfile
COPY --from=builder /app/next.config.ts ./
```

### .env.docker is not in git — back it up

The deploy script clones the repo from GitHub, so `.env.docker` (which lives only on the server) is not part of the clone. If the app directory is deleted and re-cloned, `.env.docker` is lost.

**Prevention:** Keep a local backup of `.env.docker` (but not in version control if it contains secrets). After a fresh clone, re-upload it:
```bash
scp .env.docker wapp01admin@10.69.69.10:/home/wapp01admin/apps/<name>/.env.docker
```

### deploy.sh scp can conflict with git pull on redeploy

The deploy script copies `docker-compose.yml` into the cloned repo directory. On the next redeploy, `git pull` may fail because `docker-compose.yml` is an untracked file that conflicts with the incoming pull. If the app repo does not have its own `docker-compose.yml`, this is fine. If it does, the scp'd file overwrites the repo's version (which is the intended behavior — the management repo's compose file has the Traefik labels).

### Long builds may time out over SSH

Native module compilation (e.g., `better-sqlite3` C++ bindings) can take several minutes. If the SSH session times out, run the build in the background:

```bash
ssh wapp01admin@10.69.69.10 "cd /home/wapp01admin/apps/<name> && nohup docker compose up -d --build > /tmp/build.log 2>&1 &"
```

Check progress:
```bash
ssh wapp01admin@10.69.69.10 "tail -20 /tmp/build.log > /tmp/progress.txt"
scp wapp01admin@10.69.69.10:/tmp/progress.txt ./progress.txt
```

### NextAuth respects basePath automatically

When `basePath` is set in `next.config.ts`, Next.js prepends it to `pages` paths in NextAuth config. So `pages: { signIn: "/login" }` automatically becomes `/sow-builder/login` at runtime — no manual path adjustment needed.

### Multi-service builds take longer

Apps with multiple services (e.g., veeam-audit with 3 containers) take longer to build since Docker must build each image. The `postgres:16` image is pre-built (just pulled), but custom images (`api`, `frontend`) are built from source. Use the `nohup` background pattern (above) to avoid SSH timeouts.

### nginx proxy_pass hostname must match the compose service name

In multi-service apps, if nginx proxies API requests via `proxy_pass http://api:8000`, the hostname `api` must match the compose service name — **not** the `container_name`. Docker Compose DNS resolves service names on the project's default network. Using `container_name` (e.g., `veeam-audit-api`) would fail because container names are resolved on the host Docker network, not the compose network.

### Git warnings about CRLF are a signal

When you see `warning: LF will be replaced by CRLF` during `git add`, that file will have Windows line endings in the repo. For any file that runs as a script inside a Linux container (`.sh`, entrypoints), fix this before committing.
