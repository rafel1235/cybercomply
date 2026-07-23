"""Prompt per la generazione AI dei 9 documenti di conformità (Fase 5, roadmap tecnica).

Ogni documento riusa la stessa struttura a sezioni già definita in `document_catalog`
(`DOCUMENT_SECTION_TEMPLATES`): il prompt chiede al modello di scrivere il contenuto reale
per ciascuna sezione prevista, non di inventare una struttura diversa. Questo mantiene
identico lo schema JSON già consumato dal frontend (Fase 4) — cambia solo il "corpo" delle
sezioni, da segnaposto a testo vero.
"""

from app.models.document import DocumentType
from app.models.organization import Organization
from app.services.document_catalog import DOCUMENT_SECTION_TEMPLATES

# Riferimenti normativi puntuali per tipo di documento (Guida al Servizio + roadmap
# tecnica), inclusi nel prompt così il modello li cita con precisione invece di
# generalizzare genericamente su "la normativa vigente".
_REGULATORY_REFERENCES: dict[DocumentType, list[str]] = {
    DocumentType.registro_rischi: [
        "Art. 21(2)(a) D.Lgs. 138/2024 (NIS2) — valutazione del rischio",
        "Determinazione ACN 164179/2025, §3 — misure tecniche minime",
    ],
    DocumentType.procedura_incident_response: [
        "Art. 23 D.Lgs. 138/2024 (NIS2) — notifica incidenti 24h/72h/30gg",
        "Reg. UE 2024/2847 (CRA), Art. 14 — notifica vulnerabilità sfruttate",
    ],
    DocumentType.piano_bcp: [
        "Art. 21(2)(c) D.Lgs. 138/2024 (NIS2) — continuità operativa e gestione delle crisi",
    ],
    DocumentType.politica_supply_chain: [
        "Art. 21(2)(d) D.Lgs. 138/2024 (NIS2) — sicurezza della catena di approvvigionamento",
    ],
    DocumentType.politica_crittografia: [
        "Art. 21(2)(h) D.Lgs. 138/2024 (NIS2) — crittografia e cifratura",
        "Determinazione ACN 164179/2025, §4 — controlli tecnici",
    ],
    DocumentType.politica_controllo_accessi: [
        "Art. 21(2)(i) D.Lgs. 138/2024 (NIS2) — controllo degli accessi e MFA",
    ],
    DocumentType.procedura_vulnerability_disclosure: [
        "Reg. UE 2024/2847 (CRA), Art. 14 — gestione e divulgazione delle vulnerabilità",
        "Determinazione ACN 164179/2025, §4.5 — vulnerability management",
    ],
    DocumentType.piano_formazione: [
        "Art. 20(2) D.Lgs. 138/2024 (NIS2) — formazione del personale in cybersecurity",
    ],
    DocumentType.registro_asset_critici: [
        "Determinazione ACN 164179/2025, §3.1 — censimento e aggiornamento degli asset critici",
    ],
}

_SYSTEM_PROMPT = """Sei un consulente esperto di conformità normativa NIS2 (D.Lgs. 138/2024) \
e Cyber Resilience Act (Reg. UE 2024/2847) per PMI italiane. Scrivi documenti di \
conformità professionali, precisi e concreti, in italiano formale.

Regole vincolanti:
1. Rispondi SOLO con un oggetto JSON valido, senza testo prima o dopo, nel formato esatto:
   {"sezioni": [{"titolo": "...", "corpo": "..."}]}
2. Devi produrre esattamente una voce in "sezioni" per ciascun titolo richiesto, nello \
stesso ordine, usando esattamente lo stesso testo del titolo fornito.
3. Il "corpo" di ogni sezione deve essere testo concreto e specifico per l'azienda \
descritta (usa i dati forniti: settore, dimensione, categoria NIS2), non un testo generico \
copiabile da qualunque azienda. Dove mancano dati specifici, usa un placeholder esplicito \
tra parentesi quadre (es. "[nome del responsabile IT]") invece di inventare fatti concreti \
non forniti.
4. Cita i riferimenti normativi indicati, in modo naturale nel testo, non come lista a parte.
5. Non includere disclaimer legali nel corpo delle sezioni: il disclaimer viene aggiunto \
automaticamente dalla piattaforma."""


def build_document_prompt(
    doc_type: DocumentType, organization: Organization, context: dict
) -> tuple[str, str]:
    """Costruisce (system_prompt, user_prompt) per la generazione di `doc_type`.

    `context` può contenere: `nis2_category`, `cra_in_scope` (ultimo assessment, se
    presente) — usati per personalizzare il documento senza dover ripetere query nel
    servizio chiamante.
    """
    sections = DOCUMENT_SECTION_TEMPLATES.get(doc_type, [])
    references = _REGULATORY_REFERENCES.get(doc_type, [])

    org_lines = [
        f"Ragione sociale: {organization.name}",
        f"Settore: {organization.sector or 'non specificato'}",
        f"Numero dipendenti: {organization.employee_count or 'non specificato'}",
    ]
    if context.get("nis2_category"):
        org_lines.append(f"Categoria NIS2: {context['nis2_category']}")
    if "cra_in_scope" in context:
        org_lines.append(
            f"In perimetro CRA: {'sì' if context['cra_in_scope'] else 'no'}"
        )

    sections_list = "\n".join(f"- {s}" for s in sections)
    references_list = (
        "\n".join(f"- {r}" for r in references) or "- Normativa generale NIS2/CRA"
    )

    user_prompt = f"""Genera il documento "{doc_type.value.replace('_', ' ')}" per la \
seguente azienda:

{chr(10).join(org_lines)}

Sezioni richieste (in quest'ordine esatto):
{sections_list}

Riferimenti normativi da citare dove pertinente:
{references_list}

Rispondi solo con il JSON richiesto."""

    return _SYSTEM_PROMPT, user_prompt
