# Trading Bot — Direttiva Astra per il sistema di sviluppo della prossima generazione

Data: 27 settembre 2026  
Autorità del documento: decisione strategica e specifica di indirizzo richiesta dall’Owner; da recepire nel repository prima dell’implementazione.  
Repository esaminato: `C-Gian/trading-bot`, commit `aac8dad0eb3b9af04e1cdc5898b640554e80674a`.  
Base documentale: missione, stato corrente, task, ADR-0050/0051, registry/inventory/methodology e lettura integrale dei venti dossier canonici LIB-001–LIB-020. Ho studiato i dossier, non riletto i venti originali. Le limitazioni degli originali registrate nei dossier restano vincolanti.

## 1. Decisione strategica

**La prossima allocazione deve costruire un sistema completo e verificabile di sviluppo del trader, con apprendimento iterativo limitato su dati esposti. Non deve essere un altro tentativo isolato cui chiedere subito di dimostrare un edge.**

Scelgo un’architettura gerarchica per ruoli informativi, con una previsione continua, una policy selettiva e un motore di rischio/esecuzione separato. Il sistema deve rendere osservabile il proprio ragionamento quantitativo e conservare ogni previsione, compresi i casi in cui non opera.

La sequenza è:

**contratti e causalità → prototipo completo → development con revisioni motivate → freeze → valutazione protetta → stress predefiniti → eventuale paper futuro.**

Correggo esplicitamente il limite del mio precedente indirizzo: la chiusura di G1 protegge la conclusione su G1; non deve diventare il divieto generale di apprendere progettando un successore. La precisazione dell’Owner cambia il mandato di allocazione. La knowledge base rende più solida l’architettura, ma non dimostra che essa guadagnerà.

Quattro decisioni sono definitive per questo indirizzo:

1. **G1 rimane fallita e chiusa.** Nessuna soglia, uscita o lettura retroattiva ne cambia l’esito; nessuna riapertura di Phase B come suo salvataggio.
2. **Il nuovo programma è `G2_DEVELOPMENT_SYSTEM`, non una strategia validata.** Il suo primo successo consiste nel produrre osservazioni, previsioni, decisioni e autopsie corrette e riproducibili.
3. **La ricerca può imparare dai dati di sviluppo.** Ogni cambiamento consuma budget di ricerca; il risultato resta development, anche quando è molto positivo.
4. **Non basta costruire bene per avere un vantaggio.** La selettività e la disciplina sono capacità del prodotto; l’edge dopo costi resta una domanda empirica.

Questo documento non ha modificato il repository né avviato backtest, raccolta prospettica o ordini. Nello stato canonico osservato G2 è ancora `UNALLOCATED`, l’allocazione di mercato è zero, Champion e strategia validata sono assenti. Il prossimo work package recepisce il nuovo mandato senza fingere che questi flag siano già cambiati.

## 2. Cosa cambia davvero dopo lo studio

La convergenza più utile delle fonti riguarda l’organizzazione del problema, non una ricetta di indicatori.

- **Carver e Chan** sostengono modularità, semplicità, costi, coerenza tra ricerca e operatività e una ricerca delimitata. Carver dà ragioni per combinare poche previsioni omogenee e per diffidare di pesi scelti sulla performance rumorosa. Non assegna pesi universali a trend, volatilità, cicli e liquidità.
- **Ilmanen e il gruppo di studi sul trend** distinguono fenomeni, orizzonti e contesti. Trend e momentum meritano un ruolo, ma molte loro rappresentazioni sono trasformazioni della medesima storia dei prezzi. L’evidenza tradizionale prevalentemente mensile e diversificata non convalida il nostro orizzonte BTC di quattro ore.
- **Harris e la parte disponibile di Johnson** rendono indispensabile separare informazione, opportunità, rischio ed esecuzione. Il costo della liquidità e l’incertezza del fill possono rendere razionale non operare anche con una buona view.
- **Hull** aiuta a separare pricing, carry, volatilità, rischio e previsione: un premio del future o del perpetual non è una probabilità rialzista.
- **López de Prado, DSR, factor zoo e PBO** impongono causalità e contabilità della selezione. Non dimostrano che sia vietato sviluppare; dimostrano che lo sviluppo adattivo non produce da solo conferma indipendente.
- **Le interviste di Market Wizards** suggeriscono processi e differenze tra trader, non una regola universale. La selezione dei sopravvissuti impedisce di trasformare quei racconti in prove causali.

Non tratto questi gruppi come venti conferme. LIB-010/011/015 appartengono alla stessa linea TSMOM; LIB-006–009 condividono autori, idee o universi con quella letteratura; LIB-017 è il supplemento di LIB-018; LIB-012/013/017/018 hanno relazioni metodologiche e autoriali. LIB-014 e LIB-015 sono brevi summary AQR, non i paper completi. I dataset non sono nuove repliche indipendenti.

Le tensioni vanno mantenute: il trend può soffrire whipsaw senza essere logicamente confutato, ma questo non autorizza a ignorare perdite o costi; una metodologia severa può ridurre falsi positivi e aumentare falsi negativi; PBO può diagnosticare la selezione senza certificare profitti o causalità. Nessuna singola metrica risolve queste tensioni.

## 3. Professional trader knowledge model

Non voglio un LLM che improvvisi una narrazione di mercato a ogni candela. Il runtime deve essere numerico, deterministico e versionato. L’AI può aiutare lo sviluppo e spiegare record già prodotti; non può introdurre una regola nascosta o modificare un peso durante la decisione.

Ogni famiglia ha una **knowledge card** con questi campi:

| Campo | Contenuto obbligatorio |
|---|---|
| Identità e ruolo | Che cosa osserva; direction, timing, context, risk o execution |
| Meccanismo ipotizzato | Perché potrebbe aiutare e in quali condizioni potrebbe fallire |
| Evidenza | Fonte, tipo di evidenza, mercato/orizzonte, limiti di trasferibilità |
| Osservabili | Formula, unità, dati necessari, timestamp e disponibilità |
| Dipendenze | Prezzo/volume/dati condivisi con altre famiglie; rischio di doppio conteggio |
| Collegamenti consentiti | Quali uscite può influenzare e quali no |
| Stato epistemico | Descrittivo, ipotesi, development, frozen, valutato o non disponibile |
| Invalidità | Staleness, warm-up, campione insufficiente, drift, failure del metodo |
| Diagnostica | Che risultato o ablation può mettere in discussione il suo ruolo |

Il modello di conoscenza distingue quattro livelli: **osservazione**, **interpretazione ipotetica**, **stima previsionale**, **azione**. Per esempio, “taker imbalance positivo” è un’osservazione; “pressione compratrice assorbita” è un’interpretazione che richiede evidenza aggiuntiva; “rendimento atteso positivo” è una stima; “LONG ora” è una decisione di portafoglio. Nessuna freccia fra questi livelli è automatica.

### Famiglie scelte

| Famiglia | Ruolo primario | Rappresentazione V1 | Interazione consentita | Cosa non deve fare |
|---|---|---|---|---|
| **1. Struttura e trend/momentum** | Direzione, persistenza, posizione del prezzo | Una sola famiglia di filtri causali su poche scale; distanza/estensione rispetto alla struttura locale | Fornisce il contesto in cui leggere partecipazione e timing | EMA, MACD e RSI come tre voti indipendenti |
| **2. Partecipazione e risposta al flow** | Conferma o contraddizione condizionale | Volume relativo; aggressor imbalance quando disponibile; risposta del prezzo osservata | Trend × partecipazione; flow × risposta del prezzo | “Più volume = bullish”, “buy imbalance = LONG” |
| **3. Volatilità e rischio di percorso** | Scala della distribuzione, regime, dimensionamento | Volatilità realizzata causale su due velocità, range/estensione, stato di stress | Allarga la distribuzione e modifica esposizione/actionability | Votare rialzo o ribasso soltanto perché la volatilità cresce |
| **4. Stato temporale/ciclico** | Timing e contesto multiscala | Fase/stabilità/qualità soltanto dopo il checkpoint specifico | Può modificare l’attrattività di un ingresso nella direzione del contesto | Invertire da solo la view lenta; obbligare tutti i cicli a concordare |
| **5. Liquidità ed esecuzione** | Costo, fattibilità, veto operativo | Spread/quote se osservati; proxy e scenari dichiarati nello storico a barre | Determina costi, scadenza dell’ordine, eventuale rinuncia | Confondere alto volume con profondità o riempimenti garantiti |
| **6. Contesto del contratto/derivati** | Costo e rischio del veicolo | Funding dovuto, specifiche, mark/index e basis solo se disponibili causalmente | Costo della posizione e controlli sul contratto | Usare funding/OI come segnale direzionale senza prova del ruolo |

Le ultime due famiglie non sono altri due motori alpha. Le variabili possono essere mostrate senza essere ammesse nella previsione. La UI deve distinguere **osservato**, **usato dal modello**, **sperimentale** e **non disponibile**.

Restano fuori dal primo motore: news/NLP, sentiment sociale, on-chain, universo intermarket, value BTC senza ancora difendibile, options skew, mappe di liquidazioni ricostruite e volume profile come ulteriore famiglia alpha. Non servono per costruire il primo sistema completo. Un’eventuale estensione deve risolvere una domanda concreta, non riempire una dashboard.

### Trend e momentum

Sono una famiglia, articolata per scala. Scelgo un filtro causale esponenziale per descrivere direzione e distanza normalizzata; non una gara tra EMA, RSI, MACD, regressioni e Kalman. Le lunghezze effettive, il ritardo e la normalizzazione saranno fissati nel contratto prima di osservare nuovi risultati economici. Il principio è sostenuto da LIB-008; la scelta ingegneristica del filtro non è una scoperta alpha.

“Struttura rialzista ma prezzo esteso” è uno stato lecito: la direzione attesa può restare positiva mentre l’ingresso è sfavorevole. I livelli strutturali sono soltanto estremi già confermati o range già conclusi. Un pivot che richiede due barre future diventa disponibile dopo quelle due barre, senza retrodatazione sul grafico operativo.

### Volume, flow e liquidità

Il volume misura attività, non intenzione né liquidità eseguibile. La partecipazione relativa viene confrontata con una baseline causale; non si aggiungono contemporaneamente tre normalizzazioni dello stesso volume.

Il flow è sempre letto insieme alla risposta del prezzo. Molti acquisti aggressivi con scarso progresso possono essere compatibili con assorbimento, ma anche con altre cause. L’etichetta corretta è **“pressione buy con risposta debole”**, non “venditore istituzionale nascosto identificato”. Non inferiamo inventario, identità, liquidazioni o ordini futuri dai soli OHLCV.

Una relazione flow/prezzo può essere usata come termine condizionale del modello; non le imponiamo a priori un segno bullish. Senza aggressor data verificati il blocco è assente e il modello previsto per quel contratto dati resta esplicitamente ridotto. Non si riempie il buco con zero, che significherebbe un flow equilibrato osservato.

### Derivati

Per LONG/SHORT simmetrici nello storico scelgo come riferimento di ricerca un singolo contratto lineare BTCUSDT perpetual, coerente con gli asset di G1, con esposizione nozionale simulata limitata. È un modello di ricerca del veicolo, non una decisione di usare leva o un’autorizzazione a un conto reale.

Funding entra anzitutto nei costi. La stima ex ante usa solo quanto annunciato/conoscibile; il P&L ex post usa il pagamento effettivamente maturato. OI non distingue da solo nuovi long da nuovi short. Basis e perp/spot possono descrivere dislocazioni, ma LIB-002/014/019 non ne provano il contenuto direzionale crypto. **OI, liquidazioni e basis come alpha restano fuori dalla V1**; non blocchiamo il sistema per procurarne storici fragili.

## 4. Scelta del modello di interazione e giudizio sui pesi

**Adotto importanza strutturale stabile, non pesi direzionali professionali inventati.** Una famiglia può essere indispensabile nel suo ruolo e avere coefficiente nullo nella media prevista. Il rischio non deve perdere autorità perché un backtest “preferisce” ignorarlo.

Il modello “peso base positivo × piccolo correttivo empirico” applicato a tutte le famiglie ha tre difetti: somma quantità non omogenee; impone significato direzionale a variabili di rischio; può impedire ai dati di spegnere un effetto inesistente. Carver è pertinente per combinare previsioni comparabili, non per convertire ogni stato in un voto.

Scelgo quindi:

1. **Grafo stabile dei ruoli**, con collegamenti ammessi e vietati.
2. **Un piccolo modello trasparente della distribuzione futura**, regolarizzato e aggiornato secondo una procedura fissa.
3. **Un modello separato dell’utilità dell’ingresso**, legato a un contratto di trade preciso.
4. **Risk governor indipendente**, con limiti non ottimizzabili.

La prima versione ha al massimo **sei osservabili numerici e due interazioni** nel readout predittivo: struttura locale, struttura di contesto, estensione del prezzo, partecipazione relativa, imbalance verificato, stato della volatilità. Le due interazioni previste sono struttura locale × partecipazione e imbalance × risposta del prezzo. Quest’ultima risposta deve essere una trasformazione esplicita delle osservazioni già disponibili; non un classificatore aggiuntivo nascosto. Il daily/weekly resta contesto visibile, non altri coefficienti mascherati.

La classe iniziale è una **regressione lineare regolarizzata della location del rendimento normalizzato**, con scala della volatilità stimata separatamente e distribuzione residua empirica prequenziale. Niente selezione automatica di feature, alberi, mixture di regimi o catalogo di modelli. Coefficienti alpha ristretti verso zero; nessun obbligo che volume o trend abbiano un coefficiente positivo. Le interazioni sono più penalizzate dei termini principali. Formula di scaling, penalità e limiti numerici vanno scelti una volta nel prossimo WP usando unità, stabilità e fixture sintetiche; non con una ricerca sul profitto.

Questa regressione **non è presentata come un nuovo edge rispetto alle regressioni già chiuse nel progetto**: la lineage dovrà esplicitare ciò che si riusa e ciò che cambia nel contratto completo. Il nuovo oggetto è il sistema osservabile e sviluppabile; cambiare nome a un modello non azzera l’evidenza precedente.

La frequenza di refit è mensile UTC; usa soltanto etichette mature e una finestra passata di massimo due anni. I limiti e la procedura si congelano prima del replay economico. Un refit previsto dal contratto è adattamento del modello, non una nuova invenzione; cambiare finestra, penalità o procedura dopo averne visto l’effetto è una revisione di ricerca.

Nessun “regime” latente addestrato nella V1: regime significa descrizione causale di direzionalità, volatilità e condizioni di esecuzione. Conflitto multiscala non impone neutralità. Viene conservato, può ridurre l’utilità dell’ingresso e deve comparire nelle diagnostiche.

### Esempio del ragionamento desiderato

Struttura 4h rialzista, struttura locale in rallentamento, ciclo breve discendente affidabile, prezzo esteso: la view a quattro ore può restare rialzista. Il motore d’ingresso può stimare che il percorso probabile renda troppo costoso entrare adesso e produrre `NO_TRADE`. Il ciclo non genera automaticamente SHORT. Se il ciclo non è affidabile, il motivo deve dire “timing ciclico indeterminato”, non usarlo come veto invisibile.

Viceversa, struttura rialzista e pressione buy con scarso avanzamento non autorizzano da soli uno short contrarian: sono una contraddizione da valutare, non un ordine.

## 5. Gerarchia temporale e checkpoint cicli

| Scala | Funzione congelata |
|---|---|
| **1 minuto** | Dato grezzo, aggregazione, simulazione di entry/stop/exit; supporto al contesto veloce |
| **15 minuti** | Un decision point per candela completata; una previsione e una decisione salvate |
| **1 ora** | Struttura locale, estensione e timing |
| **4 ore** | Contesto direzionale principale; orizzonte primario della previsione |
| **Daily UTC** | Contesto lento, volatilità e struttura; nessun veto universale |
| **Weekly UTC** | Sfondo lento e stato temporale, aggiornato soltanto a settimana conclusa |

Non scegliamo la scala che vince un backtest. Una sola previsione primaria a quattro ore evita di selezionare ex post l’horizon migliore; le altre scale descrivono lo stato. Previsioni multi-horizon distinte richiederebbero nuovi target, score e budget: non sono necessarie alla V1.

La griglia di campionamento non coincide con il periodo di un ciclo. Per osservare un’oscillazione di 40–45 minuti non basta un segnale calcolato esclusivamente su barre di un’ora. Il modulo ciclico riceve dati alla risoluzione appropriata e pubblica lo stato al decision point di 15 minuti.

**Gap preciso:** i dossier non fondano un estimatore di fase ciclica multiscala, causale e stabile agli estremi del campione. Manca la giustificazione per collegare fase stimata e timing, non il permesso di costruire il resto del sistema.

**Checkpoint `CYCLE-CAUSALITY-01`, massimo due giornate di lavoro:**

1. Ispezionare il solo metodo già disponibile nel progetto, comprese la sua lineage e le ragioni di invalidità. Se non esiste un metodo utilizzabile, scegliere una sola costruzione causale di riferimento da una fonte metodologica primaria. Nessun confronto economico tra algoritmi.
2. Richiedere all’output fase, ampiezza, stabilità del periodo, qualità della stima, ritardo e stato `UNRELIABLE`; una fase senza questi campi non è un segnale utilizzabile.
3. Fissare bande nominali rappresentative intorno a 45m, 3h, 1d, 4d, 1w, 4w; periodi più lenti solo descrittivi se il warm-up li sostiene. Non sono costanti naturali del BTC né una griglia da ottimizzare.
4. Verificare su rumore, sinusoidi con rumore, trend senza ciclo, frequenza variabile e salti: niente futuro, stabilità per prefissi, ritardo dichiarato, capacità di astenersi quando la fase non ha senso. Non chiedere di riconoscere perfettamente un ciclo che il segnale non identifica.
5. Congelare un solo contratto oppure dichiararlo `CYCLE_UNAVAILABLE` con la ragione tecnica precisa.

Il superamento dimostra correttezza dell’estimatore, **non utilità predittiva**. Nella baseline i cicli sono visibili e in shadow; una delle quattro revisioni di development è riservata al loro contributo al timing. L’inserimento può usare al massimo due termini ciclici nel readout della policy, sostituendo termini esistenti o restando nel tetto totale di otto; non apre sei nuovi voti direzionali. Il confronto riguarda qualità degli ingressi, selettività e utilità condizionale, non profitto del “ciclo da solo”. Se il metodo non passa, il posto riservato non viene riempito con un altro indicatore e il pannello espone il limite.

## 6. Contratto forecast

Ogni candela 15m eleggibile produce un record immutabile. Eleggibile significa dati minimi, timestamp e warm-up validi. Anche una candela non eleggibile produce un record di astensione con motivo: niente omissioni silenziose.

Il target primario è il log-rendimento del prezzo del medesimo strumento tra il close decisionale e il close quattro ore dopo. È un target di mercato lordo, separato dal rendimento di un trade eseguibile.

| Uscita | Significato |
|---|---|
| Location/media e mediana | Movimento centrale stimato a quattro ore, in rendimento e prezzo |
| Quantili | Intervallo predittivo, inizialmente 10/50/90; include incertezza del mercato |
| Probabilità del segno | Integrale della distribuzione stimata; sempre accompagnata dallo stato di calibrazione |
| Scala | Volatilità prevista/approssimata sull’horizon e suo metodo |
| Forza della view | Magnitudine normalizzata, distinta dalla qualità dell’evidenza |
| Evidence status | Supporto storico, errore del modello, drift, dati mancanti, calibrazione |
| Contributi | Termini del modello e interazioni, più eventuali conflitti multiscala |

La distribuzione empirica usa errori di previsioni generate causalmente nel passato, non residui in-sample scelti dopo il risultato. Nella fase iniziale senza sufficiente archivio prequenziale si emette una baseline distribuzionale causale e si marca la stima condizionale `UNVALIDATED`; il sistema può dire “informazione direzionale debole” anziché simulare precisione.

**Probability, uncertainty e conviction non sono sinonimi.** La probabilità riguarda un evento definito, per esempio rendimento positivo a quattro ore. L’incertezza aleatoria è la larghezza della distribuzione futura; quella epistemica riguarda stima, campione, specificazione e condizioni fuori supporto. La conviction è un’etichetta di forza della view, non una percentuale di successo e non il numero di indicatori concordi.

Mostrare “67%” perché un punteggio vale 0,67 è vietato. Una probabilità prodotta da un modello può essere conservata e sottoposta a scoring prima di essere validata, ma la UI deve chiamarla **stima non ancora calibrata** finché il controllo prequenziale non la sostiene. Non si può chiamare “calibrata” perché deriva matematicamente da una CDF.

La UI presenta separatamente forza e affidabilità: può esistere una view forte con evidenza debole. Soglie delle etichette weak/moderate/strong si fissano prima del replay; non si spostano per far apparire bello il gruppo “strong”. Nessun dimensionamento aggressivo deriva dall’etichetta.

## 7. Contratto decisionale: dalla view all’ingresso

La policy confronta tre azioni: LONG, SHORT, NO_TRADE. Non traduce direttamente il segno della previsione in posizione.

**Errore da evitare:** una distribuzione del prezzo finale non determina il valore di un trade con stop. Due percorsi con lo stesso close a quattro ore possono avere stop-out e costi opposti. Perciò non useremo la probabilità di rialzo come probabilità di successo dello stop/target.

Scelgo una sola geometria iniziale di trade, simmetrica tra LONG e SHORT:

- ingresso market simulato al primo evento 1m ammissibile dopo decisione e latenza;
- stop di protezione a distanza di due ATR(14) di barre 1h completate, calcolata al decision point e ancorata all’entry eseguita;
- nessun take-profit fisso né trailing stop nella baseline;
- uscita temporale a quattro ore dal decision point, con liquidazione al primo evento ammissibile;
- scadenza dell’intento prima della successiva decision candle; se l’esecuzione arriva troppo tardi si annulla;
- una posizione aperta al massimo, nessun pyramiding, nessun flip o re-entry sulla stessa candela;
- mentre una posizione è aperta, la previsione continua; il campo d’azione resta `NO_TRADE` con motivo `POSITION_ALREADY_OPEN`, affiancato allo stato di gestione HOLD/EXIT.

Due ATR e quattro ore sono **convenzioni iniziali di ingegneria e rischio**, non parametri derivati dai libri o dichiarati ottimali. Non vengono cercati su griglie. Questa è una geometria nuova da dichiarare nella lineage; non il ritorno a P1/P2 con soglie modificate. Eventuali cambiamenti successivi contano come revisione di policy completa.

Per valutare l’ingresso servono etichette di payoff che rispettino questa geometria. Per ogni decision point eleggibile calcoliamo, quando il futuro è maturato, il risultato di due trade shadow standardizzati, uno per lato, con entry, stop, costi ed expiry identici a quelli della policy. Sono etichette di ricerca, non trades reali né posizioni simultaneamente fattibili.

Un secondo readout piccolo e regolarizzato stima il payoff netto condizionale di ciascuna azione, usando lo stesso dizionario limitato e lo stato dell’ingresso. Nessun catalogo di stop o modelli. La sua incertezza viene stimata su errori prequenziali raggruppati per tempo, senza trattare le etichette sovrapposte come indipendenti.

La regola seleziona un lato solo se il suo margine prudente di utilità netta è positivo rispetto a NO_TRADE e l’azione è compatibile con rischio e dati. Se entrambe le stime sono positive, sceglie quella con il margine prudente maggiore; parità o supporto insufficiente portano a NO_TRADE. Il metodo del margine e il livello di prudenza vengono fissati nel contratto, non regolati per raggiungere un numero desiderato di trade. La view primaria rimane un input e un riferimento di coerenza: una decisione opposta deve essere spiegata dal payoff di percorso, non da un override nascosto.

Prima di avere un readout di payoff stimabile, il prodotto emette previsioni e decisioni `NO_TRADE / INSUFFICIENT_POLICY_EVIDENCE`. Una policy di confronto semplice permette comunque di verificare il motore di esecuzione. Questo evita di inventare un’aspettativa economica dai soli quantili finali.

Il piano contiene: decision ID, lato, tipo ordine, riferimento d’ingresso, timestamp minimo/massimo, entry effettiva separata, stop, exit temporale, rischio in valuta e percentuale, nozionale, ipotesi di costo, forecast ID e motivi di accettazione/rifiuto. Un ordine fallito non viene riscritto come NO_TRADE deciso in origine.

### Risk governor

Per la simulazione iniziale propongo 0,25% dell’equity a rischio fino allo stop, nozionale massimo 1× equity e stop dell’operatività simulata al 5% di drawdown del percorso. Se i limiti canonici applicabili sono più restrittivi, valgono quelli. Il prossimo WP deve recepire numeri coerenti in un unico contratto, senza alterarli sulla base dei risultati.

Il rischio effettivo può superare quello previsto in presenza di gap e slippage. Lo stop non è una garanzia. La violazione di un limite è una violazione anche se il trade guadagna. Il rischio non si amplia dopo una serie vincente.

Quando il limite di percorso scatta, la policy economica si ferma e lo stop resta nel risultato. Le previsioni possono continuare; eventuali shadow diagnostici successivi sono separati e non vengono ricuciti nell’equity come se il limite non fosse intervenuto. Nel development lo stop genera diagnosi e può motivare una revisione; non cancella automaticamente il programma né autorizza a spostare la soglia.

## 8. Dati V1 e execution realism sufficiente

| Dato | Necessità e uso |
|---|---|
| OHLCV 1m del contratto scelto | Indispensabile; aggregazioni causali e percorsi di esecuzione |
| Quote volume e taker-buy volume, con semantica verificata | Necessari al blocco partecipazione/flow previsto; altrimenti contratto ridotto esplicito |
| Funding con tempi di annuncio, applicazione e segno | Indispensabile se il veicolo simulato lo addebita; forecast del costo distinto da costo realizzato |
| Specifiche del contratto, tick/lot/minimi e fee assumptions | Indispensabili al modello operativo; versione storica quando disponibile |
| Quote bid/ask e timestamp di ricezione | Indispensabili per misurare esecuzione futura; nello storico assente usare scenari dichiarati |
| Mark/index | Richiesti se usati per trigger, margin o confronto; non sostituiscono silenziosamente il last |
| Order book L2/L3, queue, OI, liquidazioni, options | Non necessari al primo replay; niente ricostruzione fantasiosa dai candle |

Ogni osservazione conserva `event_time`, `available_at`, eventuale `received_at`, sorgente, unità e qualità. Gli archivi storici raramente dimostrano il momento reale di ricezione: il backtest dichiara una convenzione conservativa di disponibilità, verificabile successivamente nel paper. I dati mancanti non vengono forward-filled oltre la tolleranza del contratto; i missing critici fermano l’azione.

Tutte le risoluzioni derivano dallo stesso grezzo e da calendari UTC documentati. Al tempo t si possono usare solo barre concluse e disponibili. Il loader applica i limiti della fase **prima dell’I/O**: leggere un intero funding file futuro per poi filtrarlo nel motore non è più accettabile. Manifest con hash, intervallo autorizzato e intervallo effettivamente letto obbligatori.

Il primo simulatore è **bar-based e market-only**. Include fee di entrata/uscita, spread/slippage, latenza, funding, arrotondamenti, gap e invalidità dei dati. Non include una coda passiva inventata. Se in futuro si vogliono limit order, serviranno un nuovo contratto e dati adeguati: un touch del low/high non prova un fill.

Per uno stop attraversato da un gap si usa il primo prezzo plausibilmente eseguibile peggiore, non il livello ideale dello stop. Se entry e stop potrebbero avvenire nella stessa barra e la sequenza non è identificabile, si applica una convenzione sfavorevole fissata prima del run e si riporta il numero di casi ambigui. La size deve rispettare un limite conservativo rispetto al volume disponibile; il volume non dimostra la profondità, quindi tale limite è un’approssimazione, non una prova di capacità.

**Non dichiaro fee o slippage correnti senza verifica.** Il precedente scenario di costo può essere riusato come stress di confronto con la sua etichetta, non promosso a verità sul mercato attuale. Prima del replay il checkpoint microstructure congela un caso base e stress a 1,5× e 2× la componente spread/slippage, oltre a ritardo aggiuntivo e scenari di gap/outage. Non si sceglie lo scenario che fa sopravvivere il candidato.

La sofisticazione necessaria è quella che può cambiare la conclusione per la size e l’horizon scelti. Se una stima modesta dell’edge sparisce con una piccola variazione dei costi, bisogna riconoscere la fragilità, non costruire un exchange simulator enorme per cercare il risultato favorevole.

## 9. Replay e prodotto

Il motore di stato, forecast, policy e rischio deve essere lo stesso in replay e in modalità futura. Cambiano gli adapter del tempo e dell’esecuzione, non le regole. Il backend può avere i dati del futuro in un archivio separato, ma il motore che decide riceve solo il prefisso disponibile.

**Home:** grafico BTC, stato aggiornamento/sorgente, matrice timeframe, sei famiglie con ruolo e disponibilità, forecast a quattro ore con intervallo e qualità dell’evidenza, conflitti, piano LONG/SHORT/NO_TRADE e reason code. Il prezzo può aggiornarsi più spesso; la previsione ufficiale cambia solo al decision point. Evitare un “confidence gauge” che somma concetti diversi.

**Replay:** scelta di un intervallo consentito, avanzamento passo-passo o accelerato, forecast sopra la candela, decisione sotto, click sullo snapshot completo. In modalità causale il grafico termina a t e non rivela la correttezza prima della maturazione del target. In modalità analisi, chiaramente distinta, si possono vedere outcome e autopsie. Muovere il cursore non deve ricalcolare la storia con il modello più recente.

**Registro:** ogni previsione ha un ID, hash di stato/modello/dati, intervallo di training e ultima etichetta ammessa, output, motivi, decisione collegata e stato di maturazione. Gli outcome si aggiungono come eventi successivi; non modificano il record originario. I run con modelli diversi sono serie diverse.

**Operatività locale:** quando l’app è spenta non esiste una previsione emessa in tempo reale. Una ricostruzione al riavvio è `BACKFILLED_RESEARCH`, non paper prospettico. Disponibilità, ritardi e gap di osservazione sono parte della scorecard. Il sistema può essere utile anche on demand, ma deve dire quale copertura ha realmente avuto.

Prestazioni: cache delle aggregazioni e dei fit, aggiornamenti incrementali, niente riordinamento completo della stessa distribuzione a ogni candela. Il collo di bottiglia noto di G1 va risolto preservando parità numerica. Non serve un cluster per validare questo sistema.

## 10. Tre scorecard, nessun voto finale unico

| Livello | Domanda | Misure principali | Errore interpretativo da evitare |
|---|---|---|---|
| **Forecast** | La distribuzione aggiunge informazione? | CRPS/pinball, calibrazione degli intervalli, Brier del segno, errore di magnitude, copertura e risultati per forza/affidabilità | Il P&L non dimostra calibrazione; hit-rate da solo non misura qualità |
| **Policy** | Selezionare e gestire gli ingressi aggiunge utilità? | Payoff netto dei trade, serie temporale di portafoglio, drawdown, turnover, costo, copertura, utilità dei NO_TRADE e selezione rispetto al riferimento | Una previsione giusta non rende giusto lo stop; 0 trade non dimostrano sicurezza o qualità |
| **Execution** | Quanto si perde trasformando un’intenzione in fill? | Ritardo, slippage/shortfall, fill/reject/cancel, differenza da benchmark decisionale, funding e fee effettivi | Guadagnare non significa essere stati eseguiti bene |

I gruppi weak/moderate/strong, regime, lato e motivi di NO_TRADE sono definiti prima del run. Si riportano tutti, con denominatori e incertezza, senza premiare ex post il solo sottoinsieme bello. Un filtro che migliora l’aspettativa ma elimina quasi tutte le occasioni deve rendere visibile il compromesso.

Le previsioni a 15 minuti con target quattro ore si sovrappongono. Diecimila record non sono diecimila esperimenti indipendenti. Stime d’incertezza e confronti usano blocchi temporali e sensibilità dichiarate; non t-test che assumono indipendenza delle righe. Le serie economiche vengono conservate su un indice temporale comune, includendo i periodi senza posizioni.

Confronti obbligatori, congelati e registrati:

1. Forecast nullo causale: location zero e distribuzione/scala storica stimata solo dal passato.
2. Forecast semplice della sola famiglia trend, stessa causalità e stesso fit calendar; nessuna ottimizzazione separata.
3. Policy semplice derivata dal forecast trend, stessa geometria/rischio/esecuzione, come riferimento di valore aggiunto della selezione. Cash/NO_TRADE è il riferimento economico a esposizione nulla.

Il sistema completo deve giustificare la propria complessità rispetto a questi riferimenti; non è necessario che ciascuna famiglia abbia un P&L standalone. Se una componente migliora il timing ma non il forecast, la sua utilità va giudicata dove opera. Se migliora solo la presentazione, è una capacità descrittiva del prodotto, non alpha.

L’ablazione corretta rimuove un gruppo e, quando necessario, rifitta la stessa procedura sul medesimo training. Azzerare un input in una regione mai vista può produrre uno stato artificiale: non è automaticamente una misura causale dell’importanza. I contributi lineari spiegano l’output matematico; non provano il meccanismo economico.

## 11. Autopsy automatica che produce ipotesi verificabili

L’autopsy viene generata dopo la maturazione di ogni target/trade e aggregata a cadenza fissa. Prima di proporre interpretazioni controlla timestamp, data quality, matching e costi. Un bug di causalità non è un nuovo regime di mercato.

| Caso | Diagnosi fattuale possibile | Passo successivo consentito |
|---|---|---|
| Forecast forte sbagliato | Errore del segno, quantile violato, gruppo e contributi | Cercare ricorrenza per episodi indipendenti e calibrazione |
| Direzione corretta, trade in perdita | Stop colpito prima del target temporale; costi; entrata tardiva | Separare percorso, selezione e costo; nessun “stop sbagliato” automatico |
| Forecast debole corretto | Risultato favorevole in stato poco informativo | Non aumentare la conviction per un singolo successo |
| Trade positivo con violazione | Limite, latenza, invalidità o fill non conforme | Classificare fallimento operativo anche con P&L positivo |
| NO_TRADE e successivo grande movimento | Motivo di rinuncia e payoff del riferimento congelato | Valutare il costo opportunità condizionale, non comprare il minimo ex post |
| Molto flow, poca risposta | Discordanza osservabile; eventuale reversal successivo | Ipotesi condizionale, non attribuzione certa ad assorbimento |
| Nessun trade per lunghi periodi | Funnel di esclusione per motivo e distribuzione del payoff shadow | Individuare gating eccessivo o assenza di utilità; non abbassare soglie fino a ottenere attività |

L’unità diagnostica è un **episodio**, oltre alla singola candela: sedici previsioni sovrapposte durante un movimento non sono sedici errori indipendenti. Ogni report contiene casi favorevoli, sfavorevoli e un campione deterministico casuale; non solo i grafici selezionati dal ricercatore.

### Missed opportunities, false positive e false negative

Un’opportunità mancata è definita rispetto al trade shadow congelato alla decision candle, con informazioni e piano disponibili allora. È vietato usare il miglior entry/exit trovato dopo, sommare tutti i trade shadow sovrapposti o attribuire al portafoglio capacità infinita.

Si distinguono:

- **rinuncia del modello:** nessuna azione aveva margine prudente sufficiente;
- **rinuncia per rischio/capacità:** azione economicamente interessante ma non ammissibile;
- **mancata esecuzione:** un ordine effettivamente intenzionato non è stato completato;
- **opportunità controfattuale:** payoff futuro del piano di riferimento, utile alla diagnosi ma non una perdita contabile.

False positive/negative esistono soltanto rispetto a una label esplicita: per esempio “payoff netto positivo del trade standardizzato entro expiry”. Sono diversi dagli errori di direzione del forecast. La classificazione ex post non dimostra che l’opportunità fosse riconoscibile ex ante.

L’autopsy separa **fatto**, **ipotesi di causa**, **test necessario**. Un LLM può sintetizzare questi record e proporre una change request; non può ritoccare codice, generare una nuova strategia o scegliere soglie automaticamente. Il report post-hoc su eventi/news previsto dalla missione resta in un canale separato, successivo al replay, e non modifica i segnali o lo scoring.

### Procedura di apprendimento

Una modifica parte da una scheda: fenomeno ricorrente, numero di episodi e denominatore, ruolo coinvolto, ipotesi alternativa, modifica minima, metrica primaria che dovrebbe cambiare e possibile danno collaterale. Si include evidenza contraria, non soltanto esempi a sostegno.

Si cambia un blocco concettuale per revisione. “Correggiamo contemporaneamente soglia, stop e horizon” è una nuova policy, non un piccolo fix. Le analisi explorative possono suggerire una revisione, ma vanno etichettate come esplorative. La verifica temporale successiva nel sandbox misura stabilità interna; non restituisce indipendenza a dati che hanno già guidato il ricercatore.

Un difetto deterministico di implementazione si corregge appena provato e si invalidano i run affetti. Il rerun corretto viene conservato insieme all’originale. Un fix che cambia la specifica economica o nasce per migliorare il P&L conta anche come revisione scientifica; non può essere chiamato bug per eludere il budget.

## 12. Governance del development

### Stati distinti

| Stato | Cosa è consentito | Valore probatorio |
|---|---|---|
| `SPECIFICATION` | Contratti, lineage, audit dati, fixture sintetiche | Correttezza della progettazione |
| `ENGINEERING_REPLAY` | Parità, causalità, affidabilità, rendering su finestre esposte | Correttezza dell’implementazione |
| `EXPOSED_DEVELOPMENT` | Diagnosi e revisioni entro il budget | Apprendimento e selezione, non conferma |
| `FROZEN_CANDIDATE` | Manifest di codice/dati/modelli, piano inferenziale e stress fissati | Oggetto definito da valutare |
| `PROTECTED_EVALUATION` | Un run del candidato e riferimenti congelati; report completo | Evidenza protetta rispetto a questo processo, con storia di esposizione dichiarata |
| `PREDECLARED_STRESS` | Stesso candidato e scenari congelati | Sensibilità a costi, ritardi, gap e condizioni |
| `FUTURE_PAPER` | Emissione e decisioni prospettiche immutabili secondo gate | Evidenza futura, con effettiva copertura operativa |

Lo sviluppo del software e l’allocazione alpha sono flag diversi. Un prodotto funzionante può avere `validated_strategy = null` e produrre NO_TRADE. Una strategia non promossa non obbliga a cancellare il motore, la Home o il replay.

### Mappa dei dati

La mappa proposta è precisa, ma l’audit deve verificare disponibilità e contaminazioni prima del primo run:

- **2020:** warm-up/training iniziale, se completo per il contratto scelto. Requisito minimo operativo: 180 giorni di storia valida; fino ad allora baseline/astensione esplicita, non backfill inventato.
- **2021–2024:** sandbox esposto. Il 2023–2024 non è presentato come holdout incontaminato: il progetto ha già avuto esposizione storica precedente, anche se G1 non ne ha calcolato gli esiti economici nella fase chiusa.
- **2025 in avanti:** rimane protetto secondo le restrizioni correnti. Nessuna lettura per progettare feature, soglie, costi favorevoli o esempi. Prima del freeze un custode/audit definisce l’intervallo esatto autorizzato, controllando i log di accesso e l’effettiva storia d’esposizione.
- **Futuro successivo al freeze e all’attivazione prospettica:** evidenza nuova. I dati raccolti dopo il freeze ma esaminati per cambiare il modello non appartengono più al paper confermativo di quel nuovo modello.

La protezione è procedurale, non amnesia dei ricercatori: gli eventi generali del mercato possono essere già noti. Se l’audit scopre che anche il periodo candidato alla valutazione è stato usato per progettare il sistema, lo etichetta correttamente; non sposta arbitrariamente le date fino a trovare un “holdout”. L’evidenza realmente futura diventa allora indispensabile per una conferma più forte.

Nel sandbox il replay è chronological walk-forward, con refit mensile e training solo precedente. I label maturano dopo quattro ore più l’eventuale finestra operativa necessaria. Si escludono dal training tutti gli outcome che sconfinano oltre il cut-off. Se si fanno confronti con split diversi, il purging segue gli intervalli effettivi dei label; un embargo copiato da un libro non sana leakage. I report semestrali/annuali sono descrizioni complete, non finestre tra cui scegliere il vincitore.

### Budget proposto e congelato prima dei risultati

**Un ciclo iniziale: baseline + massimo quattro revisioni sostanziali = cinque versioni eleggibili.** Una revisione è riservata al ruolo dei cicli. Sono ammessi al massimo due confronti diagnostici di ablation a gruppi, predefiniti e non promuovibili direttamente. I riferimenti della scorecard sono fissi e tutti registrati. Nessuna griglia di parametri e nessun riavvio del budget cambiando il nome di G2.

Timebox: cinque giornate per contratti/checkpoint; dieci per il primo motore e replay completo; dieci per il primo ciclo di sviluppo e report. Sono limiti di gestione proposti da Astra, non numeri ottenuti dalle fonti. Il Director può riordinare le attività dentro il perimetro; un’estensione richiede un riesame esplicito di progresso e costo, non una proroga automatica perché “manca poco al profitto”. Non è necessario chiedere all’Owner conferma per ogni ordinario fix o passaggio già incluso nel package.

Una versione negativa non chiude il ciclo. Può giustificare una revisione se l’autopsy identifica un difetto ricorrente affrontabile. Alla fine del budget si sceglie tra:

1. congelare una versione stabile da valutare;
2. congelare un prodotto solo analitico, con policy non promossa;
3. proporre un ulteriore investimento delimitato, documentando cosa è stato imparato e quale incertezza concreta si vuole risolvere.

Non è ammesso il quarto esito implicito: continuare a cambiare finché la curva sale. Il mancato edge può fermare la promozione economica senza rendere inutile il prodotto costruito.

### Ledger e costo della ricerca umana/AI

Per ogni ipotesi, modifica o run: ID, genitore, autore umano/AI, fonti, motivazione precedente ai risultati, file/episodi già osservati, data exposure, formula e parametri, codice/dati/modello hash, fit schedule, confronto, metriche, decisione, motivi di scarto e serie temporali complete.

Tenere separati: idee discusse senza dati, ipotesi diagnostiche, configurazioni realmente eseguite, refit automatici previsti, candidati eleggibili, ablation, bug rerun e revisioni di architettura. Nessuna di queste categorie scompare; non tutte equivalgono a un trial indipendente. Registrare conteggio grezzo e gruppi di lineage/correlazione, evitando un singolo “numero effettivo” presentato come certo.

La visione umana di grafici, i prompt AI che suggeriscono eccezioni e i filtri di replay usati per scegliere un modello fanno parte della ricerca. Il ledger non deve promettere di misurare perfettamente pensieri o gradi di libertà non osservabili; deve rendere la ricerca verificabile e conservare il limite residuo.

### DSR e PBO: uso deciso

**Non rendo PBO un gate obbligatorio della V1.** Con cinque versioni adattive e correlate, i rank sono grossolani e il candidato set non somiglia ai grandi esperimenti CSCV. Non genereremo altre strategie soltanto per far funzionare il diagnostico. Inoltre ricombinare blocchi non sostituisce una simulazione temporale causale.

DSR può essere riportato come sensibilità, se la lunghezza/struttura della serie e la stima del burden lo rendono interpretabile; non come certificato preciso del rischio totale di ricerca. Non useremo `PBO < 5%`, `t > 3` o un DSR target come regole universali estratte dai paper. Non ottimizzeremo nessuno di questi valori.

La difesa principale è più concreta: ipotesi poche, ledger completo, confronto temporale, candidato frozen, valutazione protetta e osservazioni future. La dipendenza dei rendimenti, i limiti dei dati e la ricerca pregressa restano dichiarati anche dopo un buon risultato statistico.

## 13. Gate di avanzamento

### A — Specifica pronta

Passa se i contratti non hanno ambiguità su timestamp, label, causalità, dati, feature, costi, stop/exit, rischio e update. I checkpoint cicli e microstructure hanno un esito documentato; un ciclo non utilizzabile può rimanere esplicitamente indisponibile senza bloccare l’intero motore. Nessuna richiesta di profitto.

### B — Sistema sviluppabile

Passa se tutte le candle attese hanno un record o un motivo di astensione; replay e batch danno gli stessi output; modificare dati successivi a t non cambia feature/forecast/decisioni a t; non ci sono letture oltre cut-off; almeno un fixture percorre LONG, SHORT, NO_TRADE, stop, expiry, gap e failure di esecuzione. Home/replay e autopsy consentono di risalire dall’output allo stato. Nessuna richiesta di profitto.

### C — Candidato congelabile

Richiede contratti stabili, riproducibilità, nessun difetto critico aperto, ledger completo e un motivo documentato per sostenere il costo della valutazione. Si applica una regola di selezione fissata prima del ciclo: fra le versioni funzionalmente valide si preferisce la più semplice che migliori il ruolo dichiarato senza deterioramento materiale di rischio/costi; parità o differenze entro l’incertezza non giustificano complessità aggiuntiva. Non si sceglie semplicemente il massimo Sharpe.

Per congelare una **policy destinata alla promozione economica** occorrono almeno segnali di utilità netta e supporto sufficiente nel development; non serve dichiararli già edge. Se non ci sono, si congela il prodotto analitico e si evita di consumare inutilmente il periodo protetto. Un NO_TRADE permanente passa un test di sicurezza, non un test di utilità del trader.

### D — Valutazione protetta e stress

Prima di aprire i dati si congela un Evaluation Plan con: intervallo, un candidato, tutti i riferimenti, metrica primaria, unità temporale, metodo d’incertezza a blocchi, minimi di supporto, margini di non inferiorità, scenari di costo e criteri di esito. Non si potranno sceglierli osservando la valutazione. Il livello di significatività può essere fissato al 5% unilaterale nel piano; questo è una convenzione di decisione, non una misura completa del rischio di ricerca.

La promozione economica richiede coerenza tra utilità netta, rischio entro contratto, evidenza non spiegata soltanto da pochissimi episodi e assenza di collasso sotto stress plausibili. Il criterio primario proposto è il rendimento medio netto della policy sulla serie temporale di portafoglio rispetto a cash, accompagnato da incertezza temporale; l’incremento rispetto alla policy semplice e la scorecard forecast sono controlli separati. Un confronto non significativo può essere **inconcludente**, non automaticamente prova di assenza di edge.

Non fisso oggi un numero universale minimo di trade: il supporto dipende da concentrazione e dipendenza, non dal conteggio grezzo. Il prossimo contratto deve definire come calcolare supporto/precisione prima del test, e il freeze deve stabilire il minimo richiesto senza vedere quel test. Molti trade della stessa giornata non devono superare artificialmente il gate.

Dopo il run, esiti ammessi: promettente per paper, fallimento economico, inconcludente o valutazione invalida per difetto. Se si usano i risultati per una modifica, il periodo diventa esposto per il successore. Un bug scoperto dopo l’apertura può rendere invalido il run, ma non cancella ciò che i ricercatori hanno già visto. Nessun “nuovo freeze” sullo stesso holdout ripulisce la storia.

### E — Paper futuro

È un programma separatamente attivato, con istante d’inizio, calendario di review, modello/update rule congelati, limiti e registrazione dei gap. La durata e la precisione richieste si fissano prima, senza fermarsi al primo tratto favorevole. Il paper misura anche availability ed execution mismatch. Finché non è attivato, nessuna ricostruzione viene chiamata prospective. Nessun passaggio di questo documento autorizza capitale reale.

## 14. Comparative advantage ipotizzata

La mia ipotesi è modesta e falsificabile: **su un unico BTC, a frequenza moderata e size piccola, il sistema potrebbe estrarre una debole persistenza condizionale e migliorarne la monetizzazione selezionando ingressi con percorso e costi più favorevoli, senza l’obbligo di essere sempre investito.**

La possibile origine del segnale è un aggiustamento non istantaneo dei partecipanti o pressione temporanea/forzata, osservabile in prezzo, partecipazione e risposta. Non possiamo identificare chi paga il vantaggio con questi dati; né dimostrare oggi che il fenomeno duri quattro ore. La distinzione tra pressione informativa persistente e transitoria è proprio una delle ipotesi da verificare, non una facoltà già posseduta dal bot.

Piccola size, pazienza, assenza di benchmark e disciplina possono ridurre svantaggi rispetto a operatori grandi o forzati, ma non costituiscono automaticamente un’informazione superiore. Non ipotizzo vantaggi di velocità, dati esclusivi, notizie anticipate o capacità di competere nel market making. Un LLM che descrive bene un grafico non è un vantaggio comparato.

Test che possono indebolire l’ipotesi: il sistema completo non migliora forecast/policy semplici; i vantaggi spariscono con costi plausibili; tutto dipende da un periodo o da casi selezionati; il timing ciclico non aiuta nel ruolo assegnato; la policy impara solo ad astenersi; le prestazioni degradano appena la selezione viene congelata. In tali casi conserviamo le capacità del prodotto e riduciamo le pretese alpha. Non aggiungiamo automaticamente altre famiglie.

## 15. Gap bloccanti circoscritti

| Gap | Serve per decidere | Checkpoint limitato | Cosa si può congelare dopo |
|---|---|---|---|
| Semantica moderna del perpetual e dei dati | Prezzo/trigger, taker flag, funding, unità, fee, latenza, short simulato | `CRYPTO-CONTRACT-01`: una giornata, documentazione primaria della venue e campione di schema dei soli dati consentiti; niente studio alpha | Contratto di strumento/dati/esecuzione e limiti dell’approssimazione |
| Fase ciclica causale/stabile | Se il ciclo può comparire come timing affidabile | `CYCLE-CAUSALITY-01`: due giornate, un metodo, fixture, fonte primaria metodologica se necessaria | Contratto o indisponibilità esplicita; una revisione di timing riservata |
| Lineage ed esposizione dei dati | Quali asset si riusano e quale valutazione è protetta | Una giornata, log/manifests/ADR e accessi; nessuna lettura dei prezzi protetti | Exposure ledger e split autorizzabili |
| Stima distribuzionale e payoff coerente | Evitare probabilità finte e stop-EV inventato | Una giornata, formule, label intervals, fixture e calendario fit; nessun torneo | Forecast/policy contracts e scoring |

Le attività si integrano nei cinque giorni del primo package; non si sommano a un programma indefinito di letture. Se un controllo non si chiude nel timebox, l’esito deve essere specifico: cosa manca, quale componente resta disabilitata e quali parti possono avanzare.

LIB-001 incompleto **non blocca** questa architettura: la parte disponibile e Harris bastano per i principi qui usati; non costruiremo un algoritmo di execution dipendente dai capitoli mancanti. Le parti mancanti restano marcate tali. Il recupero dell’intero PDF e dei paper completi dietro LIB-014/015 può migliorare la biblioteca, ma non è prerequisito per decidere il primo motore.

## 16. Roadmap e prossimo work package esatto

| WP | Output | Fine del WP |
|---|---|---|
| **G2-00 — Knowledge to Contracts** | Nuovo mandato, schede/graph, contratti, split, budget, checkpoint | Specifica implementabile senza ambiguità critiche; nessun backtest economico |
| **G2-01 — Causal Trader Vertical Slice** | Engine condiviso, forecast continuo, policy, risk/execution, event store, Home/replay minimo, autopsy | Gate B su dati sintetici e finestre esposte autorizzate |
| **G2-02 — Bounded Development Cycle 1** | Baseline e fino a quattro revisioni, ledger, report completo | Freeze candidato o prodotto analitico; decisione esplicita sul budget |
| **G2-03 — Protected Evaluation and Stress** | Un candidato congelato, confronti e stress predefiniti | Esito scientifico distinto da riuscita del software |
| **G2-04 — Future Paper** | Stream realmente prospettico e monitoraggio operativo | Evidenza nuova, senza mutazioni retroattive |

### Istruzione immediata al Research Director

**Aprire `G2-00-KNOWLEDGE-TO-CONTRACTS-V1`.** Obiettivo: recepire questa decisione e produrre un unico package implementabile per G2-01. Non chiedere a Claude Code di “costruire un trader professionista” lasciandogli la scelta economica implicita.

Deliverable esatti nel repository, con numerazione ADR successiva disponibile:

1. **ADR di adozione:** G1 chiusa; programma G2 di sviluppo per fasi; condizioni di autorizzazione; modifica mirata delle regole one-shot incompatibili con il nuovo mandato. Nessuna modifica surrettizia alla Constitution. Allineare `state/current_state.json`, `tasks/CURRENT_TASK.md` e missione solo dove serve la distinzione development/evaluation. Conservare gli stati storici senza farli prevalere sul current status.
2. `docs/canonical/G2_PROFESSIONAL_KNOWLEDGE_MODEL_V1.md`: sei knowledge card, ruolo, fonti, limiti, grafo e tetto feature/interazioni.
3. `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md`: formule effettive del filtro, scaling, penalità, residual CDF, utility heads, margine prudente, label, clocks, record schema, geometria, risk, reason codes. Nessun parametro `TBD` che possa cambiare output economici prima del primo replay.
4. `research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md`: strumento, intervalli, schema, disponibilità storica/futura, cut-off I/O, assunzioni di costo e stress; esito `CRYPTO-CONTRACT-01`.
5. `research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md`: metodo unico, prove richieste, esito, ritardo/qualità, uso shadow e confronto di timing riservato.
6. `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md` e `G2_RESEARCH_LEDGER_V1.jsonl`: budget, criteri di revisione/selezione, riferimenti, ablation, exposure, gate e responsabilità.
7. `tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md`: ordine di implementazione, riuso dei moduli con lineage, fixture di accettazione, schermate/record richiesti e divieti di accesso ai dati protetti.

Nel registry e negli indici della biblioteca, riconciliare l’aggiornamento: il registry/dossier dettagliato riporta diciannove fonti reviewed e LIB-001 parziale, mentre alcuni testi generali conservano frasi ormai superate sullo studio ancora da compiere. **Non promuovere LIB-001 a completo** per superare una checklist. Il vincolo del vecchio task “tutte reviewed prima della sintesi” va sostituito con “copertura completa del disponibile e gap espliciti”, secondo la richiesta attuale dell’Owner. Usare un solo dossier canonico LIB-020 secondo il registry; eventuali note duplicate sono lineage, non una ventunesima fonte.

Il primo WP ammette consultazione delle fonti tecniche necessarie e fixture sintetiche. Non autorizza scansioni economiche 2025+, riapertura G1, ordini, ottimizzazioni o benchmark di performance BTC. Può riusare schema e manifest dei dati esposti per rendere il contratto concreto.

**Acceptance del WP:** il Director riesce a rispondere senza interpretazioni a “quali informazioni erano disponibili?”, “che cosa viene previsto?”, “perché NO_TRADE?”, “come viene calcolato lo stop e il payoff?”, “cosa cambia dopo un errore?”, “quanti tentativi restano?” e “quali dati non si possono leggere?”. Le fixture previste coprono anche assenza di ciclo, dati stale, modello non calibrato e stop con gap.

La review del package è un controllo di coerenza scientifica e operativa. Non deve diventare una nuova richiesta di dimostrare edge prima di costruire. Passato il Gate A, il Director può emettere il task di implementazione previsto; le autorizzazioni di mercato restano legate alle fasi canoniche, non all’entusiasmo per il prototipo.

## 17. Matrice di tracciabilità delle venti fonti

Questa tabella registra il contributo effettivamente usato e il limite che impedisce di trasformarlo in autorità universale. Le scelte numeriche e di budget di questa direttiva sono decisioni progettuali di Astra, non citazioni dei libri.

| ID | Contributo trattenuto | Decisione influenzata | Limite preservato |
|---|---|---|---|
| LIB-001 — Johnson, Algorithmic Trading and DMA | Obiettivi di execution, impatto/timing, shortfall, ordini e fill | Execution separata; costi/ritardi; niente fill da touch | PDF danneggiato: 504 pagine accessibili, 90 mancanti nel dossier; nessuna ricostruzione delle lacune; contesto 2010 |
| LIB-002 — Ilmanen, Expected Returns | Rendimento atteso vs realizzato, contesto, correlazioni, rischio | Ruoli distinti e limiti al trasferimento; non sommare proxy | Orizzonti/asset spesso lontani da BTC intraday; funding liquidity non equivale a perp funding |
| LIB-003 — Chan, Quantitative Trading | Ricerca compatibile con risorse, backtest/live, parsimonia e diagnosi | Sandbox delimitato, parità del motore e costi | Idee/parametri del libro non sono edge BTC; iterative fitting non equivale a OOS |
| LIB-004 — Carver, Systematic Trading | Forecast/risk/position, pesi robusti, costi e correlazione | Architettura modulare; shrinkage; no Sharpe-weighting libero | Pesi di forecast omogenei, non di famiglie eterogenee; benefici multiasset non copiabili |
| LIB-005 — Market Wizards, The Next Generation | Contesto, timing, rischio, processi e revisione | Autopsy e separazione view/azione | Interviste selezionate e retrospettive, non esperimento né trader universale |
| LIB-006 — Man AHL crisis alpha | Trend continuo, vol scaling, crisi e portafoglio | Trend come stato graduato; rischio indipendente | Mercati tradizionali/mensili/diversificati; modelli/esempi non tutti netti o indipendenti |
| LIB-007 — Trend Following and Drawdowns | Whipsaw, drawdown e dipendenza dall’horizon | Non dichiarare morte del concetto da un episodio | Simulazioni assumono edge; nessun permesso di tollerare perdite arbitrariamente; fast trend non convalidato |
| LIB-008 — Which Trend Is Your Friend | Equivalenze/lag dei filtri lineari | Una famiglia trend; niente torneo di indicatori | Equivalenza sotto condizioni, non di qualsiasi indicatore o ciclo |
| LIB-009 — Century of Evidence | Trend lungo periodo, costi, ricostruzioni e diversificazione | Prior concettuale, non parametro | Evidenza storica tradizionale; ricostruzione e splicing; niente garanzia per quattro ore BTC |
| LIB-010 — TSMOM factors monthly | Dataset aggregato aggiornato e lineage | Provenienza/versione dei dati e dipendenza delle fonti | Serie storiche ricostruite, non test indipendente del bot né dati da inserire nel training BTC |
| LIB-011 — TSMOM original data | Dataset originario e confronto di provenienza | Distinguere dataset da replica | Stessa linea di studio; metodologia/costi non interamente contenuti nel workbook |
| LIB-012 — Advances in Financial ML | Label, overlap, leakage, purging e ricerca | Contratti causali e target di percorso | Nessuna necessità di aggiungere ML complesso o copiare tutte le tecniche |
| LIB-013 — Deflated Sharpe Ratio | Selezione del massimo, non-normalità, trial burden | Ledger e sensibilità DSR | Trial effettivi incerti; non sana dati/fill errati o ricerca nascosta |
| LIB-014 — Value and Momentum Everywhere | Interazioni tra famiglie, driver condivisi | Complementarità diversa da accordo direzionale | Summary AQR di due pagine, non paper; nessun value BTC o peso numerico derivabile |
| LIB-015 — Time Series Momentum | Own-history vs cross-sectional; orizzonte e reversal | Trend compatibile concettualmente con un solo asset | Summary AQR, stessa linea dei dataset; non prova intraday |
| LIB-016 — Cross-Section of Expected Returns | Multiplicity, test nascosti, Type I/II, conditional effects | Iterazione tracciata; teoria limita ricerca ma non la assolve | Factor zoo azionario; t>3 non è soglia universale BTC |
| LIB-017 — Mathematical Appendices to PBO | Selezione tra molti candidati, simulazioni/EVT | Budget finito e trasparenza | Supplemento di LIB-018, non prova empirica indipendente; assunzioni sintetiche |
| LIB-018 — Probability of Backtest Overfitting | Rischio della selezione, rank OOS, disclosure | PBO facoltativo; niente tuning del diagnostico | Low PBO non significa profitto; high PBO non significa famiglia senza skill; ambiguità numeriche del testo conservate |
| LIB-019 — Hull, Derivatives 6e | Pricing vs forecasting, vol dinamica, tail risk e limiti | Derivati come costo/contesto; risk governor | Testo 2006, niente crypto perpetual né parametri correnti |
| LIB-020 — Harris, Trading and Exchanges | Flow, liquidity, adverse selection, shortfall, comparative advantage | Forecast/policy/execution distinti; NO_TRADE razionale | Testo 2003; non identifica da solo flow informativo né edge BTC |

## 18. Posizione conclusiva di Astra

La direzione scelta è costruire un trader sistematico che **osserva con ruoli espliciti, prevede sempre quando i dati lo consentono, opera solo quando il piano ha utilità e fattibilità sufficienti, e conserva abbastanza evidenza da poter essere corretto senza riscrivere il passato**.

Non prometto che la combinazione di conoscenze professionali generi un edge. Decido che questa è una base seria per costruire e scoprirlo, con un investimento delimitato. G1 rimane chiusa; il prossimo passo è G2-00, seguito da un prototipo completo e da sviluppo tracciato, non da un altro veto preventivo fondato sull’assenza di profitti già dimostrati.


## Appendice — Riferimenti verificabili

Tutti i collegamenti seguenti puntano alla revisione esaminata, non a file che possono cambiare sul branch corrente. I richiami LIB nel testo si riferiscono ai dossier e alle loro distinzioni fra fonte e interpretazione.

- [OWNER_PRODUCT_MISSION_V2.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/docs/canonical/OWNER_PRODUCT_MISSION_V2.md)
- [current_state.json](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/state/current_state.json)
- [CURRENT_TASK.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/tasks/CURRENT_TASK.md)
- [ADR-0050-ADOPT-ASTRA-SYSTEM-G1-TERMINAL-PARK.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/decisions/ADR-0050-ADOPT-ASTRA-SYSTEM-G1-TERMINAL-PARK.md)
- [ADR-0051-OWNER-DIRECTED-PROFESSIONAL-TRADING-KNOWLEDGE-BASE-STUDY.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/decisions/ADR-0051-OWNER-DIRECTED-PROFESSIONAL-TRADING-KNOWLEDGE-BASE-STUDY.md)
- [PROFESSIONAL_TRADING_LIBRARY_SOURCE_REGISTRY_V1.json](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/PROFESSIONAL_TRADING_LIBRARY_SOURCE_REGISTRY_V1.json)
- [PROFESSIONAL_TRADING_LIBRARY_INVENTORY_V1.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/PROFESSIONAL_TRADING_LIBRARY_INVENTORY_V1.md)
- [PROFESSIONAL_TRADING_LIBRARY_METHODOLOGY_NOTES_V1.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/PROFESSIONAL_TRADING_LIBRARY_METHODOLOGY_NOTES_V1.md)
- [LIB-001-ALGORITHMIC-TRADING-AND-DMA.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-001-ALGORITHMIC-TRADING-AND-DMA.md)
- [LIB-002-EXPECTED-RETURNS.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-002-EXPECTED-RETURNS.md)
- [LIB-003-QUANTITATIVE-TRADING-ERNEST-CHAN.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-003-QUANTITATIVE-TRADING-ERNEST-CHAN.md)
- [LIB-004-SYSTEMATIC-TRADING.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-004-SYSTEMATIC-TRADING.md)
- [LIB-005-MARKET-WIZARDS-THE-NEXT-GENERATION.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-005-MARKET-WIZARDS-THE-NEXT-GENERATION.md)
- [LIB-006-MAN-AHL-TREND-FOLLOWING-EQUITY-AND-BOND-CRISIS-ALPHA.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-006-MAN-AHL-TREND-FOLLOWING-EQUITY-AND-BOND-CRISIS-ALPHA.md)
- [LIB-007-TREND-FOLLOWING-AND-DRAWDOWNS-IS-THIS-TIME-DIFFERENT.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-007-TREND-FOLLOWING-AND-DRAWDOWNS-IS-THIS-TIME-DIFFERENT.md)
- [LIB-008-WHICH-TREND-IS-YOUR-FRIEND.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-008-WHICH-TREND-IS-YOUR-FRIEND.md)
- [LIB-009-A-CENTURY-OF-EVIDENCE-ON-TREND-FOLLOWING-INVESTING.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-009-A-CENTURY-OF-EVIDENCE-ON-TREND-FOLLOWING-INVESTING.md)
- [LIB-010-TIME-SERIES-MOMENTUM-FACTORS-MONTHLY.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-010-TIME-SERIES-MOMENTUM-FACTORS-MONTHLY.md)
- [LIB-011-TIME-SERIES-MOMENTUM-ORIGINAL-PAPER-DATA.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-011-TIME-SERIES-MOMENTUM-ORIGINAL-PAPER-DATA.md)
- [LIB-012-ADVANCES-IN-FINANCIAL-MACHINE-LEARNING.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-012-ADVANCES-IN-FINANCIAL-MACHINE-LEARNING.md)
- [LIB-013-DEFLATED-SHARPE-RATIO.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-013-DEFLATED-SHARPE-RATIO.md)
- [LIB-014-VALUE-AND-MOMENTUM-EVERYWHERE.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-014-VALUE-AND-MOMENTUM-EVERYWHERE.md)
- [LIB-015-TIME-SERIES-MOMENTUM.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-015-TIME-SERIES-MOMENTUM.md)
- [LIB-016-CROSS-SECTION-OF-EXPECTED-RETURNS.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-016-CROSS-SECTION-OF-EXPECTED-RETURNS.md)
- [LIB-017-MATHEMATICAL-APPENDICES-PROBABILITY-OF-BACKTEST-OVERFITTING.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-017-MATHEMATICAL-APPENDICES-PROBABILITY-OF-BACKTEST-OVERFITTING.md)
- [LIB-018-THE-PROBABILITY-OF-BACKTEST-OVERFITTING.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-018-THE-PROBABILITY-OF-BACKTEST-OVERFITTING.md)
- [LIB-019-OPTIONS-FUTURES-AND-OTHER-DERIVATIVES-6E.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-019-OPTIONS-FUTURES-AND-OTHER-DERIVATIVES-6E.md)
- [LIB-020-TRADING-AND-EXCHANGES-MARKET-MICROSTRUCTURE-FOR-PRACTITIONERS.md](https://github.com/C-Gian/trading-bot/blob/aac8dad0eb3b9af04e1cdc5898b640554e80674a/research/library/source_notes/LIB-020-TRADING-AND-EXCHANGES-MARKET-MICROSTRUCTURE-FOR-PRACTITIONERS.md)