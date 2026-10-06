# Garmin uten Tredict — v1.5

Valgfri, uoffisiell lesekobling via python-garminconnect. Ingen Tredict- eller
betalt AI-API-avhengighet. Garmin kan endre innlogging/endepunkter; filimport er
fortsatt en planlagt reserve, ikke implementert. Ingen automatisk bakgrunnssynk,
søvn/HRV-import eller planwrites i denne leveransen.

## Windows

Garmin krever Python 3.12+. Den øvrige coachen støtter fortsatt 3.11.
Opprett et separat miljø med installert Python 3.12:

```powershell
py -3.12 -m venv .venv-garmin
.\.venv-garmin\Scripts\python -m pip install -e '.[garmin]'
.\Start-Garmin-Coach.ps1 -Login
.\Start-Garmin-Coach.ps1
```

Skriv Garmin-passord og eventuell engangskode i lokal terminal, aldri i chatten.
På denne utviklingsmaskinen er Python 3.12 og miljøet allerede installert.
Garmin-start bruker port 8767 for å unngå å kollidere med andre lokale tjenester.
Klikk «Synkroniser nå» i Garmin-kortet, eller kjør skriptet med `-Sync`.

## Data og grenser

Tilgangstoken lagres i `garmin-<databasenavn>` ved den private databasen, utenfor
repoet. Token er sensitivt og skal ikke deles. Coachen lagrer ikke passord i
journalen. Beskytt mappen med operativsystemets brukertilgang. Fjern tokenmappen
for å koble fra; allerede importerte data blir bevart. Demo bruker egen tokenmappe.

Første synk må være din ønskede konto. Senere kontobytte avvises; bruk separat
database for en annen utøver. Alle kall fra adapteren er login og get_activities;
coachen har ingen Garmin-skrivehandlinger. Provider-tokenet er ikke et offisielt
read-only scope: biblioteket som helhet har også skrivefunksjoner.

Full aktivitetshistorikk hentes i sider på 100, maksimalt 10 000 økter. Ugyldige,
fremtidige og dupliserte økter avvises. Siste fullstendige synk er aktiv visning;
originale svar lagres i separat journalhendelse. Synkfeil bevarer tidligere data.
Ingen blind automatisk retry ved innloggingsfeil eller ratebegrensning.

Garmin-historikken erstatter Tredict-aktivitetene i den aktive visningen, slik at
samme økt ikke dobbelttelles. Eldre råkilder bevares. HQ-plan og målkontekst
bevares, men deres opprinnelige importdato vises separat. Garmin-synk oppdaterer
ikke HQ-planen. Tredict-planens aktivitetslenker bekreftes ikke mot Garmin-ID-er.
Ingen dato/sport-match regnes som sikkert gjennomført plan.

Varighet fra Garmin er `duration`; forløpt tid er `elapsedDuration`. Manglende
målinger beholdes som ukjente. Garmin UTC-starttid tolkes eksplisitt som UTC.
Subjektiv kvalitet, smerte og restitusjon utledes ikke fra aktivitetsdata.
Innsjekk kan referere til `actual-garmin-<activityId>`. Ingen automatisk progresjon.

## Verifikasjon

Syntetiske adaptertester dekker sideskift, duplikater, tidsstempel, ukjente
målinger, kontoendring, feilbevaring, gjentatt synk, kildebytte og HQ-grensen.
Reell Garmin-innlogging og kontoimport må verifiseres lokalt av brukeren.
