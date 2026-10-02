# Personlig oppstart og kildeimport — v1.4

Appen kan nå bruke en privat, datert Tredict-import sammen med bekreftede mål,
arbeidsrammer og HQ-kontekst. Demo og personlige data har separate databaser.

## Kildelag

`onboarding.py` tar inn connectorens originale CSV-svar og bevarer dem i
SOURCE_SNAPSHOT-hendelsen. Normaliserte aktiviteter og planoppføringer lagres
separat. Ukes-/månedsvisning er en avledet projeksjon; anbefalinger fabrikeres ikke.
CSV kan inneholde siterte flerslinjenotater. Flere sider kan samles under `pages`.
Duplikat-ID, feil format, fremtidige aktiviteter, feil utøver og manipulerte
projeksjoner avvises. Identisk snapshot er idempotent.

Bare eksplisitt `executedTrainingId` fra kilden gir en bekreftet plan–aktivitetslenke.
Dato/sport-likhet er ikke tilstrekkelig. Historiske planoppføringer kan være utdaterte;
importen beviser ikke at alle historiske avlysninger/flyttinger er representert.

Aktiv tid følger `summary.duration`, forløpt tid følger `summary.durationTotal`.
Begge vises. Manglende målinger telles eksplisitt. Lange hikes, klatring og transport
inkluderes etter kildens sport/subsport. Randuker er delvise. Manuelle kommentarer
om lengre faktisk time-on-feet blir bevart i råkilden, uten å overskrive enhetsmålingen.
Måneds- og ukesummer er beskrivelser, aldri automatiske treningsmål eller bevis på toleranse.

## Flytende tilgjengelighet og mål

Profilens ukes- og øktbudsjett kan være null når et fast tidsbudsjett ikke er avtalt.
Det betyr ikke null tilgjengelig tid. Arbeidsvinduer, gjentakende ankere og alternativer
kan dokumenteres i `athlete_context.availability`, med kildehenvisning.
Forslag som krever et numerisk budsjett stoppes til en konkret planleggingsramme finnes.

Langsiktige eller betingede mål kan ligge i kildesnapshotets `athlete_context.goals`.
Manglende baseline og konkurransedato forblir null. Visningen beregner ikke en falsk
fremgangsprosent. Et kvantifisert mål med faktisk baseline kan fortsatt registreres
via det ordinære målskjemaet. Progresjonsramme og eksplisitte hviledatoer lagres med
HQ-kildehenvisninger. En kalender som er tom på en dato uten slik bekreftelse blir
ikke automatisk tolket som hvile.

## Import og bruk

Kildesnapshotet bygges med `build_snapshot(...)`: athlete_id, originale source_facts,
athlete_context, collected_at, historie- og planvindu og tidssone. De originale
aktivitetene og planene kommer fra connectoren; mål og rammer må komme fra bekreftet
utøver-/HQ-kontekst. Ikke endre projections manuelt for å få importen gjennom.

```sh
ai-coach-onboard --db <privat-database.sqlite> --snapshot <privat-snapshot.json>
ai-coach-app --db <privat-database.sqlite> --open
```

Importer også via «Importer kildesnapshot» i appen. API-ruten `/api/source-import`
krever app-token og forventet revisjon. Innsjekker kan vise til en importert
planoppføring eller faktisk aktivitet (`actual-<activityId>`); ukjent respons blir
ikke automatisk utfylt. Eksporter og ta backup fra innstillingene.

Importen oppretter ingen HQ_PLAN og gjør ingen eksterne writes. Den eksisterende
HQ/Tredict-planen vises som lesekopi. Appen lager ikke et nytt startutkast oppå denne
kalenderen. Endring av faktisk plan går gjennom den eksisterende HQ-autoriteten.

## Personvern og status

Privat profil, originale kilder og journal oppbevares utenfor det offentlige repoet.
Snapshot kan inneholde posisjon, notater og andre personopplysninger. Publiser bare
importkoden og syntetiske tester. Datert import er ikke kontinuerlig synk; appen
merker snapshot eldre enn ett døgn som utdatert. Health viser antall source_snapshots
separat fra replay av motorevidens. Subjektiv respons og 24–72-timers oppfølging må
registreres, ikke utledes fra registrert treningstid alene.

V1.4 er testet for import, idempotens, råkilde/projeksjon, tidsgrenser, HQ-grense,
flytende kapasitet, innsjekk og HTTP-tilgang. De private dataene kontrolleres lokalt;
de publiseres ikke som test-fixtures.
