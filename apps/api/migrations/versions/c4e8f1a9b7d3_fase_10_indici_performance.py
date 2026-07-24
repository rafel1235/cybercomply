"""fase 10: indici mancanti su audit_logs e suppliers (performance)

Revision ID: c4e8f1a9b7d3
Revises: a1c9e7f3d2b4
Create Date: 2026-07-24 09:00:00.000000

Fase 10 (roadmap tecnica — "Analizzare le query PostgreSQL più lente con EXPLAIN ANALYZE"
e "Aggiungere indici sulle colonne mancanti dopo analisi"). Analisi eseguita su Postgres
embedded con `EXPLAIN ANALYZE` sulle query reali di `GET /audit-log`, `GET
/compliance/history` e `GET /suppliers`:

- `audit_logs` non aveva NESSUN indice oltre alla chiave primaria, pur essendo la tabella
  con la crescita più rapida di tutto lo schema (una riga per ogni azione registrata) e
  interrogata ad ogni caricamento della dashboard. Aggiunti due indici compositi:
  `(organization_id, created_at)` per la lista generale, `(organization_id, action,
  created_at)` per lo storico del punteggio di conformità (filtrato anche per `action`).
- `suppliers` aveva già un indice `(organization_id, status)` (pensato per un futuro
  filtro per stato, mai implementato) ma nessuno che copra l'ordinamento reale della
  lista (`created_at desc`). Aggiunto `(organization_id, created_at)`.

Nessuna altra tabella toccata in questa fase: `documents`, `incidents`,
`assessment_results` e `compliance_measures` avevano già l'indice composito
`(organization_id, <colonna di ordinamento>)` corretto fin dalla Fase 2.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e8f1a9b7d3"
down_revision: str | None = "a1c9e7f3d2b4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_org_created", "audit_logs", ["organization_id", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_org_action_created",
        "audit_logs",
        ["organization_id", "action", "created_at"],
    )
    op.create_index(
        "ix_suppliers_org_created", "suppliers", ["organization_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_suppliers_org_created", table_name="suppliers")
    op.drop_index("ix_audit_logs_org_action_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created", table_name="audit_logs")
