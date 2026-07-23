"""Classificazione NIS2/CRA da risposte strutturate di self-assessment.

Logica derivata dalla Guida al Servizio (§1.3, "Come capire se rientri nel perimetro"):
- Soglia dimensionale NIS2: rientrano le medie e grandi imprese (>=50 dipendenti O
  fatturato/bilancio annuo > 10 mln EUR) che operano nei settori dell'Allegato I
  (soggetti essenziali) o Allegato II (soggetti importanti) del D.Lgs. 138/2024.
- Le microimprese e piccole imprese sono di norma escluse, MA la Guida segnala
  esplicitamente il rischio "supply chain": un fornitore ICT di un soggetto NIS2,
  anche se piccolo, viene trascinato dentro per via contrattuale. Per questo motivo,
  se `supplies_ict_to_regulated_entities` è vero, classifichiamo in modo prudenziale
  come "importante" anche sotto soglia dimensionale, come da avvertenza della Guida.
- Il CRA (Cyber Resilience Act) si applica a chi produce/vende prodotti con elementi
  digitali per il mercato UE, indipendentemente dalla dimensione dell'impresa.
"""

from dataclasses import dataclass
from typing import Literal

from app.models.assessment import Nis2Category

SectorAnnex = Literal["allegato_i", "allegato_ii", "nessuno"]

NIS2_EMPLOYEE_THRESHOLD = 50
NIS2_REVENUE_THRESHOLD_EUR = 10_000_000


@dataclass
class AssessmentAnswersData:
    sector_annex: SectorAnnex
    employee_count: int
    annual_revenue_eur: int
    supplies_ict_to_regulated_entities: bool
    produces_digital_product_for_eu_market: bool


@dataclass
class ClassificationResult:
    nis2_category: Nis2Category
    cra_in_scope: bool
    rationale: str


def classify(answers: AssessmentAnswersData) -> ClassificationResult:
    meets_size_threshold = (
        answers.employee_count >= NIS2_EMPLOYEE_THRESHOLD
        or answers.annual_revenue_eur > NIS2_REVENUE_THRESHOLD_EUR
    )

    if answers.sector_annex == "allegato_i" and meets_size_threshold:
        nis2_category = Nis2Category.essenziale
        rationale = (
            "Settore in Allegato I (soggetti essenziali) e dimensione sopra soglia "
            "NIS2 (>=50 dipendenti o >10 mln EUR fatturato)."
        )
    elif answers.sector_annex == "allegato_ii" and meets_size_threshold:
        nis2_category = Nis2Category.importante
        rationale = (
            "Settore in Allegato II (soggetti importanti) e dimensione sopra soglia "
            "NIS2 (>=50 dipendenti o >10 mln EUR fatturato)."
        )
    elif answers.supplies_ict_to_regulated_entities:
        nis2_category = Nis2Category.importante
        rationale = (
            "Sotto soglia dimensionale o fuori settore diretto, ma fornisce servizi/prodotti "
            "ICT a soggetti regolati NIS2: classificazione prudenziale come 'importante' "
            "per rischio di trascinamento contrattuale nella supply chain (cfr. Guida al "
            "Servizio §1.3)."
        )
    else:
        nis2_category = Nis2Category.non_in_perimetro
        rationale = (
            "Non risultano soddisfatti i criteri dimensionali/settoriali NIS2 né il "
            "rischio di trascinamento da supply chain."
        )

    cra_in_scope = answers.produces_digital_product_for_eu_market

    return ClassificationResult(
        nis2_category=nis2_category, cra_in_scope=cra_in_scope, rationale=rationale
    )
