"""
TenderGreen - Scraper za ejn.gov.ba
Green Step Company | Sarajevo, BiH
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

CPV_KODOVI = {
    "77310000": "Sadnja i održavanje zelenih površina",
    "77300000": "Hortikulturne usluge",
    "45112710": "Uređenje zelenih površina",
    "77120000": "Usluge košenja",
    "77211500": "Usluge nadzora stabala",
    "77200000": "Šumarske usluge",
    "77211400": "Usluge sječe stabala",
    "77314000": "Usluge održavanja travnjaka",
    "77314100": "Usluge sijanja trave",
    "45112700": "Radovi na uređenju terena",
}

KLJUCNE_RIJECI = [
    "zelene površine",
    "zelene povrsine",
    "održavanje zelenih površina",
    "odrzavanje zelenih povrsina",
    "uređenje zelenih površina",
    "uredjenje zelenih povrsina",
    "javne zelene površine",
    "javne zelene povrsine",

    "hortikultura",
    "hortikulturne usluge",
    "hortikulturno",
    "pejzažno uređenje",
    "pejzazno uredjenje",
    "uređenje parka",
    "uredjenje parka",
    "parkovi",
    "travnjaci",
    "travnjak",

    "košenje trave",
    "kosenje trave",
    "košenje",
    "kosenje",
    "trimerisanje",
    "malčiranje",
    "malciranje",
    "krčenje",
    "krcenje",

    "sadnja bilja",
    "sadnja cvijeća",
    "sadnja cvijeca",
    "sadnice",
    "sadni materijal",
    "ukrasno bilje",
    "cvjetne površine",
    "cvjetne povrsine",
    "zeleni pojas",
    "drvoredi",

    "orezivanje",
    "obrezivanje",
    "obrezivanje stabala",
    "održavanje stabala",
    "odrzavanje stabala",
    "nadzor stabala",
    "sječa stabala",
    "sjeca stabala",

    "čišćenje javnih površina",
    "ciscenje javnih povrsina",
    "čišćenje",
    "ciscenje",
    "odvoz zelenog otpada",
    "zeleni otpad",
    "biljni otpad",

    "navodnjavanje",
    "zalijevanje",
    "rasvjeta",
    "vanjska rasvjeta",
    "uređenje terena",
    "uredjenje terena"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "bs-BA,bs;q=0.9,hr;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EJN_BASE = "https://ejn.gov.ba"
SEEN_FILE = "data/seen_tenders.json"
RESULTS_FILE = "data/last_results.json"


@dataclass
class Tender:
    id: str
    naslov: str
    narucilac: str
    cpv_kod: str
    cpv_opis: str
    vrijednost: str
    datum_objave: str
    rok_prijave: str
    url: str
    relevantnost: int
    razlozi: list = field(default_factory=list)

    def rok_za_n_dana(self):
        if not self.rok_prijave or self.rok_prijave == "—":
            return None
        for fmt in ("%d.%m.%Y", "%d.%m.%Y.", "%Y-%m-%d"):
            try:
                rok = datetime.strptime(self.rok_prijave.strip("."), fmt)
                return (rok - datetime.now()).days
            except ValueError:
                continue
        return None

    def hitnost(self):
        dana = self.rok_za_n_dana()
        if dana is None: return "nepoznato"
        if dana <= 3: return "hitno"
        if dana <= 7: return "uskoro"
        return "normalno"

    def to_dict(self):
        return {
            "id": self.id, "naslov": self.naslov, "narucilac": self.narucilac,
            "cpv_kod": self.cpv_kod, "cpv_opis": self.cpv_opis,
            "vrijednost": self.vrijednost, "datum_objave": self.datum_objave,
            "rok_prijave": self.rok_prijave, "url": self.url,
            "relevantnost": self.relevantnost, "razlozi": self.razlozi,
            "hitnost": self.hitnost(), "dana_ostalo": self.rok_za_n_dana(),
        }


def load_seen():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def save_results(tenderi):
    os.makedirs("data", exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump([t.to_dict() for t in tenderi], f, ensure_ascii=False, indent=2)


def izracunaj_relevantnost(naslov, cpv_kod):
    score = 0
    razlozi = []
    tekst = naslov.lower()
    if cpv_kod in CPV_KODOVI:
        score += 50
        razlozi.append(f"CPV {cpv_kod}: {CPV_KODOVI[cpv_kod]}")
    for kw in KLJUCNE_RIJECI:
        if kw.lower() in tekst:
            bonus = 15 if kw in ["zelene površine", "hortikultura", "košenje trave"] else 8
            score += bonus
            razlozi.append(f'Ključna riječ: "{kw}"')
    return min(score, 100), razlozi


def parse_tabela(soup, cpv_kod=""):
    rezultati = []
    tabela = (
        soup.find("table", {"id": re.compile(r"tblNabavke", re.I)})
        or soup.find("table", {"class": re.compile(r"table-nabavke", re.I)})
        or soup.find("table", {"class": re.compile(r"table", re.I)})
    )
    if not tabela:
        for link in soup.find_all("a", href=re.compile(r"/nabavka/")):
            href = link.get("href", "")
            id_match = re.search(r"id=(\d+)", href)
            if id_match:
                rezultati.append({
                    "id": id_match.group(1), "naslov": link.get_text(strip=True),
                    "narucilac": "", "datum_objave": datetime.now().strftime("%d.%m.%Y"),
                    "rok_prijave": "", "vrijednost": "", "cpv_kod": cpv_kod,
                    "url": urljoin(EJN_BASE, href),
                })
        return rezultati

    for red in tabela.find_all("tr")[1:]:
        kolone = red.find_all("td")
        if len(kolone) < 3: continue
        link = red.find("a", href=re.compile(r"/nabavka/"))
        href = link["href"] if link else ""
        url = urljoin(EJN_BASE, href) if href else EJN_BASE
        id_match = re.search(r"id=(\w+)", href)
        id_val = id_match.group(1) if id_match else (kolone[0].get_text(strip=True) if kolone else url)
        rezultati.append({
            "id": id_val, "naslov": kolone[1].get_text(strip=True) if len(kolone) > 1 else "",
            "narucilac": kolone[2].get_text(strip=True) if len(kolone) > 2 else "",
            "datum_objave": kolone[3].get_text(strip=True) if len(kolone) > 3 else "",
            "rok_prijave": kolone[4].get_text(strip=True) if len(kolone) > 4 else "",
            "vrijednost": kolone[5].get_text(strip=True) if len(kolone) > 5 else "",
            "cpv_kod": cpv_kod, "url": url,
        })
    return rezultati


def pretrazi_cpv(session, cpv_kod):
    params = {
        "vrstaPostupka": "", "statusNabavke": "1", "cpvKod": cpv_kod,
        "datumOd": (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y"),
        "datumDo": datetime.now().strftime("%d.%m.%Y"),
    }
    try:
        r = session.get(f"{EJN_BASE}/nabavka/pregled.html", params=params, timeout=30)
        r.raise_for_status()
        return parse_tabela(BeautifulSoup(r.text, "lxml"), cpv_kod)
    except Exception as e:
        print(f"  ⚠️  CPV {cpv_kod}: {e}")
        return []


def pretrazi_kljucnu_rijec(session, rijec):
    params = {
        "statusNabavke": "1", "predmetNabavke": rijec,
        "datumOd": (datetime.now() - timedelta(days=14)).strftime("%d.%m.%Y"),
        "datumDo": datetime.now().strftime("%d.%m.%Y"),
    }
    try:
        r = session.get(f"{EJN_BASE}/nabavka/pregled.html", params=params, timeout=30)
        r.raise_for_status()
        return parse_tabela(BeautifulSoup(r.text, "lxml"))
    except Exception as e:
        print(f"  ⚠️  '{rijec}': {e}")
        return []


def prikupi_tendere(min_relevantnost=30):
    print("🔍 Pokrenuta pretraga ejn.gov.ba...")
    session = requests.Session()
    session.headers.update(HEADERS)
    sirovi = {}

    print("  → CPV kodovi...")
    for cpv in CPV_KODOVI:
        for r in pretrazi_cpv(session, cpv):
            if r["id"] and r["id"] not in sirovi:
                sirovi[r["id"]] = r

    print("  → Ključne riječi...")
    for kw in KLJUCNE_RIJECI[:6]:
        for r in pretrazi_kljucnu_rijec(session, kw):
            if r["id"] and r["id"] not in sirovi:
                sirovi[r["id"]] = r

    print(f"  → Ukupno unikatnih: {len(sirovi)}")
    tenderi = []
    for raw in sirovi.values():
        score, razlozi = izracunaj_relevantnost(raw.get("naslov", ""), raw.get("cpv_kod", ""))
        if score >= min_relevantnost:
            tenderi.append(Tender(
                id=raw["id"], naslov=raw.get("naslov", "Bez naziva"),
                narucilac=raw.get("narucilac", "—"), cpv_kod=raw.get("cpv_kod", ""),
                cpv_opis=CPV_KODOVI.get(raw.get("cpv_kod", ""), ""),
                vrijednost=raw.get("vrijednost", "—"), datum_objave=raw.get("datum_objave", "—"),
                rok_prijave=raw.get("rok_prijave", "—"), url=raw.get("url", EJN_BASE),
                relevantnost=score, razlozi=razlozi,
            ))

    tenderi.sort(key=lambda x: x.relevantnost, reverse=True)
    print(f"✅ Relevantnih: {len(tenderi)}")
    return tenderi


def filtriraj_nove(tenderi, seen):
    return [t for t in tenderi if t.id not in seen]
