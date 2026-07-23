"""Struttura a sezioni dei 9 documenti generabili (Guida al Servizio, §4.3).

In questa fase (Fase 3 — API) la generazione produce contenuto segnaposto strutturato
secondo lo scheletro corretto per tipo di documento: il motore AI che scriverà il
contenuto vero arriva in Fase 5. Tenere lo scheletro qui, condiviso tra generazione e
test, evita di dover riscrivere le sezioni quando arriverà il motore AI: basterà
sostituire il corpo di ogni sezione, non la struttura.
"""

from app.models.document import DocumentType

DOCUMENT_SECTION_TEMPLATES: dict[DocumentType, list[str]] = {
    DocumentType.registro_rischi: [
        "Metodologia di valutazione del rischio",
        "Inventario degli asset critici",
        "Minacce e vulnerabilità identificate",
        "Valutazione probabilità/impatto",
        "Misure di mitigazione adottate",
    ],
    DocumentType.procedura_incident_response: [
        "Definizione e classificazione degli incidenti",
        "Ruoli e responsabilità del team di risposta",
        "Fasi operative: rilevazione, contenimento, eradicazione, ripristino",
        "Obblighi di notifica (CSIRT Italia, ACN, autorità competenti)",
        "Comunicazione interna ed esterna durante l'incidente",
    ],
    DocumentType.piano_bcp: [
        "Analisi di impatto sul business (BIA)",
        "Strategie di continuità operativa",
        "Piano di disaster recovery e RTO/RPO",
        "Procedure di test e aggiornamento del piano",
    ],
    DocumentType.politica_supply_chain: [
        "Criteri di classificazione dei fornitori critici",
        "Requisiti di sicurezza contrattuali",
        "Processo di valutazione e monitoraggio dei fornitori",
        "Gestione degli incidenti originati da terze parti",
    ],
    DocumentType.politica_crittografia: [
        "Standard crittografici adottati",
        "Gestione del ciclo di vita delle chiavi",
        "Crittografia dei dati a riposo e in transito",
        "Controlli di accesso alle chiavi crittografiche",
    ],
    DocumentType.politica_controllo_accessi: [
        "Principio del privilegio minimo",
        "Gestione delle identità e autenticazione",
        "Autenticazione a più fattori per accessi privilegiati",
        "Revisione periodica dei permessi",
    ],
    DocumentType.procedura_vulnerability_disclosure: [
        "Canale di segnalazione delle vulnerabilità",
        "Tempistiche di risposta e remediation",
        "Politica di divulgazione responsabile",
        "Riconoscimento ai segnalatori",
    ],
    DocumentType.piano_formazione: [
        "Obiettivi formativi annuali",
        "Destinatari e frequenza della formazione",
        "Contenuti minimi (phishing, gestione password, incident reporting)",
        "Verifica dell'efficacia della formazione",
    ],
    DocumentType.registro_asset_critici: [
        "Metodologia di censimento degli asset",
        "Classificazione per criticità",
        "Proprietari e responsabili degli asset",
        "Modalità di aggiornamento del registro",
    ],
}


def build_placeholder_content(doc_type: DocumentType) -> dict:
    sections = DOCUMENT_SECTION_TEMPLATES.get(doc_type, [])
    return {
        "generato_da": "placeholder",
        "nota": "Contenuto segnaposto: la generazione automatica con AI arriva in Fase 5.",
        "sezioni": [
            {
                "titolo": titolo,
                "corpo": "Sezione da completare con il motore di generazione AI (Fase 5).",
            }
            for titolo in sections
        ],
    }
