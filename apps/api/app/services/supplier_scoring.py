"""Calcolo dello stato di conformità di un fornitore dalle risposte al questionario.

Domande fisse del questionario di sicurezza fornitori (Guida al Servizio, §4.4): risposte
booleane su controlli minimi attesi. Lo stato non è mai lasciato alla libera
interpretazione del fornitore: si calcola sempre allo stesso modo, sommando le risposte
positive sulle domande fisse (le chiavi mancanti nelle risposte contano come "no").
"""

from app.models.supplier import SupplierStatus

QUESTIONNAIRE_QUESTIONS: list[str] = [
    "mfa_attivo",
    "certificazione_iso27001",
    "backup_testato",
    "incident_response_documentato",
    "formazione_sicurezza_annuale",
]


def compute_supplier_status(answers: dict) -> SupplierStatus:
    positive_count = sum(1 for q in QUESTIONNAIRE_QUESTIONS if answers.get(q) is True)
    total = len(QUESTIONNAIRE_QUESTIONS)

    if positive_count == total:
        return SupplierStatus.conforme
    if positive_count == 0:
        return SupplierStatus.non_conforme
    return SupplierStatus.parziale
