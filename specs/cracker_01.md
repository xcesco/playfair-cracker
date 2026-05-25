Ecco le specifiche complete.

```text
Agisci come esperto di crittoanalisi classica, Python ad alte prestazioni, Numba, multiprocessing e software engineering.

Devi realizzare un progetto Python gestito con uv per attaccare un crittogramma sospettato di essere Playfair tramite Simulated Annealing ottimizzato, scoring con modelli n-grammi PAISÀ base 25, esecuzione parallela e modalità fast/deep.

NOME PROGETTO
playfair-cracker

GESTIONE PROGETTO
Usare uv.

Dipendenze minime:
- numpy
- numba
- tqdm

Comandi:
uv init playfair-cracker
uv add numpy numba tqdm

STRUTTURA DIRECTORY

playfair-cracker/
├── pyproject.toml
├── assets/
│   └── ngrams_paisa_alphabet25/
│       └── npy/
│           ├── paisa_4grams_continuous_logprob.npy
│           ├── paisa_3grams_continuous_logprob.npy
│           ├── paisa_4grams_inword_logprob.npy
│           └── paisa_letter_logprob.npy
├── data/
│   ├── cipher.txt
│   ├── clean_cipher.txt
│   └── core_blocks.txt
├── src/
│   └── playfair_cracker/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── preprocessing.py
│       ├── numba_core.py
│       ├── annealing.py
│       ├── parallel.py
│       ├── reporting.py
│       └── utils.py
└── output/

ALFABETO

Usare alfabeto Playfair e scoring base 25:

ABCDEFGHIKLMNOPQRSTUVWXYZ

La J deve essere convertita in I.

Mapping:
A=0, B=1, ..., I=8, K=9, ..., Z=24.

I modelli n-grammi sono PAISÀ alphabet25, quindi:
- trigrammi: 25^3 = 15625
- quadrigrammi: 25^4 = 390625
- lettere: 25

NOTA METODOLOGICA FONDAMENTALE

Non enumerare mai tutte le matrici Playfair.

Lo spazio teorico è:

25! ≈ 1.55 × 10^25

Il sistema deve cercare chiavi plausibili tramite:
- simulated annealing;
- restart indipendenti;
- scoring linguistico;
- parallelizzazione multi-processo sui restart.

Il parallelismo deve essere applicato ai restart, NON alla suddivisione esaustiva delle permutazioni.

INPUT ATTESI

1. Cifrato principale:
--cipher-file data/cipher.txt

2. Variante pulita opzionale:
--clean-cipher-file data/clean_cipher.txt

3. Blocchi CORE opzionali:
--core-file data/core_blocks.txt

Esempio core_blocks.txt:
MTDIQVPQRCFINUVONTLBYZYLNP
NQCTBLLNYVCLHYLWIFIGNALHMTDIQVPQRCFINUVONTLBYZYLNP

4. Directory n-grammi:
--ngram-dir assets/ngrams_paisa_alphabet25

File richiesti:
npy/paisa_4grams_continuous_logprob.npy

File opzionali:
npy/paisa_3grams_continuous_logprob.npy
npy/paisa_4grams_inword_logprob.npy
npy/paisa_letter_logprob.npy

CLI

Comando fast:

uv run python -m playfair_cracker.cli \
  --cipher-file data/clean_cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --core-file data/core_blocks.txt \
  --mode fast \
  --workers 8 \
  --output-dir output/fast_run

Comando deep:

uv run python -m playfair_cracker.cli \
  --cipher-file data/clean_cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --core-file data/core_blocks.txt \
  --mode deep \
  --workers 8 \
  --restarts 300 \
  --iters 10000000 \
  --output-dir output/deep_run

Parametri CLI:
--cipher-file PATH obbligatorio
--clean-cipher-file PATH opzionale
--core-file PATH opzionale
--core-block TEXT ripetibile opzionale
--ngram-dir PATH default assets/ngrams_paisa_alphabet25
--mode fast|deep default fast
--workers N default cpu_count()-1
--restarts N override mode
--iters N override mode
--seed N default 12345
--top-k N default 50
--output-dir PATH default output
--checkpoint-every N default 0
--strict opzionale
--verbose
--quiet

PREPROCESSING

Implementare in preprocessing.py:

normalize_text(text: str) -> str
- uppercase
- J -> I
- conserva solo caratteri in ABCDEFGHIKLMNOPQRSTUVWXYZ
- rimuove spazi, punteggiatura, numeri, accenti già eventualmente convertiti se presenti

text_to_ids(text: str) -> np.ndarray uint8
ids_to_text(ids: np.ndarray) -> str
split_pairs(ids: np.ndarray) -> np.ndarray uint8 shape=(n_pairs,2)

Se lunghezza dispari:
- se --strict: errore
- altrimenti: warning e ignora ultimo carattere

Costruire:
cipher_ids
cipher_pairs
cipher_pair_ids = c1 * 25 + c2

Ottimizzazione:
unique_pair_ids, inverse_unique_index = np.unique(cipher_pair_ids, return_inverse=True)

I dati FULL, CLEAN e CORE devono essere preprocessati nello stesso modo.

RAPPRESENTAZIONE CHIAVE

La matrice Playfair è rappresentata come:

key: np.ndarray dtype=np.uint8 shape=(25,)

key[pos] = letter_id presente nella cella pos.

Posizione row-major:
pos = row * 5 + col

Esempio:

key = [0,1,2,3,4,5,...]

rappresenta:

A B C D E
F G H I K
L M N O P
Q R S T U
V W X Y Z

Inverse:

pos[letter_id] = posizione nella matrice

NUMBA OBBLIGATORIO

Le funzioni hot devono stare in numba_core.py.

Usare:

from numba import njit

@njit(cache=True)

Le funzioni hot devono evitare:
- dict
- pandas
- stringhe
- liste Python dinamiche
- oggetti dataclass
- logging
- allocazioni inutili

Usare:
- np.ndarray numerici
- uint8, uint16, int64, float32/float64
- loop espliciti compilati

FUNZIONI NUMBA CORE

Implementare:

1. build_inverse_positions(key, pos_out)

Input:
key uint8[25]
pos_out uint8[25]

Effetto:
pos_out[key[i]] = i

2. decrypt_pair_id(pair_id, key, pos) -> uint16

pair_id = c1 * 25 + c2

Regole decifratura:
- stessa riga: sposta a sinistra
- stessa colonna: sposta sopra
- rettangolo: scambia colonne

Return:
plain_pair_id = p1 * 25 + p2

3. decrypt_unique_pairs(unique_pair_ids, key, pos, decoded_unique_out)

Decifra solo i pair_id unici.

4. rebuild_plain(decoded_unique, inverse_unique_index, plain_out)

Ricostruisce plaintext completo:

plain_out[2*i]   = decoded_pair // 25
plain_out[2*i+1] = decoded_pair % 25

5. score_quadgrams(plain, quad_scores) -> float64

Indice:

idx = (((a * 25) + b) * 25 + c) * 25 + d

Score preferibilmente medio:

score = total / max(1, n_quadgrams)

6. score_trigrams(plain, tri_scores) -> float64 opzionale

idx = ((a * 25) + b) * 25 + c

7. score_letters(plain, letter_scores) -> float64 opzionale

8. penalty_consonant_runs(plain) -> float64

Penalizza sequenze consonantiche troppo lunghe.

Vocali:
A,E,I,O,U

9. penalty_repeated_plain_digrams(plain) -> float64

Penalizza plaintext con troppe doppie immediate o pattern strani.

10. bonus_endings(plain) -> float64

Bonus piccolo:
- ultima lettera vocale
Bonus medio:
- finali RE, TO, TA, TE, NE, NO, NA, LA, LE, LO, DI, SI
Bonus più alto:
- suffissi ZIONE, MENTO, ARE, ERE, IRE

Non deve essere vincolo duro.

11. evaluate_key(...)

Input:
- key
- dati FULL precomputati
- dati CORE precomputati
- quad_scores
- opzionali tri_scores, inword_scores, letter_scores
- pesi

Output:
score totale float64

Formula base:

score =
    w_full * score_full
  + w_core * score_core_mean
  + w_tri * score_tri
  + w_inword * score_inword
  + w_letter * score_letter
  + bonuses
  - penalties

Score principale:
paisa_4grams_continuous_logprob.npy

12. mutate_key(current_key, candidate_key, rng_state, phase)

Deve generare candidate_key da current_key.

Mutazioni:
- swap due lettere
- swap due righe
- swap due colonne
- rotazione riga
- rotazione colonna
- inversione riga
- inversione colonna
- trasposizione matrice
- large jump con 3-8 swap

Fase calda:
45% swap lettere
15% swap righe
15% swap colonne
8% rotazioni
8% inversioni
4% trasposizione
5% large jump

Fase fredda:
85% swap lettere
10% swap righe/colonne
5% altro

RNG IN NUMBA

Per semplicità e performance:
- usare np.random.seed(seed) dentro ogni annealing_run compilato
- usare np.random.randint e np.random.random dentro Numba

Ogni restart deve ricevere seed distinto:

restart_seed = base_seed + worker_id * 1_000_000 + restart_id

SIMULATED ANNEALING

Implementare annealing_run in numba_core.py.

Input:
- initial_key
- seed
- iters
- temperatura iniziale T0
- cooling
- dati scoring
- pesi
- buffer preallocati

Output:
- best_key
- best_score
- current/best plaintext opzionale o ricostruibile fuori

Pseudo:

set seed
current_key = initial_key
current_score = evaluate_key(current_key)
best_key = current_key
best_score = current_score

for iter in range(iters):
    phase = iter / iters
    mutate_key(current_key, candidate_key, seed, phase)
    candidate_score = evaluate_key(candidate_key)

    delta = candidate_score - current_score

    if delta > 0:
        accept
    else:
        accept with probability exp(delta / T)

    if accept:
        swap current_key/candidate_key
        current_score = candidate_score

    if current_score > best_score:
        best_score = current_score
        best_key = current_key

    T *= cooling

Restituire best_key e best_score.

MODALITÀ FAST

Default:
restarts = 50
iters = 1_000_000
T0 = 20.0
cooling = 0.999995
top_k = 50

Pesi:
w_full = 0.55
w_core = 0.45
w_tri = 0.05 se trigrammi disponibili
w_inword = 0.05 se disponibile
w_letter = 0.02 se disponibile

Scopo:
- debug
- esplorazione rapida
- verifica pipeline

MODALITÀ DEEP

Default:
restarts = 300
iters = 10_000_000
T0 = 35.0
cooling = 0.9999992
top_k = 100

Fase iniziale:
w_full = 0.40
w_core = 0.60

Fase finale/refinement:
- prendere top 20 risultati
- eseguire 2_000_000 iterazioni aggiuntive per ciascuno
- quasi solo swap lettere
- pesi:
  w_full = 0.75
  w_core = 0.25

Scopo:
- attacco serio
- massimizzazione qualità plaintext
- riduzione overfitting sui core blocks

PARALLELIZZAZIONE

Implementare in parallel.py.

Usare:

concurrent.futures.ProcessPoolExecutor

Ogni worker:
- riceve worker_id
- riceve numero restart assegnati
- carica o riceve dati necessari
- usa seed distinti
- esegue restart indipendenti
- mantiene top-K locale
- ritorna risultati migliori

Non coordinare ogni mutazione tra worker.

Main:
- crea workers
- raccoglie risultati
- deduplica chiavi
- ordina per score
- salva top-K globale

Dedup:

key_tuple = tuple(key.tolist())

NGINRAM LOADING

In annealing.py o cli.py:

Caricare con mmap dove possibile:

np.load(path, mmap_mode="r")

Controlli:
quad continuous shape == (390625,)
tri continuous shape == (15625,) se presente
quad inword shape == (390625,) se presente
letter logprob shape == (25,) se presente

Se shape diversa:
errore chiaro.

OUTPUT

Salvare in output-dir:

1. best_results.jsonl

Ogni record:
{
  "rank": 1,
  "score": -12.345,
  "key": "ABCDEFGHIKLMNOPQRSTUVWXYZ",
  "matrix": ["ABCDE", "FGHIK", "LMNOP", "QRSTU", "VWXYZ"],
  "plaintext": "...",
  "plaintext_preview": "...",
  "mode": "fast",
  "worker_id": 0,
  "restart_id": 12,
  "iters": 1000000,
  "seed": 12345
}

2. best_plaintext.txt

3. best_key.txt

4. report.md

5. config_used.json

REPORT

report.md deve contenere:
- data esecuzione
- parametri
- file input
- worker
- restart
- iterazioni
- pesi scoring
- top 10 chiavi
- top 10 score
- preview plaintext
- decifratura dei CORE blocks
- finale plaintext
- note su plausibilità linguistica
- avvertenza: SA è probabilistico e non garantisce soluzione certa

CHECKPOINT

Se --checkpoint-every > 0:
- salvare risultati parziali ogni N restart completati
- non serve salvare stato interno del singolo annealing
- salvare top-K corrente e config

OTTIMIZZAZIONI OBBLIGATORIE

1. Decifrare solo digrammi unici:
- unique_pair_ids
- inverse_unique_index
- decoded_unique

2. Preallocare buffer:
- pos_out uint8[25]
- decoded_unique uint16[n_unique]
- plain_out uint8[n_chars]
- candidate_key uint8[25]
- current_key uint8[25]

3. Loop caldo in Numba:
- mutazione
- decifratura
- scoring
- acceptance

4. Evitare stringhe nel loop.

5. Convertire a testo solo per i risultati top-K fuori dal loop Numba.

6. Parallelizzare restart con processi.

7. Usare array float32 per scores ma accumulare in float64.

8. Non usare pandas.

VALIDAZIONE

Implementare test minimi:

- valid_key(key)
  - lunghezza 25
  - lettere 0..24 uniche

- test indice quadrigramma:
  ABCD = (((0*25)+1)*25+2)*25+3

- test decifratura:
  con matrice alfabetica, verificare manualmente alcuni digrammi:
  stessa riga
  stessa colonna
  rettangolo

- test preprocessing:
  J -> I
  rimozione caratteri non validi

- test shape n-grammi.

LOGGING

Usare logging semplice.

Durante esecuzione:
- stampa parametri
- stampa worker avviati
- aggiorna best globale quando migliora
- mostra preview plaintext per best
- in verbose mostra restart completati

Usare tqdm se non quiet.

RISULTATI INTERPRETABILI

Aggiungere funzione:

decode_with_key(cipher, key)

fuori da Numba o con wrapper, per ottenere plaintext leggibile.

Aggiungere:

format_matrix(key)

per stampare:

A B C D E
F G H I K
...

ESTENSIONI FUTURE DA PREDISPORRE

Non implementare necessariamente, ma progettare senza impedire:
- vincoli manuali da playground;
- blocchi con pesi diversi;
- blacklist/whitelist di plaintext;
- restart da chiave iniziale fornita;
- export compatibile con HTML lab.

REQUISITI FINALI

Consegna:
1. progetto Python completo;
2. pyproject.toml compatibile uv;
3. codice modulare nei file indicati;
4. README breve con esempi;
5. script eseguibile con uv run;
6. report output automatico.

Principio guida:
correttezza crittoanalitica + performance.

Il sistema deve produrre candidate ordinate per plausibilità, non promettere certezza.
```
