"""Calcolo delle scadenze di notifica NIS2/CRA a partire dall'apertura di un incidente.

Le scadenze sono derivate matematicamente da `opened_at` (Guida al Servizio, §2.3: "early
warning" entro 24h, notifica entro 72h, relazione finale entro 30gg per NIS2 Art. 23; per
il CRA, ENISA prevede scadenze analoghe a 24h/72h). Non c'è bisogno di una tabella
separata per le scadenze: si ricalcolano sempre dalla data di apertura, e lo stato "inviata"
si verifica controllando se esiste già una `IncidentNotification` per quella fase.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.incident import IncidentNotification, NotificationPhase

_DEADLINE_OFFSETS: dict[NotificationPhase, timedelta] = {
    NotificationPhase.early_warning_24h: timedelta(hours=24),
    NotificationPhase.notifica_72h: timedelta(hours=72),
    NotificationPhase.relazione_30gg: timedelta(days=30),
    NotificationPhase.cra_enisa_24h: timedelta(hours=24),
    NotificationPhase.cra_enisa_72h: timedelta(hours=72),
}


@dataclass
class DeadlineStatus:
    phase: NotificationPhase
    due_at: datetime
    sent: bool
    sent_at: datetime | None
    overdue: bool


def compute_deadlines(
    opened_at: datetime,
    notifications: list[IncidentNotification],
    *,
    now: datetime | None = None,
) -> list[DeadlineStatus]:
    now = now or datetime.now(opened_at.tzinfo)
    sent_by_phase = {n.phase: n.sent_at for n in notifications}

    statuses = []
    for phase, offset in _DEADLINE_OFFSETS.items():
        due_at = opened_at + offset
        sent_at = sent_by_phase.get(phase)
        statuses.append(
            DeadlineStatus(
                phase=phase,
                due_at=due_at,
                sent=sent_at is not None,
                sent_at=sent_at,
                overdue=(sent_at is None and now > due_at),
            )
        )
    return statuses
