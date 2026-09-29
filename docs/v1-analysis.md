# Kildeanalyse og overføring til AI Coach v1

Gjennomgang 28.–29. september 2026. Formålet er en liten, etterprøvbar personlig
coach, ikke å kopiere autonome handelsbeslutninger til trening. Kildeomtale,
implementerte kontroller og dokumentert treningseffekt er tre forskjellige ting.

## Kodegjennomgang: hva kan overføres?

AI-Trader ble gjennomgått som referanse, uten kodeendringer eller kjøring av dens
testmiljø. Gjennomgangen omfattet README, arkitektur, forskningsstyring,
eksekveringsgrense, temporal audit, verifikasjon etter merge og utdrag av
champion/challenger-sammenligning. Dette er en målrettet arkitekturanalyse,
ikke en full sikkerhetsrevisjon av alle kjøreveier. Private implementasjonsdetaljer,
økonomiske resultater og kode er ikke kopiert til dette offentlige repoet.

Horsebett ble lest lokalt: oversikt, eligibility, point-in-time, replay,
manifest og v1-readiness. Ingen endringer eller tester ble kjørt i referanseprosjektet.

| Prinsipp | Implementert i coachen | Kontroll / gjenværende begrensning |
| --- | --- | --- |
| Én autoritet for konsekvensfulle handlinger | HQAuthority er eneste planwriter i normal appflyt | Egen kode, test for feil legitimasjon; lokal administrator kan endre programmet |
| Manglende bevis er ikke bestått | NO_EVIDENCE / INSUFFICIENT_EVIDENCE / INCOMPLETE | Tom replay gir ikke PASS; ufullstendig respons stopper progresjon |
| Frosset beslutningsgrunnlag | Importerte snapshots, hash og manifest på forslag | Ny evidens eller profil forelder forslag |
| Historisk korrekt evaluering | as_of og avvisning av fremtidsdata | Snapshot-tester beviser ikke at leverandørklokker er riktige |
| Replay og avstemming | Reberegning av lagret v0.1-evidens; forslag og HQ-plan er separate | Godkjenning betyr ikke at økten faktisk er gjennomført |
| Versjonsstyrt policy | Separat appversjon, motorversjon og coachpolicy | Regelendringer må testes og dokumenteres; ingen automatisk opprykking |
| Sporbar drift | Hashkoblet journal, revisjonslås, backupkontrollsum | Ingen ekstern forankring eller manipulasjonssikker lagring |
| Teknisk kvalitet vs faktisk effekt | Health skiller integritet/replay fra NOT_VALIDATED | Ingen påstand om bedre form eller færre skader fra grønne tester |

### Viktige vurderinger

En eksekveringsgrense må håndheve rettigheter ved selve skrivepunktet. Et flagg,
en advarsel eller en statusfil er ikke tilstrekkelig. Derfor er ikke et vellykket
preflight-resultat i et referanseprogram bevis for at coachens HQ-grense holder;
den har egne negative tester og separate godkjenningsruter.

Historisk replay må bruke det som var kjent på beslutningstidspunktet. V1 lagrer
rå import og evaluering sammen og lar senere data lage nye hendelser. Revisjons-
kontroll hindrer at et gammelt forslag blir godkjent etter endret respons. Dette
løser lokale revisjonskonflikter, men ikke feilaktige kildetidsstempler eller
forsinket ekstern synkronisering; de krever adapterkontroller i neste fase.

Champion/challenger er nyttig først når alternativene sammenlignes på samme
utøver, økttype, startgrunnlag og responshorisont. Ukjente utfall må telles som
ukjente og ha en synlig nevner. ROI, log-loss, tradinggrenser og bettingregler
har ingen direkte mening som treningsdose. V1 har derfor ingen automatisk
policykonkurranse, opprykk eller ML. Neste relevante steg er observasjon av
anbefaling -> HQ-beslutning -> faktisk utført -> tidsavgrenset respons.

## De ti artiklene

Artiklene brukes som produkt-/arkitekturreferanser, ikke som validert fysiologi.
Ingen markedsføringspåstand er gjort til en medisinsk eller prestasjonsmessig garanti.

| Kilde og tilgang | Relevant idé | Beslutning i v1 |
| --- | --- | --- |
| [two06: Building an AI fitness coach](https://medium.com/@two06/building-an-ai-fitness-coach-47c5bf4c0ead), lest | Koble historikk til dialog; aggregere treningsdata | Separat import og oppsummering. Ikke kopiert eksempelets håndtering av credentials/API-nøkler. Direkte enhetsintegrasjon utsatt. |
| [The Fit Futurist](https://www.thefitfuturist.com/en/training-analysis/create-training-plan-with-ai/), lest | Mål, livssituasjon, eksisterende plan og kritisk gjennomgang | Strukturert profil, mål og HQ-gjennomgang. Artikkelens sammenligninger og generelle uke-/hvileoppskrifter brukes ikke som forskningsbevis. |
| [IBM: AI personal trainer](https://www.ibm.com/think/tutorials/develop-ai-personal-trainer-with-llama-4-watsonx-ai), lest | Strukturert mellomformat mellom tolkning og plan | Kontrakter før råd, isolert språkmodell. Utstyrsgjenkjenning fra bilder og Llama/watsonx-stakk ikke nødvendig i lokal v1. |
| [Mercor: What is an AI trainer?](https://www.mercor.com/resources/experts/what-is-an-ai-trainer/), lest | Menneskelig evaluering og kvalitetskontroll | Regressionstester og eksplisitt vurdering. Artikkelen gjelder mennesker som trener AI, ikke en personlig treningstrener. |
| [Personal.ai Training Studio](https://www.personal.ai/ai-training-studio), lest | Strukturert minne og skilt kontekst | Én utøver per database og egne datalag. Ingen avhengighet av plattformen eller automatisk innlært helsefaglig ekspertise. |
| [freeCodeCamp: Real-time AI gym coach](https://www.freecodecamp.org/news/how-to-build-a-real-time-ai-gym-coach-with-vision-agents/), lest | Sanntidsfeedback og tilbakeholdenhet ved usikkerhet | Usikkerhet eksplisitt i råd. Pose-/kamerafunksjoner utsatt: tutorialen dokumenterer ikke biomekanisk sikkerhet. |
| [ASCN: Fitness automation](https://ascn.ai/blog-no-code/ai-personal-trainer-fitness-automation), lest | Separate analyse-/kommunikasjonsledd og rutineoppfølging | Lokale oppsummeringer og forslag. Påstander om overtreningsdeteksjon/automatisk optimalisering ikke overtatt. |
| [Creator Economy: Build your AI coach](https://creatoreconomy.so/p/full-tutorial-build-your-ai-coach-to-improve-your-health-and-fitness), kun offentlig forhåndsvisning | Profil, mål, hverdagskontekst og målinger | Strukturert oppfølging. Betalt resten av artikkelen er ikke lest; ingen kostholdsprotokoll implementert fra den. |
| [FITR: How to use AI as a personal trainer](https://www.coachwithfitr.com/blog/how-to-use-ai-as-a-personal-trainer), lest | Kontekst, tydelige begrensninger og coachens kontroll | Coachingstil, blokkerte økttyper og HQ. Kommersielt coach-støttemateriale, ikke dokumentasjon på treningseffekt. |
| [Men’s Health](https://www.menshealth.com/uk/fitness/a62947230/ai-personal-training-fitness/), utilgjengelig | Innhold ikke verifisert | Ingen funksjons- eller effektpåstand basert på denne artikkelen. Tidligere sammendrag ble ikke behandlet som originalkilde. |

Språklaget følger [OpenAI Responses-dokumentasjon](https://developers.openai.com/api/docs/guides/migrate-to-responses)
og [datakontroller](https://developers.openai.com/api/docs/guides/your-data): ingen
planverktøy, eksplisitt samtykke, minimal kontekst og lokal fallback. `store: false`
må ikke forveksles med en generell null-lagringsgaranti.

## Implementert, utsatt og forkastet

**Implementert:** norsk lokal oversikt, mål/målinger/referansemilepæler, profil og
rammer, ukeplan, innsjekk, regelstyrt motivasjon/dialog, forslag, separat HQ,
versjonert historikk, import, backup/replay, valgfritt språkmodell-lag.

**Utsatt:** én faktisk klokke-/treningsplattformadapter, automatisk 24/48-timers
oppfølging, varsler, bedre kalenderflytting, treningsbibliotek, målspesifikk
periodisering og sammenligning av policyer på reelle utfall. Krever eksplisitte
kontrakter, tilgang og evalueringsgrunnlag. Dette er ikke ferdige skjulte funksjoner.

**Forkastet for v1:** direkte LLM-skriving av plan, ML uten data, ukritisk kopiering
av trading-/bettingterskler, medisinske slutninger fra manglende data og
kamera-/ernæringsløfter uten validering. Måldatoer gir ingen garanti om fremgang.

## Neste beslutning

Bruk v1 med en faktisk HQ-plan og konsistente innsjekker først. Velg deretter én
integrasjon ut fra tilgjengelig API. Mål datadekning og feil før bedre automatikk.
En ferdig lokal v1 er et teknisk fundament; personlig effekt må undersøkes over tid.
