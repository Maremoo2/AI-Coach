# V1-arkitektur

## Ansvar og dataflyt

Kildefakta -> validerte utøverdata -> avledede trekk -> v0.1-anbefaling.
Profil + innsjekk + mål + eksisterende HQ-plan + anbefaling -> forslag -> HQ -> ny planversjon.

`service.py` håndterer profil, mål, innsjekk, import og forslag. `coaching.py` er ren
beregning. Bare `hq.py` skriver HQ_PLAN i appens normale arbeidsflyt. `language.py`
formulerer allerede beregnede svar uten planverktøy. Dette er lokal ansvarsdeling,
ikke en sikkerhetsgrense mot administratoren som kan endre kode og database.

`app_contracts.py` definerer profil, mål, ukeplan og innsjekk. Planned/actual/response
beholder v0.1-kontraktene. Innsjekk fabrikerer aldri downstream-respons, pulsdrift
eller 24/48-timers restitusjon. Original import lagres separat fra evalueringen.
Journalen skiller PROFILE, GOAL, CHECKIN, IMPORT, EVALUATION, PROPOSAL, HQ_PLAN og
HQ_DECISION. Projeksjoner bygges fra hendelsene; anbefalinger er aldri kildefakta.

## HQ og historikk

Alle endringer krever forventet revisjon kontrollert i SQLite-transaksjonen.
HQ krever separat kode, ventende forslag, uendret datagrunnlag/planversjon,
samme policy/manifest, alder høyst sju dager og ingen blokkeringer. Endrede data
forelder tidligere forslag. Historiske, fullførte og låste økter endres ikke av
forslagsmotoren. Eksplisitt HQ-import kan importere historikk og er separat fra råd.

Manifestet binder forslaget til utvalgt domenekode og schemas med SHA-256. Det er
ikke en full programvaresignatur eller klinisk validering. Journalen har hashkjede
og SQLite-triggere mot endring. Lokal administrator kan likevel omskrive databasen
eller fjerne halen. Eksternt oppbevarte backupkontrollsummer styrker etterprøvbarhet.

## Policy coach-1.0.0

Startutkast bruker foretrukket rolig løp, aerob sykkel eller svømmeteknikk, høyst
30 minutter per økt og innen tidsbudsjett. HQ må vurdere utkastet. Ny uke kopierer
godkjent struktur/dose uten automatisk økning.

Økning i eksisterende uke krever PROGRESS fra siste sju dager, identisk kontinuerlig
rolig dose/økttype/intensitet, ingen intervaller eller volumkonflikt, fersk komplett
innsjekk og ingen smerte-/restitusjonsflagg. Økning er avrundet 5 %, minst ett og
høyst fem minutter, én økt per økttype per forslag. Ny dose matcher ikke samme gamle
evidens. Dårlig restitusjon foreslår 20 % reduksjon for rolige økter. Andre økter
krever HQ-vurdering. Smerte blokkerer vanlig godkjenning. Manglende RPE, kvalitet,
smerte eller ukjent restitusjon stopper progresjon.

Planen må holde tidsbudsjett, tilgjengelige dager og blokkerte økttyper. V1 tillater
ikke flere økter samme dag eller HARD på nabodager. Dette er konservative tekniske
policyvalg, ikke universelle forskningsbaserte treningsgrenser. Fritekstbegrensninger
tolkes ikke automatisk. MOVE/AVOID_COMBINATION krever HQ, uten automatisk flytting.

## Drift og personvern

Én utøver per database, egen demo. Loopback, app-token, separat HQ-kode, Host/Origin-
kontroll, CSP og JSON-grense på 2 MB. Ingen flerbrukerautentisering, databasekryptering
eller ekstern sikkerhetsrevisjon. Ingen hemmeligheter eller utøverdata skal i Git.
Språkmodell krever samtykke, får spørsmål/lokalt svar og kan fortsatt formulere feil.
Integrasjonen er testet med simulerte svar, ikke betalt produksjonsforespørsel.

## Kontroll og videre arbeid

Tester dekker motortilstander, ukjente/fremtidige data, identitet, HQ-grense, foreldede
forslag, låsing, budsjett, samtidighet, backup/replay, HTTP-tilgang og språkfallback.
Health viser NO_EVIDENCE uten importer, ikke PASS for tomt grunnlag. Ingen test beviser
treningseffekt. Mål, innsjekk, dialog og godkjenning kontrolleres også i nettleseren.

Oktoberforslag: uke 1 faktisk profil/mål og manuell historikk; uke 2 én tilgjengelig
integrasjon; uke 3 kalender- og responsoppfølging; uke 4 prøvebruk og utfallsevaluering.
Dette er foreløpig planlegging, ikke automatisk bestilling eller bindende frist.
