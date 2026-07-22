#!/usr/bin/env bash
# Backup automatico del database CyberComplyIT (Fase 2 della roadmap tecnica).
#
# In produzione su Supabase i backup giornalieri sono già inclusi automaticamente
# (vedi roadmap Fase 9): questo script serve per due casi che Supabase non copre da solo:
#   1. un backup locale extra prima di operazioni rischiose (es. prima di una migration
#      importante o di un cambio piano);
#   2. un secondo backup indipendente su storage separato, come richiesto esplicitamente
#      dalla roadmap ("Backup dei file su storage separato" — qui applicato al database).
#
# Uso:
#   DATABASE_URL="postgresql://user:pass@host:5432/dbname" ./scripts/backup_db.sh
#
# Ripristino da un backup (da testare almeno una volta prima del lancio, roadmap Fase 9):
#   pg_restore --clean --if-exists --dbname="$DATABASE_URL" cybercomplyit_TIMESTAMP.dump
#
# Pianificazione consigliata (cron, es. ogni notte alle 3:00):
#   0 3 * * * DATABASE_URL="..." /percorso/completo/scripts/backup_db.sh >> /var/log/cybercomplyit-backup.log 2>&1
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "Errore: variabile DATABASE_URL non impostata." >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DIR}/cybercomplyit_${TIMESTAMP}.dump"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date -u)] Avvio backup verso ${BACKUP_FILE}"

# Formato "custom" di pg_dump: compresso e ripristinabile selettivamente con pg_restore,
# a differenza di un semplice dump SQL testuale.
pg_dump --format=custom --file="$BACKUP_FILE" "$DATABASE_URL"

echo "[$(date -u)] Backup completato: $(du -h "$BACKUP_FILE" | cut -f1)"

# Pulizia dei backup più vecchi della retention configurata (default 30 giorni).
find "$BACKUP_DIR" -name 'cybercomplyit_*.dump' -mtime "+${RETENTION_DAYS}" -print -delete

echo "[$(date -u)] Backup vecchi oltre ${RETENTION_DAYS} giorni rimossi (se presenti)."
