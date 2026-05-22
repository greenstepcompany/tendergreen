"""
TenderGreen - Scraper za ejn.gov.ba
Green Step Company | Sarajevo, BiH
"""

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests


CPV_KODOVI = {
    "77300000": "Hortikulturne usluge",
    "77310000": "Usluge sadjenja i odrzavanja zelenih povrsina",
    "77311000": "Usluge odrzavanja ukrasnih parkova i perivoja",
    "77312000": "Usluge plijevljenja korova",
    "77313000": "Usluge odrzavanja parkova",
    "77314000": "Usluge odrzavanja terena",
    "77314100": "Usluge pokrivanja travom",
    "77315000": "Usluge sijanja",
    "77320000": "Usluge odrzavanja sportskih terena",
    "77330000": "Usluge u podrucju floristike",
    "77340000": "Usluge obrezivanja drveca i sisanja zivice",
    "77200000": "Sumarske usluge",
    "77211400": "Usluge sjece drveca",
    "77211500": "Usluge odrzavanja drveca",
    "45112700": "Radovi uredjenja pejzaza",
    "45112710": "Radovi pejzaznog uredjenja zelenih povrsina",
    "45112711": "Radovi pejzaznog uredjenja parkova",
    "45112712": "Radovi pejzaznog uredjenja vrtova",
    "16311000": "Kosilice za travnjake",
    "16311100": "Kosilice za travnjake, parkove ili sportske terene",
}

KLJUCNE_RIJECI = [
    "zelene površine",
    "održavanje zelenih površina",
    "uređenje zelenih površina",
    "hortikultura",
    "hortikulturno",
    "košenje",
    "košenje trave",
    "sadnja",
    "sadnja bilja",
    "sadnice",
    "uređenje dvorišta",
    "uređenje parka",
    "travnjak",
    "zelenilo",
    "pejzažno uređenje",
    "parkovi",
    "drveće",
    "grmlje",
    "cvjetne površine",
    "zeleni pojas",
    "vrtlarstvo",
    "sadni materijal",
]

HEADERS = {
    "User-Agent": "TenderGreen/1.0 (+https://github.com)",
    "Accept-Language": "bs-BA,bs;q=0.9,hr;q=0.8,en;q=0.7",
    "Accept": "application/json,text/html;q=0.8,*/*;q=0.7",
}

OPEN_DATA_BASE = "https://open.ejn.gov.ba"
NEXT_PORTAL_BASE = "https://next.ejn.gov.ba"
PROCEDURE_CALLS_URL = (
    f"{NEXT_PORTAL_BASE}/bs-latn-ba/announcements/procedure-calls"
    "?page=1&rows=10&searchByIsLatestVersion=True"
)
SEEN_FILE = "data/seen_tenders.json"
RESULTS_FILE = "data/last_results.json"
REQUEST_TIMEOUT = 30
MAX_CPV_LINKS = int(os.environ.get("MAX_CPV_LINKS", "80"))
MAX_KEYWORD_RESULTS = int(os.environ.get("MAX_KEYWORD_RESULTS", "30"))
MAX_ACTIVE_SCAN = int(os.environ.get("MAX_ACTIVE_SCAN", "200"))
MAX_PROCEDURE_CALL_AGE_DAYS = int(os.environ.get("MAX_PROCEDURE_CALL_AGE_DAYS", "60"))
SAMO_SARAJEVO = True
SARAJEVO_LOKACIJE = [
    "Sarajevo",
    "Ilidža",
    "Novi Grad",
    "Novo Sarajevo",
    "Centar",
    "Vogošća",
    "Hadžići",
    "Ilijaš",
    "Trnovo",
]


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
        for fmt in ("%d.%m.%Y", "%d.%m.%Y.", "%Y-%m-%d", "%d.%m.%Y %H:%M"):
            try:
                rok = datetime.strptime(self.rok_prijave.strip("."), fmt)
                return (rok - datetime.now()).days
            except ValueError:
                continue
        return None

    def hitnost(self):
        dana = self.rok_za_n_dana()
        if dana is None:
            return "nepoznato"
        if dana <= 3:
            return "hitno"
        if dana <= 7:
            return "uskoro"
        return "normalno"

    def to_dict(self):
        return {
            "id": self.id,
            "naslov": self.naslov,
            "narucilac": self.narucilac,
            "cpv_kod": self.cpv_kod,
            "cpv_opis": self.cpv_opis,
            "vrijednost": self.vrijednost,
            "datum_objave": self.datum_objave,
            "rok_prijave": self.rok_prijave,
            "url": self.url,
            "relevantnost": self.relevantnost,
            "razlozi": self.razlozi,
            "hitnost": self.hitnost(),
            "dana_ostalo": self.rok_za_n_dana(),
        }


def load_seen():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


def save_results(tenderi):
    os.makedirs("data", exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump([t.to_dict() for t in tenderi], f, ensure_ascii=False, indent=2)


def izracunaj_relevantnost(naslov, cpv_kod="", cpv_opis=""):
    score = 0
    razlozi = []
    cpv_key = normalizuj_cpv(cpv_kod)
    tekst = normalizuj_tekst(f"{naslov} {cpv_opis}")

    if cpv_key in CPV_KODOVI:
        score += 50
        razlozi.append(f"CPV {cpv_key}: {CPV_KODOVI[cpv_key]}")

    for kw in KLJUCNE_RIJECI:
        if normalizuj_tekst(kw) in tekst:
            bonus = 15 if kw in {
                "zelene površine",
                "održavanje zelenih površina",
                "uređenje zelenih površina",
                "hortikultura",
                "košenje",
                "košenje trave",
            } else 8
            score += bonus
            razlozi.append(f'Ključna riječ: "{kw}"')

    return min(score, 100), razlozi


def pretrazi_cpv(session, cpv_kod):
    cpv_redovi = _nadji_cpv_redove(session, cpv_kod)
    if not cpv_redovi:
        print(f"  ⚠️  CPV {cpv_kod}: nije pronađen u Open Data šifrarniku")
        return []

    rezultati = []
    for cpv in cpv_redovi:
        cpv_id = cpv.get("Id")
        if not cpv_id:
            continue

        links = _odata_get(
            session,
            "LotCpvCodeLinks",
            {
                "$filter": f"CpvCodeId eq {cpv_id}",
                "$orderby": "LastUpdated desc",
                "$top": str(MAX_CPV_LINKS),
            },
        )
        lot_ids = [link.get("LotId") for link in links if link.get("LotId")]

        for lot in _ucitaj_lotove(session, lot_ids):
            if not _aktivan_red(lot):
                continue
            rezultati.append(_mapiraj_odata_red(lot, cpv.get("Code"), cpv.get("Description")))

    return rezultati


def pretrazi_kljucnu_rijec(session, rijec):
    keyword = rijec.lower()
    now = _odata_datetime(datetime.now(timezone.utc))
    filter_keyword = _odata_string(keyword)

    notice_filter = (
        f"ApplicationDeadlineDateTime ge {now} "
        f"and contains(tolower(ProcedureName),{filter_keyword})"
    )
    notice_rows = _odata_get(
        session,
        "ProcurementNotices",
        {
            "$filter": notice_filter,
            "$orderby": "Announced desc",
            "$top": str(MAX_KEYWORD_RESULTS),
        },
    )

    lot_filter = (
        f"ApplicationDeadlineDateTime ge {now} and "
        f"(contains(tolower(ProcedureName),{filter_keyword}) "
        f"or contains(tolower(Name),{filter_keyword}) "
        f"or contains(tolower(ShortDescription),{filter_keyword}))"
    )
    lot_rows = _odata_get(
        session,
        "Lots",
        {
            "$filter": lot_filter,
            "$orderby": "LastUpdated desc",
            "$top": str(MAX_KEYWORD_RESULTS),
        },
    )

    return [
        _mapiraj_odata_red(row)
        for row in notice_rows + lot_rows
        if _aktivan_red(row)
    ]


def prikupi_tendere(min_relevantnost=30):
    print("🔍 Pokrenuta pretraga open.ejn.gov.ba...")
    session = requests.Session()
    session.headers.update(HEADERS)
    sirovi = {}

    print("  → CPV kodovi...")
    for cpv in CPV_KODOVI:
        for red in pretrazi_cpv(session, cpv):
            _dodaj_sirovi(sirovi, red)

    print("  → Ključne riječi...")
    for kw in KLJUCNE_RIJECI:
        for red in pretrazi_kljucnu_rijec(session, kw):
            _dodaj_sirovi(sirovi, red)
        for red in pretrazi_pozive_po_kljucnoj_rijeci(session, kw):
            _dodaj_sirovi(sirovi, red)

    print("  → Najnovije aktivne objave...")
    for red in pretrazi_najnovije_aktivne(session):
        _dodaj_sirovi(sirovi, red)

    print(f"  → Ukupno unikatnih: {len(sirovi)}")
    tenderi = []
    preskoceno_rok = 0
    preskoceno_lokacija = 0
    for raw in sirovi.values():
        if not _ima_buduci_rok(raw):
            preskoceno_rok += 1
            continue
        if SAMO_SARAJEVO and not _u_sarajevu(raw):
            preskoceno_lokacija += 1
            continue

        score, razlozi = izracunaj_relevantnost(
            raw.get("naslov", ""),
            raw.get("cpv_kod", ""),
            raw.get("cpv_opis", ""),
        )
        if score >= min_relevantnost:
            tenderi.append(Tender(
                id=raw["id"],
                naslov=raw.get("naslov", "Bez naziva"),
                narucilac=raw.get("narucilac", "—"),
                cpv_kod=raw.get("cpv_kod", ""),
                cpv_opis=raw.get("cpv_opis", ""),
                vrijednost=raw.get("vrijednost", "—"),
                datum_objave=raw.get("datum_objave", "—"),
                rok_prijave=raw.get("rok_prijave", "—"),
                url=raw.get("url", NEXT_PORTAL_BASE),
                relevantnost=score,
                razlozi=razlozi,
            ))

    tenderi.sort(key=lambda x: x.relevantnost, reverse=True)
    if preskoceno_rok:
        print(f"  → Preskočeno bez budućeg roka: {preskoceno_rok}")
    if SAMO_SARAJEVO and preskoceno_lokacija:
        print(f"  → Preskočeno van Kantona Sarajevo: {preskoceno_lokacija}")
    print(f"✅ Relevantnih: {len(tenderi)}")
    return tenderi


def pretrazi_najnovije_aktivne(session):
    now = _odata_datetime(datetime.now(timezone.utc))
    rows = _odata_get(
        session,
        "ProcurementNotices",
        {
            "$filter": f"ApplicationDeadlineDateTime ge {now}",
            "$orderby": "Announced desc",
            "$top": str(MAX_ACTIVE_SCAN),
        },
    )

    rezultati = []
    for row in rows:
        tekst = normalizuj_tekst(" ".join([
            str(row.get("ProcedureName") or ""),
            str(row.get("AdditionalInformation") or ""),
            str(row.get("TechnicalAbility") or ""),
        ]))
        if any(normalizuj_tekst(kw) in tekst for kw in KLJUCNE_RIJECI):
            rezultati.append(_mapiraj_odata_red(row))
    return rezultati


def pretrazi_pozive_po_kljucnoj_rijeci(session, rijec):
    cutoff = _odata_datetime(
        datetime.now(timezone.utc) - timedelta(days=MAX_PROCEDURE_CALL_AGE_DAYS)
    )
    filter_expr = (
        "IsLatestVersion eq true "
        f"and Announced ge {cutoff} "
        f"and contains(tolower(ProcedureName),{_odata_string(rijec.lower())})"
    )
    rows = _odata_get(
        session,
        "AnnouncementProcedureCalls",
        {
            "$filter": filter_expr,
            "$orderby": "Announced desc",
            "$top": str(MAX_KEYWORD_RESULTS),
        },
    )
    return [_mapiraj_odata_red(row) for row in rows if _aktivan_red(row)]


def filtriraj_nove(tenderi, seen):
    return [t for t in tenderi if t.id not in seen]


def _odata_get(session, collection, params=None):
    url = f"{OPEN_DATA_BASE}/{collection}"
    try:
        response = session.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            print(f"  ⚠️  Open Data endpoint nije pronađen: {response.url}")
            return []
        response.raise_for_status()
        data = response.json()
        return data.get("value", [])
    except requests.HTTPError as exc:
        print(f"  ⚠️  HTTP greška za {collection}: {exc}")
    except requests.RequestException as exc:
        print(f"  ⚠️  Greška pri pozivu {collection}: {exc}")
    except ValueError as exc:
        print(f"  ⚠️  Neispravan JSON odgovor za {collection}: {exc}")
    return []


def _nadji_cpv_redove(session, cpv_kod):
    cpv_prefix = normalizuj_cpv(cpv_kod)
    return _odata_get(
        session,
        "CpvCodes",
        {
            "$filter": f"startswith(Code,{_odata_string(cpv_prefix)})",
            "$top": "5",
        },
    )


def _ucitaj_lotove(session, lot_ids):
    lotovi = []
    for chunk in _chunked(lot_ids, 20):
        filter_expr = " or ".join(f"Id eq {lot_id}" for lot_id in chunk)
        lotovi.extend(_odata_get(
            session,
            "Lots",
            {
                "$filter": filter_expr,
                "$top": str(len(chunk)),
            },
        ))
    return lotovi


def _mapiraj_odata_red(row, cpv_kod="", cpv_opis=""):
    procedure_id = row.get("ProcedureId") or row.get("Id")
    tender_id = str(procedure_id or row.get("Id") or row.get("Number") or "")

    procedure_name = _clean_text(row.get("ProcedureName") or row.get("NpsProcurementName") or "")
    lot_name = _clean_text(row.get("Name") or "")
    naslov = procedure_name or lot_name or "Bez naziva"
    if lot_name and procedure_name and lot_name not in procedure_name:
        naslov = f"{procedure_name} - {lot_name}"

    deadline = (
        row.get("ApplicationDeadlineDateTime")
        or row.get("ProcurementPhaseOfferSubmissionDeadline")
        or row.get("IntermediatePhaseOfferSubmissionDeadline")
    )
    announced = row.get("Announced") or row.get("LastUpdated")
    value = row.get("EstimatedValue")
    lokacija = _clean_text(" ".join([
        str(row.get("Location") or ""),
        str(row.get("ContractingAuthorityCityName") or ""),
        str(row.get("ContractingAuthorityAdministrativeUnitName") or ""),
        str(row.get("AdditionalInformationCityName") or ""),
        str(row.get("OfferDeliveryCityName") or ""),
        str(row.get("DocumentationTakeOverCityName") or ""),
    ]))

    return {
        "id": tender_id,
        "naslov": naslov,
        "narucilac": _clean_text(row.get("ContractingAuthorityName") or "—"),
        "lokacija": lokacija,
        "cpv_kod": cpv_kod or "",
        "cpv_opis": cpv_opis or "",
        "vrijednost": _format_money(value),
        "datum_objave": _format_date(announced),
        "rok_prijave": _format_date(deadline),
        "rok_prijave_dt": deadline,
        "url": _announcement_url(row.get("Id")) if row.get("IsLatestVersion") is not None else _portal_url(procedure_id),
    }


def _dodaj_sirovi(sirovi, red):
    tender_id = red.get("id")
    if not tender_id:
        return

    postojeci = sirovi.get(tender_id)
    if not postojeci:
        sirovi[tender_id] = red
        return

    if red.get("cpv_kod") and not postojeci.get("cpv_kod"):
        postojeci.update({
            "cpv_kod": red.get("cpv_kod", ""),
            "cpv_opis": red.get("cpv_opis", ""),
        })
    if postojeci.get("vrijednost") == "—" and red.get("vrijednost") != "—":
        postojeci["vrijednost"] = red["vrijednost"]


def _aktivan_red(row):
    deadline = (
        _parse_datetime(row.get("ApplicationDeadlineDateTime"))
        or _parse_datetime(row.get("ProcurementPhaseOfferSubmissionDeadline"))
        or _parse_datetime(row.get("IntermediatePhaseOfferSubmissionDeadline"))
    )
    return bool(deadline and deadline > datetime.now(timezone.utc))


def _ima_buduci_rok(raw):
    deadline = _parse_datetime(raw.get("rok_prijave_dt"))
    if not deadline:
        deadline = _parse_lokalni_datum(raw.get("rok_prijave"))
    return bool(deadline and deadline > datetime.now(timezone.utc))


def _u_sarajevu(raw):
    tekst = normalizuj_tekst(" ".join([
        raw.get("naslov", ""),
        raw.get("narucilac", ""),
        raw.get("lokacija", ""),
    ]))
    return any(normalizuj_tekst(lokacija) in tekst for lokacija in SARAJEVO_LOKACIJE)


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_lokalni_datum(value):
    if not value or str(value).strip().lower() in {"—", "-", "nepoznat", "none"}:
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%Y.", "%Y-%m-%d", "%d.%m.%Y %H:%M"):
        try:
            parsed = datetime.strptime(str(value).strip("."), fmt)
            if fmt in ("%d.%m.%Y", "%d.%m.%Y.", "%Y-%m-%d"):
                parsed = parsed.replace(hour=23, minute=59, second=59)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _format_date(value):
    parsed = _parse_datetime(value)
    if not parsed:
        return "—"
    return parsed.strftime("%d.%m.%Y")


def _format_money(value):
    if value in (None, ""):
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted} KM"


def _announcement_url(announcement_id):
    if not announcement_id:
        return PROCEDURE_CALLS_URL
    return f"{NEXT_PORTAL_BASE}/bs-latn-ba/announcements/{announcement_id}/overview"


def _portal_url(procedure_id):
    if not procedure_id:
        return PROCEDURE_CALLS_URL
    return f"{NEXT_PORTAL_BASE}/procurement-notices/{procedure_id}/overview"


def _odata_datetime(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def _odata_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def normalizuj_cpv(cpv_kod):
    match = re.search(r"\d{8}", str(cpv_kod or ""))
    return match.group(0) if match else ""


def normalizuj_tekst(text):
    text = str(text or "").lower().translate(_CYRILLIC_TO_LATIN)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def _clean_text(value):
    return " ".join(str(value or "").split())


def _chunked(items: Iterable, size: int):
    items = list(dict.fromkeys(items))
    for index in range(0, len(items), size):
        yield items[index:index + size]


_CYRILLIC_TO_LATIN = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "dj",
    "е": "e", "ж": "z", "з": "z", "и": "i", "ј": "j", "к": "k",
    "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "ћ": "c", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "c", "џ": "dz", "ш": "s",
})
