"""
TenderGreen - Monitor javnih nabavki
Green Step Company
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.scraper import (
    prikupi_tendere,
    filtriraj_nove,
    load_seen,
    save_seen,
    save_results,
)
from src.email_sender import posalji_email


def parse_vrijednost(vrijednost):
    """Pretvara vrijednost tipa '57,540 KM' u broj."""
    try:
        if not vrijednost:
            return 0
        tekst = str(vrijednost)
        tekst = tekst.replace("KM", "")
        tekst = tekst.replace(".", "")
        tekst = tekst.replace(",", "")
        tekst = tekst.strip()
        return int(tekst) if tekst.isdigit() else 0
    except Exception:
        return 0


def main():
    print("=" * 55)
    print("🌿 TenderGreen — Green Step Company")
    print("Monitor javnih nabavki | ejn.gov.ba")
    print("=" * 55)

    required = ["EMAIL_POSILJALAC", "EMAIL_LOZINKA", "EMAIL_PRIMALAC"]
    missing = [k for k in required if not os.environ.get(k)]

    if missing:
        print(f"\n❌ Nedostaju environment varijable: {', '.join(missing)}")
        print("Pokrenite: cp .env.example .env i popunite podatke")
        sys.exit(1)

    min_rel = int(os.environ.get("MIN_RELEVANTNOST", "30"))
    min_vrij = int(os.environ.get("MIN_VRIJEDNOST_KM", "0"))
    prikazi_sve = os.environ.get("PRIKAZI_SVE_AKTIVNE", "false").lower() == "true"

    print(f"\nMinimalna relevantnost: {min_rel}")
    print(f"Minimalna vrijednost: {min_vrij} KM")
    print(f"Prikaži sve aktivne tendere: {prikazi_sve}")

    svi_tenderi = prikupi_tendere(min_relevantnost=min_rel)

    if min_vrij > 0:
        svi_tenderi = [
            t for t in svi_tenderi
            if parse_vrijednost(getattr(t, "vrijednost", "")) >= min_vrij
        ]
        print(f"Filter vrijednosti ≥ {min_vrij} KM: {len(svi_tenderi)} tendera")

    seen = load_seen()

    if prikazi_sve:
        novi = svi_tenderi
        print(f"\n📋 Prikazujem SVE aktivne tendere: {len(novi)}")
    else:
        novi = filtriraj_nove(svi_tenderi, seen)
        print(f"\n🆕 Novih tendera ranije neviđenih: {len(novi)}")

    save_results(svi_tenderi)

    if novi or os.environ.get("SLJI_PRAZAN_IZVJESTAJ", "false").lower() == "true":
        posalji_email(svi_tenderi, novi_tenderi=novi)
    else:
        print("\n📭 Nema novih tendera za slanje emaila.")

    seen.update(t.id for t in svi_tenderi)
    save_seen(seen)

    print("\n✅ Završeno!")
    print("=" * 55)


if __name__ == "__main__":
    main()
