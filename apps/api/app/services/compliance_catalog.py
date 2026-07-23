"""Catalogo statico delle 15 misure tecniche e organizzative della Determinazione ACN
164179/2025, citate nella Guida al Servizio (§2.2).

Non è una tabella di database perché non varia per organizzazione: è lo stesso elenco per
tutti i clienti della piattaforma. Ogni organizzazione ha invece una riga in
`compliance_measures` per ciascuna voce di questo catalogo, con il proprio stato.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComplianceMeasureDefinition:
    measure_id: str
    label: str
    normative_reference: str


COMPLIANCE_MEASURE_CATALOG: list[ComplianceMeasureDefinition] = [
    ComplianceMeasureDefinition(
        "valutazione_rischio_annuale",
        "Valutazione del rischio documentata e aggiornata almeno annualmente",
        "Art. 21(2)(a) NIS2",
    ),
    ComplianceMeasureDefinition(
        "mfa_accessi_remoti_privilegiati",
        "Autenticazione a più fattori (MFA) per accessi remoti e privilegiati",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "backup_cifrati_testati",
        "Backup cifrati e testati con procedura documentata",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "vulnerability_scanning_periodico",
        "Vulnerability scanning periodico con SLA di remediation definiti",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "piano_business_continuity",
        "Piano di business continuity e disaster recovery testato",
        "Art. 21(2)(c) NIS2",
    ),
    ComplianceMeasureDefinition(
        "formazione_personale_annuale",
        "Formazione del personale in materia di cybersecurity almeno una volta l'anno",
        "Art. 20 NIS2",
    ),
    ComplianceMeasureDefinition(
        "registro_fornitori_ict_critici",
        "Registro dei fornitori ICT critici con valutazione del rischio",
        "Art. 21(2)(d) NIS2",
    ),
    ComplianceMeasureDefinition(
        "gestione_incidenti_procedura",
        "Procedura di gestione degli incidenti documentata",
        "Art. 21(2)(b) NIS2",
    ),
    ComplianceMeasureDefinition(
        "crittografia_dati_a_riposo",
        "Politica di crittografia e gestione delle chiavi",
        "Art. 21(2)(h) NIS2",
    ),
    ComplianceMeasureDefinition(
        "controllo_accessi_privilegi_minimi",
        "Politica di controllo degli accessi basata sul privilegio minimo",
        "Art. 21(2)(i) NIS2",
    ),
    ComplianceMeasureDefinition(
        "segmentazione_rete",
        "Segmentazione della rete per isolare i sistemi critici",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "patch_management",
        "Processo di patch management con tempistiche definite",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "monitoraggio_log_centralizzato",
        "Monitoraggio e conservazione centralizzata dei log",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "piano_disaster_recovery_testato",
        "Piano di disaster recovery testato almeno una volta l'anno",
        "Det. ACN 164179/2025",
    ),
    ComplianceMeasureDefinition(
        "revisione_contratti_fornitori_ict",
        "Revisione periodica delle clausole di sicurezza nei contratti con fornitori ICT",
        "Det. ACN 164179/2025 §6.1",
    ),
]

COMPLIANCE_MEASURE_IDS: list[str] = [m.measure_id for m in COMPLIANCE_MEASURE_CATALOG]
