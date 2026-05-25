# Playfair Cracker

Attacco a crittogrammi Playfair tramite Simulated Annealing con scoring basato su modelli n-grammi PAISÀ.

## Caratteristiche

- **Simulated Annealing ottimizzato**: Ricerca euristica nello spazio delle chiavi Playfair
- **Scoring linguistico**: Modelli n-grammi italiani (quadrigrammi, trigrammi, frequenze lettere)
- **Esecuzione parallela**: Restart multipli distribuiti su processi paralleli
- **Numba JIT compilation**: Funzioni hot-path compilate per massime prestazioni
- **Modalità Fast e Deep**: Configurazioni bilanciate per esplorazione rapida o ricerca approfondita
- **Core blocks**: Supporto per blocchi di testo noti per guidare la ricerca

## Installazione

Gestione con `uv`:

```bash
git clone https://github.com/xcesco/playfair-cracker .
cd /playfair-cracker
uv sync
```

## Utilizzo

### Modalità Fast (Esplorazione rapida)

```bash
uv run python -m playfair_cracker.cli \
  --cipher-file data/cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --mode fast \
  --workers 8 \
  --output-dir output/fast_run
```

**Parametri Fast:**
- 50 restart
- 1.000.000 iterazioni per restart
- Ottimizzato per debug e verifica pipeline

### Modalità Deep (Ricerca approfondita)

```bash
uv run python -m playfair_cracker.cli \
  --cipher-file data/cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --core-file data/core_blocks.txt \
  --mode deep \
  --workers 8 \
  --output-dir output/deep_run
```

**Parametri Deep:**
- 300 restart
- 10.000.000 iterazioni per restart
- Refinement automatico sui top-20 risultati
- Ottimizzato per attacco reale

### Con blocchi CORE

I blocchi CORE sono porzioni di testo cifrato che si sospetta possano corrispondere a parole/frasi note. Aiutano a guidare la ricerca:

```bash
# Da file
--core-file data/core_blocks.txt

# Da command line
--core-block "MTDIQVPQRCFINUVONTLBYZYLNP" \
--core-block "NQCTBLLNYVCLHYLWIFIGNALHMTDIQVPQRCFINUVONTLBYZYLNP"
```

## Struttura Input

### Cipher File

Testo cifrato in formato Playfair (solo lettere A-Z, J convertita in I):

```
MTDIQVPQRCFINUVONTLBYZYLNP
NQCTBLLNYVCLHYLWIFIGNALH...
```

### N-gram Directory

Directory contenente modelli PAISÀ base 25:

```
assets/ngrams_paisa_alphabet25/
└── npy/
    ├── paisa_4grams_continuous_logprob.npy    [OBBLIGATORIO]
    ├── paisa_3grams_continuous_logprob.npy    [opzionale]
    ├── paisa_4grams_inword_logprob.npy        [opzionale]
    └── paisa_letter_logprob.npy               [opzionale]
```

## Output

Il sistema genera nella directory di output:

1. **best_results.jsonl**: Risultati top-K in formato JSONL
2. **best_plaintext.txt**: Plaintext migliore
3. **best_key.txt**: Matrice chiave migliore (5x5)
4. **report.md**: Report dettagliato con analisi
5. **config_used.json**: Configurazione eseguita

### Esempio report.md

```markdown
# Playfair Cracker Report

## Top Results

### Rank 1

**Score:** -2.3456

**Key Matrix:**
```
A B C D E
F G H I K
L M N O P
Q R S T U
V W X Y Z
```

**Plaintext Preview:**
```
QUESTOEUNESEMPIODIPLAINTEXTDECIFRATO...
```
```

## Parametri CLI Completi

```
--cipher-file PATH          File cifrato (OBBLIGATORIO)
--clean-cipher-file PATH    File cifrato pulito (opzionale)
--core-file PATH            File con blocchi CORE (opzionale)
--core-block TEXT           Blocco CORE da CLI (ripetibile)
--ngram-dir PATH            Directory n-grammi (default: assets/ngrams_paisa_alphabet25)
--mode fast|deep            Modalità esecuzione (default: fast)
--workers N                 Processi paralleli (default: CPU-1)
--restarts N                Override numero restart
--iters N                   Override iterazioni per restart
--seed N                    Seed casuale base (default: 12345)
--top-k N                   Numero risultati da conservare
--output-dir PATH           Directory output (default: output)
--checkpoint-every N        Salvataggio checkpoint ogni N restart (default: 0 = disabilitato)
--strict                    Errore su lunghezza dispari
--verbose                   Output verboso
--quiet                     Output minimale
```

## Algoritmo

### Rappresentazione Chiave

La chiave Playfair è una permutazione dell'alfabeto 25 lettere disposta in matrice 5×5:

```python
key = np.array([0,1,2,...,24], dtype=uint8)  # posizione -> lettera
pos = np.array([0,1,2,...,24], dtype=uint8)  # lettera -> posizione
```

### Simulated Annealing

1. **Inizializzazione**: Chiave casuale
2. **Iterazione**:
   - Muta chiave corrente (swap lettere, righe, colonne, rotazioni, ecc.)
   - Valuta candidato con scoring linguistico
   - Accetta se migliore o con probabilità exp(Δ/T)
   - Raffredda temperatura T
3. **Tracking**: Mantiene best key globale

### Mutazioni

**Fase calda** (primi 50% iterazioni):
- 45% swap lettere
- 15% swap righe
- 15% swap colonne
- 8% rotazioni
- 4% trasposizione
- 5% large jump (3-8 swap)

**Fase fredda** (ultimi 50%):
- 85% swap lettere (fine-tuning)
- 10% swap righe/colonne
- 5% altro

### Scoring

```
score = w_full × score_full_quadgrams
      + w_core × score_core_quadgrams
      + w_tri × score_trigrams          [opzionale]
      + w_inword × score_inword          [opzionale]
      + w_letter × score_letter_freq     [opzionale]
      + bonus_endings                    [piccolo bonus]
      - penalty_consonant_runs           [penalità sequenze consonantiche]
      - penalty_repeated_digrams         [penalità doppie eccessive]
```

**Pesi Fast:**
- w_full = 0.55
- w_core = 0.45

**Pesi Deep (iniziale):**
- w_full = 0.40
- w_core = 0.60

**Pesi Deep (refinement):**
- w_full = 0.75
- w_core = 0.25

### Parallelizzazione

- I **restart** sono indipendenti → parallelizzazione perfetta
- Ogni worker:
  - Riceve subset di restart
  - Usa seed distinti
  - Esegue annealing locale
  - Ritorna top-K locale
- Main processo:
  - Raccoglie risultati
  - Deduplica chiavi
  - Ordina per score
  - Salva top-K globale

### Ottimizzazioni

1. **Decifratura digrammi unici**: Cache-friendly, evita ricalcoli
2. **Numba JIT**: Compilazione hot-path (10-100× speedup)
3. **Buffer preallocati**: Zero allocazioni nel loop
4. **Float32 per scores**: Bilancio precisione/memoria
5. **mmap per n-grammi**: Caricamento lazy

## Avvertenze

⚠️ **Simulated Annealing è probabilistico**:
- Non garantisce trovare la soluzione vera
- Risultati dipendono da parametri, seed, numero restart
- Validazione umana essenziale

⚠️ **Spazio di ricerca enorme**:
- 25! ≈ 1.55 × 10²⁵ chiavi possibili
- SA esplora solo frazione infinitesima
- Core blocks critici per guidare ricerca

## Esempi di Uso

### Debug rapido

```bash
uv run python -m playfair_cracker.cli \
  --cipher-file data/cipher.txt \
  --mode fast \
  --workers 4 \
  --restarts 10 \
  --verbose
```

### Attacco production

```bash
uv run python -m playfair_cracker.cli \
  --cipher-file data/clean_cipher.txt \
  --core-file data/core_blocks.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --mode deep \
  --workers 16 \
  --restarts 500 \
  --output-dir output/production_$(date +%Y%m%d_%H%M%S)
```

## Troubleshooting

### Errore: "Invalid quadgram shape"

Verificare che i file `.npy` nella directory n-grammi siano per alfabeto 25 lettere.

### Score troppo bassi

- Aumentare `--restarts`
- Aumentare `--iters`
- Verificare core blocks
- Provare seed diversi

### Out of memory

- Ridurre `--workers`
- Verificare dimensione file .npy
- Usare mmap (già abilitato)

## Performance

**Hardware tipico** (16 core, 32GB RAM):
- Fast mode: ~5-10 minuti
- Deep mode: ~2-4 ore

**Scaling**:
- Lineare con numero restart
- Lineare con lunghezza cifrato
- Sub-lineare con numero workers (overhead comunicazione)

## Documentazione
Per la documentaizone si consulti [INDICE_DOCUMENTAZIONE.md](INDICE_DOCUMENTAZIONE.md)

## Licenza

MIT License

## Autore

Francesco Benincasa

