"""
TenderGreen - Email modul
Šalje lijepo formatiran HTML email sa novim tenderima
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


HITNOST_BOJA = {
    "hitno":     ("#7f1d1d", "#fca5a5", "🔴 HITNO"),
    "uskoro":    ("#78350f", "#fcd34d", "🟡 Ističe uskoro"),
    "normalno":  ("#14532d", "#86efac", "🟢 Aktivan"),
    "nepoznato": ("#1e3a5f", "#93c5fd", "🔵 Nepoznat rok"),
}


def generiši_html(tenderi, naziv_firme="Green Step Company") -> str:
    datum = datetime.now().strftime("%d.%m.%Y u %H:%M")
    ukupno = len(tenderi)
    hitnih = sum(1 for t in tenderi if t.hitnost() == "hitno")
    uskoro = sum(1 for t in tenderi if t.hitnost() == "uskoro")

    tender_html = ""
    for t in tenderi:
        bg, fg, label = HITNOST_BOJA.get(t.hitnost(), HITNOST_BOJA["nepoznato"])
        dana = t.rok_za_n_dana()
        dana_tekst = f"{dana} dana" if dana is not None else "—"

        razlozi_html = "".join(
            f'<li style="margin:3px 0;color:#6b7280;font-size:12px;">✓ {r}</li>'
            for r in t.razlozi[:3]
        )

        tender_html += f"""
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;
                    padding:20px;margin-bottom:16px;border-left:4px solid {fg};">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      margin-bottom:12px;gap:12px;">
            <h3 style="margin:0;font-size:15px;color:#111827;line-height:1.4;flex:1;">
              {t.naslov}
            </h3>
            <span style="background:{bg};color:{fg};padding:3px 10px;border-radius:20px;
                         font-size:11px;font-weight:700;white-space:nowrap;">
              {label}
            </span>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;
                      margin-bottom:14px;">
            <div style="background:#f9fafb;border-radius:8px;padding:10px;">
              <div style="font-size:10px;color:#9ca3af;margin-bottom:4px;
                          text-transform:uppercase;letter-spacing:0.5px;">Naručilac</div>
              <div style="font-size:13px;color:#374151;font-weight:500;">{t.narucilac}</div>
            </div>
            <div style="background:#f9fafb;border-radius:8px;padding:10px;">
              <div style="font-size:10px;color:#9ca3af;margin-bottom:4px;
                          text-transform:uppercase;letter-spacing:0.5px;">Rok prijave</div>
              <div style="font-size:13px;color:#374151;font-weight:500;">
                {t.rok_prijave} <span style="color:{fg};font-size:12px;">({dana_tekst})</span>
              </div>
            </div>
            <div style="background:#f9fafb;border-radius:8px;padding:10px;">
              <div style="font-size:10px;color:#9ca3af;margin-bottom:4px;
                          text-transform:uppercase;letter-spacing:0.5px;">Vrijednost</div>
              <div style="font-size:13px;color:#374151;font-weight:500;">{t.vrijednost or "—"}</div>
            </div>
          </div>

          <div style="margin-bottom:12px;">
            <div style="font-size:10px;color:#9ca3af;margin-bottom:6px;
                        text-transform:uppercase;letter-spacing:0.5px;">Zašto je relevantan</div>
            <ul style="margin:0;padding-left:16px;">{razlozi_html}</ul>
          </div>

          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:20px;
                        padding:3px 12px;font-size:12px;color:#15803d;">
              Relevantnost: <strong>{t.relevantnost}%</strong>
            </div>
            <a href="{t.url}" style="background:#16a34a;color:#ffffff;padding:8px 18px;
               border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
              Pogledaj tender →
            </a>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="bs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>TenderGreen Izvještaj</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#14532d,#166534);border-radius:16px;
                padding:28px 32px;margin-bottom:20px;text-align:center;">
      <div style="font-size:32px;margin-bottom:8px;">🌿</div>
      <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:800;letter-spacing:-0.5px;">
        TenderGreen
      </h1>
      <p style="color:#86efac;margin:6px 0 0;font-size:13px;">{naziv_firme} · {datum}</p>
    </div>

    <!-- Statistike -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;">
      <div style="background:#ffffff;border-radius:10px;padding:16px;text-align:center;
                  border:1px solid #e5e7eb;">
        <div style="font-size:28px;font-weight:800;color:#16a34a;">{ukupno}</div>
        <div style="font-size:11px;color:#9ca3af;margin-top:2px;">NOVIH TENDERA</div>
      </div>
      <div style="background:#ffffff;border-radius:10px;padding:16px;text-align:center;
                  border:1px solid #e5e7eb;">
        <div style="font-size:28px;font-weight:800;color:#dc2626;">{hitnih}</div>
        <div style="font-size:11px;color:#9ca3af;margin-top:2px;">HITNIH</div>
      </div>
      <div style="background:#ffffff;border-radius:10px;padding:16px;text-align:center;
                  border:1px solid #e5e7eb;">
        <div style="font-size:28px;font-weight:800;color:#d97706;">{uskoro}</div>
        <div style="font-size:11px;color:#9ca3af;margin-top:2px;">ISTIČU USKORO</div>
      </div>
    </div>

    <!-- Tenderi -->
    <div style="margin-bottom:20px;">
      <h2 style="font-size:14px;color:#374151;margin:0 0 12px;font-weight:600;
                 text-transform:uppercase;letter-spacing:0.5px;">
        Novi relevantni tenderi
      </h2>
      {tender_html if tender_html else
        '<div style="text-align:center;padding:40px;color:#9ca3af;">Nema novih tendera</div>'}
    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#9ca3af;font-size:11px;">
      <p style="margin:0;">TenderGreen · Automatski monitoring ejn.gov.ba</p>
      <p style="margin:4px 0 0;">Generirano: {datum}</p>
    </div>

  </div>
</body>
</html>"""


def posalji_email(tenderi, novi_tenderi=None):
    """Posalji email notifikaciju."""
    posiljalac = os.environ["EMAIL_POSILJALAC"]
    lozinka = os.environ["EMAIL_LOZINKA"]
    primalac = os.environ["EMAIL_PRIMALAC"]
    naziv_firme = os.environ.get("NAZIV_FIRME", "Green Step Company")
    slji_prazan = os.environ.get("SLJI_PRAZAN_IZVJESTAJ", "false").lower() == "true"

    ciljni = novi_tenderi if novi_tenderi is not None else tenderi

    if not ciljni and not slji_prazan:
        print("📭 Nema novih tendera — email nije poslan.")
        return False

    datum = datetime.now().strftime("%d.%m.%Y")
    hitnih = sum(1 for t in ciljni if t.hitnost() == "hitno")

    if hitnih > 0:
        subjekt = f"🔴 TenderGreen: {len(ciljni)} novih tendera ({hitnih} hitnih!) — {datum}"
    else:
        subjekt = f"🌿 TenderGreen: {len(ciljni)} novih tendera — {datum}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subjekt
    msg["From"] = f"TenderGreen <{posiljalac}>"
    msg["To"] = primalac

    html_sadrzaj = generiši_html(ciljni, naziv_firme)
    msg.attach(MIMEText(html_sadrzaj, "html", "utf-8"))

    try:
        print(f"📧 Šaljem email na {primalac}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(posiljalac, lozinka)
            server.sendmail(posiljalac, primalac, msg.as_string())
        print("✅ Email uspješno poslan!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Greška autentifikacije! Provjerite EMAIL_POSILJALAC i EMAIL_LOZINKA u GitHub Secrets.")
        raise
    except Exception as e:
        print(f"❌ Greška pri slanju emaila: {e}")
        raise


pošalji_email = posalji_email
