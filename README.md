# 🌿 TenderGreen — Monitor Javnih Nabavki

**Automatsko praćenje tendera za zelene površine i hortikulturne usluge u BiH**

> Green Step Company · ejn.gov.ba · Sarajevo

---

## 📋 Šta ovaj program radi?

TenderGreen automatski, svakih **3 sata**, pretražuje portal **ejn.gov.ba** i:

- ✅ Pronalazi tendere relevantne za vaše poslovanje (zelene površine, hortikultura, košenje...)
- ✅ Šalje vam **email** sa svim novim tenderima
- ✅ Prikazuje rok prijave, vrijednost i naručioca za svaki tender
- ✅ Označava hitne tendere (koji uskoro ističu)
- ✅ Radi **automatski, 24/7**, bez da vi išta radite

**Cijena: 0 KM** (GitHub Actions je besplatan za javne repozitorije)

---

## 🚀 POSTAVLJANJE — Korak po korak

### KORAK 1: Napravite GitHub nalog

1. Idite na **[github.com](https://github.com)**
2. Kliknite **"Sign up"**
3. Unesite email, lozinku i korisničko ime
4. Potvrdite email

---

### KORAK 2: Kreirajte novi repozitorij

1. Nakon prijave, kliknite zeleno dugme **"New"** (gore lijevo)
2. U polje **"Repository name"** upišite: `tendergreen`
3. Odaberite **"Public"** (obavezno — besplatni Actions rade samo za Public)
4. Kliknite **"Create repository"**

---

### KORAK 3: Uploadujte fajlove

#### Opcija A — Direktno kroz browser (najlakše):

1. U vašem novom repozitoriju kliknite **"uploading an existing file"**
2. Prevucite SVE fajlove iz `tender-monitor` foldera
3. Kliknite **"Commit changes"**

> ⚠️ **Važno:** Morate uploadovati i podfoldere `.github/workflows/` i `src/`
> GitHub ne podržava upload foldera direktno — koristite GitHub Desktop app (vidi Opciju B)

#### Opcija B — GitHub Desktop (preporučeno za foldere):

1. Preuzmite **[GitHub Desktop](https://desktop.github.com)**
2. Instalirajte i prijavite se sa vašim GitHub nalogom
3. Kliknite **File → Clone Repository** → odaberite `tendergreen`
4. Kopirajte sve fajlove iz `tender-monitor` foldera u klonirani folder
5. U GitHub Desktop kliknite **"Commit to main"**, zatim **"Push origin"**

---

### KORAK 4: Postavite Gmail za slanje emaila

> TenderGreen treba posebnu "App lozinku" za Gmail — **ne vašu pravu lozinku!**

1. Idite na **[myaccount.google.com](https://myaccount.google.com)**
2. Kliknite **"Sigurnost"** u lijevom meniju
3. Pod "Kako se prijavljujete u Google" kliknite **"Verifikacija u 2 koraka"**
4. Aktivirajte je (pratite upute)
5. Vratite se na stranicu Sigurnost
6. Potražite **"Lozinke za aplikacije"** (App passwords)
7. Odaberite:
   - Aplikacija: **Pošta (Mail)**
   - Uređaj: **Windows računar** (ili bilo što)
8. Kliknite **"Generiši"**
9. **ZAPIŠITE** 16-cifrenu lozinku koja se pojavi (npr. `abcd efgh ijkl mnop`)

---

### KORAK 5: Dodajte tajne varijable u GitHub

Ovo su vaši privatni podaci — GitHub ih čuva šifrovano.

1. Idite na vaš `tendergreen` repozitorij na GitHub
2. Kliknite **Settings** (zupčanik, gore desno)
3. U lijevom meniju kliknite **Secrets and variables → Actions**
4. Za svaki red ispod kliknite **"New repository secret"** i unesite:

| Name (Ime) | Secret (Vrijednost) |
|---|---|
| `EMAIL_POSILJALAC` | Vaša Gmail adresa (npr. `vaseime@gmail.com`) |
| `EMAIL_LOZINKA` | App lozinka iz Koraka 4 (npr. `abcd efgh ijkl mnop`) |
| `EMAIL_PRIMALAC` | Email na koji stižu notifikacije (može biti isti) |
| `NAZIV_FIRME` | `Green Step Company` |

> 💡 **Savjet:** `EMAIL_POSILJALAC` i `EMAIL_PRIMALAC` mogu biti isti Gmail

---

### KORAK 6: Pokrenite prvi put ručno

1. U vašem repozitoriju kliknite **"Actions"** tab (gornji meni)
2. Vidjet ćete "🌿 TenderGreen Monitor" u lijevom meniju — kliknite na njega
3. Kliknite **"Run workflow"** → **"Run workflow"**
4. Sačekajte 2-3 minute
5. Trebate primiti email sa prvim tenderima!

**Ako vidite zelenu kvačicu ✅ — sve radi!**
**Ako vidite crveni X ❌ — pogledajte Rješavanje problema ispod**

---

### KORAK 7: Gotovo! 🎉

Od sada, **svaka 3 sata**, GitHub automatski:
- Pretražuje ejn.gov.ba
- Šalje email ako ima novih tendera

---

## ⚙️ Podešavanja

### Promjena učestalosti provjere

Otvorite fajl `.github/workflows/tender-monitor.yml` i pronađite liniju:
```
- cron: "0 */3 * * *"
```

Primjeri:
- Svakih sat: `"0 * * * *"`
- Svakih 6 sati: `"0 */6 * * *"`
- Jednom dnevno u 7h: `"0 6 * * *"` *(UTC = 7h za Sarajevo ljeti)*

### Promjena minimalne relevantnosti

U GitHub → Settings → Actions → Variables dodajte:
- `MIN_RELEVANTNOST` = `50` (samo direktno relevantni tenderi)

### Dodavanje novih ključnih riječi

Otvorite `src/scraper.py` i dodajte u listu `KLJUCNE_RIJECI`.

---

## 🔧 Rješavanje problema

### ❌ "Authentication Error" u logu
→ App lozinka nije ispravno unesena. Ponovite Korak 4 i 5.

### ❌ Email ne stiže
→ Provjerite Spam folder. Dodajte pošiljaoca u kontakte.

### ❌ Workflow se ne pokreće
→ GitHub može kasniti do 15 minuta sa scheduled workflows.

### ❌ "ModuleNotFoundError"
→ Provjerite da ste uploadovali `requirements.txt`.

---

## 📁 Struktura projekta

```
tendergreen/
├── main.py                          # Glavna skripta
├── requirements.txt                 # Python paketi
├── .env.example                     # Primjer konfiguracije
├── .gitignore                       # Šta NE ide na GitHub
├── README.md                        # Ovo uputstvo
├── src/
│   ├── scraper.py                   # Preuzima tendere sa ejn.gov.ba
│   └── email_sender.py              # Šalje email notifikacije
└── .github/
    └── workflows/
        └── tender-monitor.yml       # GitHub Actions konfiguracija
```

---

## 🌿 CPV Kodovi koji se prate

| Kod | Opis |
|---|---|
| 77310000 | Sadnja i održavanje zelenih površina |
| 77300000 | Hortikulturne usluge |
| 45112710 | Uređenje zelenih površina |
| 77120000 | Usluge košenja |
| 77314000 | Usluge održavanja travnjaka |
| 77211500 | Usluge nadzora stabala |
| 45112700 | Radovi na uređenju terena |

---

## 📞 Podrška

Ako imate problema sa postavljanjem, otvorite **Issue** na GitHub repozitoriju.

---

*TenderGreen · Green Step Company · Sarajevo, BiH*
