# AI Coach / Treningsmotor — v1

Lokal treningscoach med mål, målbare milepæler, øktregistrering, ukesoppsummering,
motivasjon og forklarte endringsforslag. **HQ er eneste planautoritet.**
Motoren og trenerdialogen kan aldri skrive planen gjennom appens arbeidsflyt.

## Start

Python 3.11 eller nyere. Fra prosjektmappen i PowerShell:

```powershell
.\Start-Coach.ps1 -Demo
```

Alternativt:

```sh
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
ai-coach-app --demo --open
```

Demoen bruker syntetiske data i `~/.ai-coach/demo.sqlite`. For egen profil:
`ai-coach-app --open`, som bruker `~/.ai-coach/coach.sqlite`.
Terminalen viser privat oppstartslenke og separat HQ-kode. Hold begge private.
Appen kjører bare på `127.0.0.1`. Stopp med Ctrl+C. Ikke bruk offentlig tunnel.

## Bruk

1. Registrer profil, tilgjengelige dager/tid, foretrukne og blokkerte økttyper.
2. Sett mål med utgangspunkt, ønsket verdi, enhet og dato. Registrer faktiske målinger.
3. Lag et ukeforslag, eller importer en HQ-plan etter `app_plan.schema.json`.
4. Se hele forslaget. HQ godkjenner med egen kode. Før det er planen uendret.
5. Registrer gjennomføring, anstrengelse, kvalitet, smerte og restitusjon.
6. Be coachen om neste økt, mål eller ukesoppsummering.

Milepæler er lineære referansepunkter, ikke prognoser. Enkel innsjekk erstatter ikke
24/48-timers respons. Progresjon krever også sammenlignbar detaljert evidens via
`evaluation_request.schema.json`. Manglende data betyr ukjent, aldri friskmeldt.
Ny uke viderefører godkjent struktur uten automatisk doseøkning. Smerte blokkerer
ordinær forslagsgodkjenning og krever særskilt HQ-vurdering.

Eksport og sikkerhetskopi finnes under innstillinger. Eksport inneholder private
opplysninger og skal ikke i GitHub. SQLite-backup med kontrollsum ligger under
`backups/` ved databasen. Gjenoppretting: stopp appen, behold eksisterende database,
og start med `ai-coach-app --db <kopi-av-backupfil>`.

## Valgfri språkmodell

Lokal trenerdialog fungerer uten API-nøkkel. Valgfri OpenAI-formulering krever
`OPENAI_API_KEY` og `AI_COACH_MODEL` i miljøet før oppstart og samtykke i dialogen.
Ingen modell velges automatisk. Spørsmålet og et lokalt faktasvar sendes til OpenAI;
disse kan inneholde personopplysninger. Hele journalen sendes ikke. `store: false`
er ikke alene en garanti om null leverandørlagring. API-bruk kan koste penger.
Ved feil brukes lokalt svar. Språkmodellen har ingen planverktøy eller HQ-rettigheter.

## Leveranse og begrensninger

- Lokal app med persistente data, måloppfølging, innsjekk og HQ-godkjente forslag.
- Motor: KEEP, PROGRESS, CONSOLIDATE, REDUCE, MOVE, AVOID_COMBINATION og INSUFFICIENT_EVIDENCE.
- Separate kildefakta, utøverdata, avledede trekk og anbefalinger; historikk og replay.
- Ingen ML-trening, automatisk policyopprykk, klokkesynkronisering, videocoaching,
  flerbrukerdrift eller ekstern HQ-integrasjon.
- Regler er tekniske utgangsverdier. Treningseffekt og medisinsk sikkerhet er ikke
  validert. Utstyr og begrensningsfritekst gir HQ kontekst, ikke automatisk klinisk tilpasning.

## Utvikling

```sh
python -m scripts.generate_schemas
python -m scripts.generate_fixtures
python -m unittest discover -s tests -t . -v
ai-coach examples/synthetic_progress.json --audit history.sqlite
```

Samlet pakkeversjon er 1.3.0. Motorens algoritmeversjon er 0.1.0; samlet taksonomi er 1.1. Replay sammenligner også versjonsmetadata. Historikk fra eldre pakker må replayes med opprinnelig kodeversjon for identisk resultat. Schemas ligger i
`schemas/`, syntetiske fixtures i `tests/fixtures/`. CI kjører Windows og Ubuntu.

Se [v1-arkitektur](v1-architecture.md), [kilde- og overføringsanalyse](v1-analysis.md),
[opprinnelig arkitektur](architecture.md), [HQ-kontrakt](hq-contract.md),
[motorpolicy](policy.md), [taksonomi](taxonomy.md) og [repo-audit](repo-audit.md).

Denne lokale appen er levert sammen med eksisterende v1.2-moduler. Den bruker ikke automatisk deres experience-/profilstore eller en ekstern Tredict-runtime. Se repoets README for de separate kommandoene.
