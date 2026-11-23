#!/usr/bin/env bash
# Migration'ları geçici bir yerel Postgres'e uygular ve SQL testlerini çalıştırır.
# Gerekenler: PostgreSQL 15+ ikili dosyaları (initdb, pg_ctl, psql) PATH'te.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PGBIN="${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"
export PATH="$PGBIN:$PATH"
DATA="$(mktemp -d)"
PORT="${PGPORT:-$((20000 + RANDOM % 20000))}"
if [ "$(id -u)" = "0" ]; then RUN="runuser -u postgres --"; chown postgres "$DATA"; else RUN=""; fi
cleanup() { $RUN pg_ctl -D "$DATA" -m fast -w stop >/dev/null 2>&1 || true; rm -rf "$DATA"; }
trap cleanup EXIT
$RUN initdb -D "$DATA" -U postgres -A trust >/dev/null
$RUN pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l "$DATA/log" -w start >/dev/null
PSQL="psql -h /tmp -p $PORT -U postgres -v ON_ERROR_STOP=1 -q"
$PSQL -c "create database t" >/dev/null
$PSQL -d t -f "$HERE/supabase_stub.sql" 2>/dev/null
for f in "$ROOT"/migrations/*.sql; do echo "migration: $(basename "$f")"; $PSQL -d t -f "$f"; done
for f in "$HERE"/sql/*.sql; do echo "test: $(basename "$f")"; $PSQL -d t -f "$f" >"$DATA/out.txt" || { cat "$DATA/out.txt"; exit 1; }; done
echo "test: eşzamanlı eşleşme"
PSQL="$PSQL" bash "$HERE/concurrency.sh"
echo "TÜM TESTLER GEÇTİ"
