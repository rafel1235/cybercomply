"""Template HTML delle email transazionali (Fase 7 — roadmap tecnica).

Un wrapper brandizzato comune (`_wrapper`) più una funzione per ciascun tipo di email
richiesto dalla roadmap, che ritorna sempre `(subject, html)`. Struttura a tabella e stile
inline per la massima compatibilità con i client email (Gmail, Outlook), che ignorano o
filtrano i fogli di stile esterni. Le funzioni prendono URL già completi (mai
`settings.frontend_base_url` importato qui): tenere questo modulo puro e senza I/O rende
i template testabili senza dover mai configurare nulla.

Non incluse qui (per scelta, vedi ROADMAP_PROGRESS.md): conferma registrazione e reset
password, che restano email native di Supabase Auth finché non colleghiamo un progetto
Supabase reale con SMTP personalizzato — non email inviate da questo backend."""

_BRAND_DARK = "#0B2545"
_BRAND_BLUE = "#1B6EC2"
_BRAND_AMBER = "#E8871E"


def _wrapper(
    *,
    preheader: str,
    title: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> str:
    cta_html = ""
    if cta_label and cta_url:
        cta_html = f"""
            <tr>
              <td style="padding:8px 32px 28px 32px;">
                <a href="{cta_url}" style="display:inline-block;background:{_BRAND_BLUE};color:#ffffff;
                  text-decoration:none;padding:12px 24px;border-radius:6px;font-weight:600;
                  font-family:Arial,Helvetica,sans-serif;font-size:14px;">{cta_label}</a>
              </td>
            </tr>"""
    return f"""<!DOCTYPE html>
<html lang="it">
  <head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /></head>
  <body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">
    <span style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0"
            style="background:#ffffff;border-radius:8px;overflow:hidden;max-width:560px;width:100%;">
            <tr>
              <td style="background:{_BRAND_DARK};padding:20px 32px;">
                <span style="color:#ffffff;font-size:18px;font-weight:700;">CyberComply<span
                  style="color:{_BRAND_AMBER};">IT</span></span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px 32px 8px 32px;">
                <h1 style="margin:0 0 16px 0;font-size:20px;color:{_BRAND_DARK};">{title}</h1>
                <div style="font-size:14px;line-height:1.6;color:#334155;">{body_html}</div>
              </td>
            </tr>
            {cta_html}
            <tr>
              <td style="padding:20px 32px;border-top:1px solid #e2e8f0;">
                <p style="margin:0;font-size:12px;color:#94a3b8;">
                  CyberComplyIT — piattaforma di conformità NIS2 e Cyber Resilience Act per PMI
                  italiane. Questa è un'email transazionale relativa al tuo account.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def welcome_email(
    *, organization_name: str, trial_days: int, dashboard_url: str
) -> tuple[str, str]:
    subject = f"Benvenuto in CyberComplyIT, {organization_name}"
    body = f"""
        <p>Benvenuto! L'account di <strong>{organization_name}</strong> è attivo, con
        {trial_days} giorni di prova gratuita del piano Essential — nessuna carta di credito
        richiesta.</p>
        <p>Puoi da subito: eseguire l'assessment di applicabilità NIS2/CRA, iniziare a tracciare
        le misure di conformità richieste, e generare i primi documenti previsti dalla
        normativa.</p>
    """
    return subject, _wrapper(
        preheader="Il tuo account CyberComplyIT è pronto.",
        title="Benvenuto in CyberComplyIT",
        body_html=body,
        cta_label="Vai alla dashboard",
        cta_url=dashboard_url,
    )


def invite_email(
    *, organization_name: str, inviter_name: str, role_label: str, accept_url: str
) -> tuple[str, str]:
    subject = f"{inviter_name} ti ha invitato su CyberComplyIT"
    body = f"""
        <p><strong>{inviter_name}</strong> ti ha invitato a collaborare su
        <strong>{organization_name}</strong> con ruolo <strong>{role_label}</strong> sulla
        piattaforma di conformità NIS2/CRA CyberComplyIT.</p>
        <p>L'invito scade tra 7 giorni. Se non ti aspettavi questa email, puoi ignorarla.</p>
    """
    return subject, _wrapper(
        preheader=f"{inviter_name} ti ha invitato su CyberComplyIT.",
        title="Sei stato invitato",
        body_html=body,
        cta_label="Accetta l'invito",
        cta_url=accept_url,
    )


def payment_succeeded_email(
    *,
    organization_name: str,
    plan_label: str,
    invoice_url: str | None,
    billing_url: str,
) -> tuple[str, str]:
    subject = "Pagamento confermato — CyberComplyIT"
    invoice_line = (
        f'<p><a href="{invoice_url}" style="color:{_BRAND_BLUE};">Scarica la fattura</a></p>'
        if invoice_url
        else ""
    )
    body = f"""
        <p>Il pagamento per il piano <strong>{plan_label}</strong> di
        <strong>{organization_name}</strong> è andato a buon fine. Grazie per la fiducia.</p>
        {invoice_line}
    """
    return subject, _wrapper(
        preheader="Il tuo pagamento è stato confermato.",
        title="Pagamento confermato",
        body_html=body,
        cta_label="Gestisci abbonamento",
        cta_url=billing_url,
    )


def payment_failed_email(
    *, organization_name: str, plan_label: str, billing_url: str
) -> tuple[str, str]:
    subject = "Pagamento non riuscito — azione richiesta"
    body = f"""
        <p>L'ultimo pagamento per il piano <strong>{plan_label}</strong> di
        <strong>{organization_name}</strong> non è andato a buon fine.</p>
        <p>Aggiorna il metodo di pagamento per evitare un'interruzione del servizio: i tuoi dati
        restano comunque al sicuro, non vengono mai cancellati.</p>
    """
    return subject, _wrapper(
        preheader="Aggiorna il metodo di pagamento per evitare interruzioni.",
        title="Pagamento non riuscito",
        body_html=body,
        cta_label="Aggiorna metodo di pagamento",
        cta_url=billing_url,
    )


def subscription_canceled_email(
    *, organization_name: str, billing_url: str
) -> tuple[str, str]:
    subject = "Il tuo abbonamento è stato annullato"
    body = f"""
        <p>L'abbonamento di <strong>{organization_name}</strong> è stato annullato e
        l'organizzazione è tornata al piano Free.</p>
        <p>Nessun dato è stato cancellato: assessment, misure di conformità, documenti e
        incidenti restano tutti consultabili in sola lettura dove previsto dal piano Free.</p>
    """
    return subject, _wrapper(
        preheader="Il tuo account è tornato al piano Free. I tuoi dati sono al sicuro.",
        title="Abbonamento annullato",
        body_html=body,
        cta_label="Rivedi i piani",
        cta_url=billing_url,
    )


def trial_ending_email(
    *, organization_name: str, days_left: int, billing_url: str
) -> tuple[str, str]:
    when = "domani" if days_left <= 1 else f"tra {days_left} giorni"
    subject = f"La prova di {organization_name} scade {when}"
    body = f"""
        <p>La prova gratuita del piano Essential per <strong>{organization_name}</strong> scade
        {when}.</p>
        <p>Passa a un piano a pagamento in qualsiasi momento per continuare senza interruzioni,
        oppure non fare nulla: alla scadenza l'account torna automaticamente al piano Free, senza
        che nessun dato venga cancellato.</p>
    """
    return subject, _wrapper(
        preheader=f"La prova gratuita scade {when}.",
        title="La tua prova sta per scadere",
        body_html=body,
        cta_label="Passa a un piano a pagamento",
        cta_url=billing_url,
    )


def trial_expired_email(*, organization_name: str, billing_url: str) -> tuple[str, str]:
    subject = f"{organization_name} è tornata al piano Free"
    body = f"""
        <p>La prova gratuita di Essential per <strong>{organization_name}</strong> è scaduta e
        l'account è tornato al piano Free.</p>
        <p>Tutti i tuoi dati restano intatti. Sul piano Free il Compliance Tracker mostra 3 misure
        in sola lettura e la generazione documenti/Incident Reporting/Supply Chain non sono
        inclusi: passa a Essential o superiore in qualsiasi momento per riattivarli.</p>
    """
    return subject, _wrapper(
        preheader="La prova è scaduta: il tuo account è ora sul piano Free.",
        title="Il tuo account è tornato al piano Free",
        body_html=body,
        cta_label="Rivedi i piani",
        cta_url=billing_url,
    )


def nis2_deadline_email(
    *,
    organization_name: str,
    deadline_label: str,
    deadline_date: str,
    days_left: int,
    dashboard_url: str,
) -> tuple[str, str]:
    subject = f"Scadenza normativa tra {days_left} giorni: {deadline_label}"
    body = f"""
        <p>Promemoria per <strong>{organization_name}</strong>: tra {days_left} giorni
        ({deadline_date}) scade la seguente scadenza normativa NIS2/CRA:</p>
        <p style="padding:12px;background:#fff7ed;border-radius:6px;color:#9a3412;">
          {deadline_label}
        </p>
        <p>Verifica lo stato di conformità della tua organizzazione prima della scadenza.</p>
    """
    return subject, _wrapper(
        preheader=f"Tra {days_left} giorni: {deadline_label}",
        title="Scadenza normativa in avvicinamento",
        body_html=body,
        cta_label="Vai al Compliance Tracker",
        cta_url=dashboard_url,
    )


def incident_overdue_email(
    *, organization_name: str, reference_code: str, incident_url: str
) -> tuple[str, str]:
    subject = f"Incidente {reference_code}: notifica 24h non ancora inviata"
    body = f"""
        <p>L'incidente <strong>{reference_code}</strong> di <strong>{organization_name}</strong>
        è aperto da più di 20 ore e la notifica delle 24h (NIS2/CRA) non risulta ancora
        registrata come inviata.</p>
        <p>Verifica se la notifica al CSIRT Italia/ENISA è stata inviata e registrala sulla
        piattaforma, oppure invia una notifica preliminare al più presto.</p>
    """
    return subject, _wrapper(
        preheader=f"Incidente {reference_code}: scadenza 24h in avvicinamento.",
        title="Notifica di incidente in scadenza",
        body_html=body,
        cta_label="Apri l'incidente",
        cta_url=incident_url,
    )


def supplier_stale_email(
    *, organization_name: str, supplier_name: str, supplier_url: str
) -> tuple[str, str]:
    subject = f"Fornitore {supplier_name}: revisione non aggiornata da 6+ mesi"
    body = f"""
        <p>La valutazione del fornitore <strong>{supplier_name}</strong> di
        <strong>{organization_name}</strong> non viene aggiornata da oltre 6 mesi.</p>
        <p>Invia un nuovo questionario di sicurezza per mantenere aggiornato il monitoraggio
        della catena di fornitura.</p>
    """
    return subject, _wrapper(
        preheader=f"{supplier_name}: valutazione da aggiornare.",
        title="Valutazione fornitore da aggiornare",
        body_html=body,
        cta_label="Vai a Supply Chain",
        cta_url=supplier_url,
    )


def monthly_report_email(
    *,
    organization_name: str,
    score_percent: float,
    measures_conformi: int,
    measures_total: int,
    dashboard_url: str,
) -> tuple[str, str]:
    subject = f"Report mensile conformità — {organization_name}"
    body = f"""
        <p>Riepilogo mensile per <strong>{organization_name}</strong>:</p>
        <p style="font-size:28px;font-weight:700;color:{_BRAND_DARK};margin:8px 0;">
          {score_percent:.0f}%
        </p>
        <p>{measures_conformi} misure conformi su {measures_total}.</p>
    """
    return subject, _wrapper(
        preheader=f"Indice di conformità attuale: {score_percent:.0f}%.",
        title="Il tuo report mensile di conformità",
        body_html=body,
        cta_label="Vai al Compliance Tracker",
        cta_url=dashboard_url,
    )
