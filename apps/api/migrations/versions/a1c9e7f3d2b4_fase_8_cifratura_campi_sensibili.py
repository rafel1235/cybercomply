"""fase 8: cifratura campi sensibili (vat_number, incidents.data)

Revision ID: a1c9e7f3d2b4
Revises: 37d54ba648cf
Create Date: 2026-07-27 10:00:00.000000

Cambia il tipo di due colonne per ospitare valori cifrati (Fase 8 — roadmap tecnica:
"cifrare dati sensibili a riposo, almeno P.IVA e dati incidenti"):
- organizations.vat_number: VARCHAR(32) -> TEXT (il testo cifrato è più lungo del
  valore in chiaro originale).
- incidents.data: JSONB -> TEXT (il valore cifrato è un blob opaco, non più JSON
  interrogabile lato SQL; l'applicazione lo serializza/deserializza da sé, vedi
  app/db/encrypted_types.py).

I valori esistenti (se presenti) restano in chiaro finché non vengono riscritti
dall'applicazione: `USING ...::text` li converte al nuovo tipo colonna senza perdita,
e `field_encryption.decrypt_value` riconosce e restituisce invariati i valori senza il
prefisso "enc::" (mai stati cifrati), quindi non serve un backfill per questa migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c9e7f3d2b4"
down_revision: str | None = "37d54ba648cf"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE organizations ALTER COLUMN vat_number TYPE TEXT USING vat_number::text")
    op.execute("ALTER TABLE incidents ALTER COLUMN data TYPE TEXT USING data::text")


def downgrade() -> None:
    # Il downgrade riparte da dati in chiaro: se nel frattempo sono stati scritti valori
    # cifrati (prefisso "enc::"), il downgrade li lascerebbe illeggibili come JSON/testo
    # semplice — accettabile per una migration di rollback di sviluppo, da non eseguire
    # su un database di produzione con dati già cifrati senza prima decifrarli a mano.
    op.execute(
        "ALTER TABLE organizations ALTER COLUMN vat_number TYPE VARCHAR(32) USING vat_number::varchar(32)"
    )
    op.execute("ALTER TABLE incidents ALTER COLUMN data TYPE JSONB USING data::jsonb")
