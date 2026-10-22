#!/usr/bin/env bash
# Read-only container/runtime diagnostics. NEVER removes containers, tasks or volumes.
set -Eeuo pipefail
CONTAINER=lumiere-dev-mongo
echo '=== Docker daemon ==='
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}' 2>&1 || true
echo '=== Existing MongoDB container ==='
docker inspect "$CONTAINER" --format 'ID={{.Id}} Status={{.State.Status}} Running={{.State.Running}} Exit={{.State.ExitCode}} OOM={{.State.OOMKilled}} Started={{.State.StartedAt}} Finished={{.State.FinishedAt}} Runtime={{.HostConfig.Runtime}}' 2>&1 || true
echo '=== Docker runtime configuration ==='
docker info --format 'Runtimes={{json .Runtimes}} Default={{.DefaultRuntime}} Driver={{.Driver}}' 2>&1 || true
echo '=== Runtime processes ==='
ps -eo pid,ppid,stat,comm,args | grep -E '(^ *PID|[d]ockerd|[c]ontainerd|[r]unc|[m]ongod)' | cut -c1-180 | head -30 || true
echo '=== Recent kernel runtime and resource messages ==='
if command -v journalctl >/dev/null 2>&1; then
  journalctl -k --since '-30 minutes' --no-pager 2>/dev/null | grep -Ei 'oom|containerd|runc|overlay|docker' | tail -25 || true
fi
echo '=== Memory and disk ==='
free -h || true
df -h / /workspaces || true
echo 'No mutations performed. For OCI container-ID conflicts, STOP and reopen the SAME Codespace; never delete volumes or runtime state.'
