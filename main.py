"""
TenderGreen - Glavna skripta
Pokrenite: python main.py
"""

import os
import sys
from dotenv import load_dotenv

# Učitaj .env fajl (za lokalno testiranje)
load_dotenv()

from src.scraper import prikupi_tendere, filtriraj_nove, load_seen, save_seen, save_results
from src.email_sender import posalji_email


def main():
    print("=" * 55)
    print("  🌿 TenderGreen — Green Step Company")
    print("  Monitor javnih nabavki | ejn.gov.ba")
    print("=" * 55)

    # Provjeri environment varijable
    required = ["EMAIL_POSILJALAC", "EMAIL_LOZINKA", "EMAIL_PRIMALAC"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"\n❌ Nedostaju environment varijable: {', '.join(missing)}")
        print("   Pokrenite: cp .env.example .env i popunite podatke")
        sys.exit(1)

    min_rel = int(os.environ.get("MIN_RELEVANTNOST", "30"))
    min_vrij = int(os.environ.get("MIN_VRIJEDNOST_KM", "0"))

    # Prikupi tendere
    svi_tenderi = prikupi_tendere(min_relevantnost=min_rel)

    # Filtriraj po vrijednosti
    if min_vrij > 0:
        svi_tenderi = [
            t for t in svi_tenderi
            if _parse_vrijednost(t.vrijednost) >= min_vrij
        ]
        print(f"   Filter vrijednosti ≥ {min_vrij} KM: {len(svi_tenderi)} tendera")

    # Filtriraj samo nove
    seen = load_seen()
    novi = filtriraj_nove(svi_tenderi, seen)
    print(f"\n📋 Novih tendera (ranije neviđenih): {len(novi)}")

    # Sačuvaj rezultate
    save_results(svi_tenderi)

    # Pošalji email
    if novi or os.environ.get("SLJI_PRAZAN_IZVJESTAJ", "false").lower() == "true":
        posalji_email(svi_tenderi, novi_tenderi=novi)

    # Ažuriraj listu viđenih
    seen.update(t.id for t in svi_tenderi)
    save_seen(seen)

    print("\n✅ Završeno!")
    print("=" * 55)


def _parse_vrijednost(v: str) -> float:
    """Pokušaj parsirati vrijednost tendera u broj."""
    if not v or v == "—":
        return 0
    import re
    brojevi = re.findall(r"[\d.,]+", v.replace(".", "").replace(",", "."))
    try:
        return float(brojevi[0]) if brojevi else 0
    except (ValueError, IndexError):
        return 0


if __name__ == "__main__":
    main()
