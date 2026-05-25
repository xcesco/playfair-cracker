FUNZIONALITÀ: INITIAL KEY / INITIAL MATRIX PER ANNEALING LOCALE

Obiettivo:
permettere al sistema di partire da una matrice nota o parzialmente promettente, invece che da matrici casuali, così da esplorare il vicinato della soluzione.

CLI

Aggiungere parametri:

--initial-keyword TEXT
    Keyword Playfair da cui costruire la matrice iniziale.

--initial-matrix TEXT
    Matrice completa da 25 lettere, row-major.

--initial-key-file PATH
    File contenente una o più matrici iniziali, una per riga.

--local-search
    Se presente, l’annealing deve fare ricerca locale attorno alle matrici iniziali.

--initial-mutation-radius N
    Numero massimo di mutazioni casuali applicate alla matrice iniziale per diversificare i restart.
    Default:
      fast = 5
      deep = 20

Regole:
- --initial-keyword, --initial-matrix e --initial-key-file possono essere usati come sorgenti di seed-key.
- Se nessuno è presente, i restart partono da matrici casuali.
- Se sono presenti, ogni restart parte da una variante della matrice iniziale.
- Non confondere seed RNG e initial key: il seed controlla il caso, la initial key è la matrice di partenza.

Comportamento consigliato:

fast:
- 70% restart da initial key perturbata
- 30% restart casuali

deep:
- 50% restart da initial key perturbata
- 50% restart casuali

local-search:
- 100% restart da initial key perturbata
- mutazioni più conservative
- temperatura iniziale più bassa
- più swap singoli, meno large jump

Parametri local-search:
T0 = 5.0–12.0
cooling più rapido
mutazioni:
  90% swap lettere
  5% swap righe/colonne
  5% altro

Output report:
- indicare se è stata usata una initial key;
- stampare matrice iniziale;
- stampare distanza approssimata tra best key e initial key.

Distanza:
- Hamming distance tra key iniziale e key finale;
- numero di posizioni diverse;
- eventuale numero di lettere spostate.

FUNZIONALITÀ: REPORT DETTAGLIATO N-GRAMMI RILEVATI

Obiettivo:
nel report non basta mostrare lo score. Bisogna indicare quali trigrammi/quadrigrammi rilevanti sono stati rilevati nel plaintext candidato, distinguendo:
- continuous/extraparola;
- inword/in parola;
- osservati nel modello;
- non osservati/default;
- posizioni nel plaintext.

Terminologia:
- continuous: n-grammi calcolati sul plaintext continuo, quindi possono attraversare confini di parola non noti;
- inword: n-grammi valutati come se appartenessero a parole, utile solo come euristica perché gli spazi non sono noti;
- “extra” nel report può indicare i modelli continuous;
- “in parola” indica modelli inword.

INPUT MODELLI

Obbligatori:
--quad-continuous PATH oppure default:
assets/ngrams_paisa_alphabet25/npy/paisa_4grams_continuous_logprob.npy

Opzionali:
--tri-continuous PATH
--quad-inword PATH
--tri-inword PATH
--quad-continuous-counts PATH
--quad-inword-counts PATH
--tri-continuous-counts PATH
--tri-inword-counts PATH

Se sono presenti i counts, il report può distinguere:
- n-grammi osservati: count > 0
- n-grammi non osservati: count = 0

Se i counts non sono presenti:
- usare solo logprob e soglie.

FUNZIONI DA IMPLEMENTARE

In reporting.py:

analyze_ngrams(
    plain_ids: np.ndarray,
    n: int,
    logprob: np.ndarray,
    counts: Optional[np.ndarray],
    model_name: str,
    top_k_best: int = 50,
    top_k_worst: int = 50
) -> NgramAnalysis

Deve produrre:
- total_windows;
- observed_count;
- unobserved_count;
- observed_ratio;
- mean_logprob;
- min_logprob;
- max_logprob;
- top best n-grammi;
- top worst n-grammi;
- lista posizioni dei n-grammi più significativi.

Ogni record n-gramma:
{
  "ngram": "ZION",
  "start_pos": 123,
  "end_pos": 126,
  "logprob": -4.123,
  "count": 98765,
  "observed": true
}

Conversione:
ids_to_ngram(ids[start:start+n]) usando alfabeto:
ABCDEFGHIKLMNOPQRSTUVWXYZ

Per quadrigrammi:
idx = (((a * 25) + b) * 25 + c) * 25 + d

Per trigrammi:
idx = ((a * 25) + b) * 25 + c

REPORT

Nel report.md aggiungere sezioni:

## Analisi n-grammi del plaintext candidato

### Quadrigrammi continuous / extra-parola

Campi:
- totale finestre;
- osservati nel corpus;
- non osservati;
- percentuale osservati;
- score medio;
- score minimo;
- score massimo.

Tabella top migliori:
| pos | ngram | logprob | count | observed |
|---:|---|---:|---:|---|

Tabella peggiori:
| pos | ngram | logprob | count | observed |
|---:|---|---:|---:|---|

### Quadrigrammi in parola

Stessa struttura.

### Trigrammi continuous

Stessa struttura, se modello disponibile.

### Trigrammi in parola

Stessa struttura, se modello disponibile.

OUTPUT FILE AGGIUNTIVI

Salvare:

ngram_analysis_best.json

Contiene analisi completa per il miglior plaintext.

ngram_analysis_topK.jsonl

Una riga per ogni risultato top-K:
{
  "rank": 1,
  "score": ...,
  "key": "...",
  "quad_continuous": {
    "total_windows": ...,
    "observed_count": ...,
    "unobserved_count": ...,
    "observed_ratio": ...,
    "mean_logprob": ...
  },
  "quad_inword": {...}
}

CSV opzionali:

best_quad_continuous_positions.csv
best_quad_inword_positions.csv
best_tri_continuous_positions.csv
best_tri_inword_positions.csv

Colonne:
- model
- n
- start_pos
- end_pos
- ngram
- logprob
- count
- observed
- rank_by_logprob

INTERPRETAZIONE

Nel report aggiungere nota:

“Il numero di quadrigrammi osservati non dimostra da solo la correttezza della chiave, ma è utile per confrontare plaintext candidati. Una buona chiave tende ad aumentare la media delle log-probabilità e la quota di n-grammi osservati, e a ridurre la presenza di sequenze estremamente improbabili.”

ATTENZIONE SU INWORD

Poiché il plaintext Playfair è senza spazi, il modello inword è solo euristico.

Scrivere nel report:
“Il modello inword valuta la compatibilità con sequenze interne alle parole. In assenza di spazi, non identifica davvero parole, ma premia frammenti compatibili con morfologia italiana.”

FUNZIONALITÀ: CONFRONTO INITIAL KEY VS BEST KEY

Se viene passata una matrice iniziale, aggiungere:

## Confronto matrice iniziale / migliore matrice

Campi:
- initial_key row-major;
- best_key row-major;
- hamming_distance;
- percentuale posizioni uguali;
- matrice iniziale;
- matrice finale.

Esempio:
Hamming distance: 7/25
Posizioni uguali: 72%

FUNZIONALITÀ: RESTART DA MATRICE INIZIALE

Implementazione:

In annealing.py:

prepare_initial_keys(config, n_restarts, rng)

Se initial matrices presenti:
- costruire lista base_keys;
- per ogni restart:
  - scegliere base_key round-robin o casualmente;
  - copiarla;
  - applicare random_perturbations(key, radius);
  - usare come initial_key.

random_perturbations:
- applica N mutazioni leggere;
- N random tra 0 e initial_mutation_radius;
- in local-search usare solo swap lettere e piccoli swap righe/colonne.

Nel report per ogni risultato:
- indicare initial_source:
  - random
  - keyword
  - matrix
  - key_file
- initial_key usata;
- mutation_radius applicato;
- distance_from_initial.

TEST

TEST initial matrix:
- passare --initial-matrix ABCDEFGHIKLMNOPQRSTUVWXYZ
- verificare che i restart partano da quella matrice perturbata.

TEST local-search:
- usare --local-search --initial-matrix ...
- verificare che nessun restart sia random puro;
- verificare T0 più bassa;
- verificare mutazioni conservative.

TEST ngram report:
- usare plaintext noto italiano;
- verificare che analyze_ngrams riporti:
  - total_windows = len(plain)-n+1
  - observed_count + unobserved_count = total_windows
  - posizioni corrette
  - ngram string corretto.

TEST counts assenti:
- se counts non disponibili, il report deve comunque funzionare usando logprob;
- observed può essere null oppure stimato come logprob > default_logprob.

TEST decode-only:
- anche decode-only deve generare ngram_analysis_best.json e sezioni n-grammi nel report.