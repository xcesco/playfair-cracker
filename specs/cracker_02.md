FUNZIONALITÀ: DECODE/EVALUATE CON CHIAVE NOTA

Obiettivo:
implementare una modalità che consenta di passare al cracker una chiave Playfair nota, come keyword o come matrice 5x5 completa, e verificare cosa produce la decifratura senza eseguire simulated annealing.

Serve per:
- validare preprocessing;
- validare costruzione matrice;
- validare decifratura Playfair;
- validare scoring n-grammi;
- testare casi simulati con chiave nota.

CLI

Aggiungere parametri:

--decode-only
    Se presente, non esegue simulated annealing.

--known-keyword TEXT
    Keyword Playfair da cui costruire la matrice.

--known-matrix TEXT
    Matrice Playfair completa da 25 lettere, in ordine row-major.

Regole:
- --known-keyword e --known-matrix sono mutuamente esclusivi.
- --decode-only richiede uno tra --known-keyword e --known-matrix.
- Se --decode-only non è presente, questi parametri possono essere ignorati oppure usati in futuro come initial key.

Esempi:

uv run python -m playfair_cracker.cli \
  --cipher-file data/test_cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --decode-only \
  --known-keyword INTELLIGENCE \
  --output-dir output/decode_test

uv run python -m playfair_cracker.cli \
  --cipher-file data/test_cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --decode-only \
  --known-matrix ABCDEFGHIKLMNOPQRSTUVWXYZ \
  --output-dir output/decode_test

COSTRUZIONE MATRICE DA KEYWORD

Implementare:

key_from_keyword(keyword: str) -> np.ndarray

Regole:
1. normalizzare keyword:
   - uppercase
   - J -> I
   - tenere solo lettere dell’alfabeto Playfair:
     ABCDEFGHIKLMNOPQRSTUVWXYZ

2. rimuovere duplicati preservando l’ordine.

3. appendere le lettere mancanti dell’alfabeto Playfair in ordine alfabetico.

Esempio:

keyword = INTELLIGENCE

normalizzata:
INTELLIGENCE

senza duplicati:
INTELG C
oppure, mantenendo ordine esatto:
I N T E L G C

poi completare:
I N T E L G C A B D F H K M O P Q R S U V W X Y Z

Risultato row-major:
INTELGCABDFHKMOPQRSUVWXYZ

Matrice:
I N T E L
G C A B D
F H K M O
P Q R S U
V W X Y Z

Nota:
la funzione deve essere deterministica.

COSTRUZIONE MATRICE DA STRINGA COMPLETA

Implementare:

key_from_matrix(matrix: str) -> np.ndarray

Regole:
- normalizzare:
  - uppercase
  - J -> I
  - rimuovere spazi, newline, separatori;
- dopo normalizzazione devono rimanere esattamente 25 lettere;
- tutte le lettere devono essere uniche;
- devono coincidere con l’alfabeto Playfair completo.

Se non valido:
- generare errore chiaro.

Esempi validi:
"ABCDEFGHIKLMNOPQRSTUVWXYZ"

"A B C D E
 F G H I K
 L M N O P
 Q R S T U
 V W X Y Z"

Esempi non validi:
- contiene J;
- contiene duplicati;
- manca una lettera;
- lunghezza diversa da 25.

MODALITÀ DECODE-ONLY

Implementare:

run_decode_only(config)

Passi:
1. caricare ciphertext;
2. normalizzarlo;
3. convertire in ids base 25;
4. se lunghezza dispari:
   - se strict: errore;
   - altrimenti warning e ignora ultimo carattere;
5. costruire key da keyword o matrix;
6. decifrare con Playfair;
7. calcolare score:
   - quadrigrammi continuous obbligatorio;
   - trigrammi continuous se disponibile;
   - quadrigrammi inword se disponibile;
   - letter score se disponibile;
8. salvare output.

OUTPUT DECODE-ONLY

In output-dir salvare:

1. decoded_plaintext.txt

Contiene plaintext normalizzato.

2. known_key.txt

Contiene:
- keyword usata, se presente;
- matrice row-major;
- matrice formattata 5x5.

Esempio:
KEYWORD: INTELLIGENCE
ROW_MAJOR: INTELGCABDFHKMOPQRSUVWXYZ

MATRIX:
I N T E L
G C A B D
F H K M O
P Q R S U
V W X Y Z

3. decode_report.md

Contiene:
- file cifrato;
- lunghezza cifrato normalizzato;
- eventuali caratteri rimossi;
- keyword/matrice usata;
- score quadrigrammi;
- score trigrammi se disponibile;
- score lettere se disponibile;
- prime 500 lettere del plaintext;
- ultime 500 lettere del plaintext;
- eventuali warning.

4. decode_result.json

Formato:

{
  "mode": "decode-only",
  "cipher_file": "...",
  "cipher_length": 1234,
  "known_keyword": "INTELLIGENCE",
  "known_matrix_row_major": "INTELGCABDFHKMOPQRSUVWXYZ",
  "scores": {
    "quad_continuous": -12.345,
    "tri_continuous": -8.123,
    "quad_inword": -13.456,
    "letter": -3.210
  },
  "plaintext_preview": "...",
  "plaintext_tail": "...",
  "warnings": []
}

FUNZIONI DA IMPLEMENTARE

In preprocessing.py:
- normalize_text(text: str) -> str
- text_to_ids(text: str) -> np.ndarray
- ids_to_text(ids: np.ndarray) -> str

In utils.py:
- key_from_keyword(keyword: str) -> np.ndarray
- key_from_matrix(matrix: str) -> np.ndarray
- key_to_text(key: np.ndarray) -> str
- format_matrix(key: np.ndarray) -> str
- validate_key(key: np.ndarray) -> None

In annealing.py o decode.py:
- decode_with_known_key(cipher_ids, key, models) -> DecodeResult

In numba_core.py:
- decrypt_full(cipher_pair_ids, unique_pair_ids, inverse_unique_index, key, ...) oppure riusare la pipeline già prevista;
- score_quadgrams;
- score_trigrams;
- score_letters.

TEST FUNZIONALI

Creare test manuali e/o automatici.

TEST 1: key_from_keyword

Input:
INTELLIGENCE

Atteso:
- lunghezza 25
- lettere uniche
- J assente
- ordine iniziale coerente con rimozione duplicati:
  I N T E L G C ...

Verificare:
key_to_text(key) == "INTELGCABDFHKMOPQRSUVWXYZ"

TEST 2: key_from_matrix alfabetica

Input:
ABCDEFGHIKLMNOPQRSTUVWXYZ

Atteso:
- key valida
- format_matrix produce:

A B C D E
F G H I K
L M N O P
Q R S T U
V W X Y Z

TEST 3: matrix non valida

Input:
ABCDEFGHIJKLMNOPQRSTUVWXY

Atteso:
- errore perché contiene J e manca Z oppure alfabeto errato dopo conversione.

Input:
AAAAAAAAAAAAAAAAAAAAAAAAA

Atteso:
- errore duplicati.

TEST 4: roundtrip Playfair

Implementare anche encrypt_playfair per test, anche se non necessario nel cracker.

Plaintext:
QUESTOESUNTESTDIPLAYFAIR

Keyword:
INTELLIGENCE

Passi:
1. normalizza plaintext;
2. applica preparazione Playfair:
   - dividere in digrammi;
   - se due lettere uguali nel digramma, inserire filler X;
   - se lunghezza dispari, aggiungere X;
3. cifra con key;
4. decifra con decode-only;
5. verificare che il plaintext decifrato coincida con il plaintext preparato.

Nota:
il confronto deve essere fatto con il plaintext già preparato per Playfair, non con il testo originale con spazi.

TEST 5: matrice alfabetica nota

Usare known-matrix:
ABCDEFGHIKLMNOPQRSTUVWXYZ

Creare un piccolo plaintext preparato manualmente, cifrarlo e decifrarlo.

Verificare:
decoded == prepared_plaintext

TEST 6: scoring

Decifrare con chiave corretta e con chiave casuale.

Atteso:
score chiave corretta > score chiave casuale

Usare testo italiano sufficientemente lungo, almeno 300 caratteri.

TEST 7: CLI decode-only

Eseguire:

uv run python -m playfair_cracker.cli \
  --cipher-file data/test_cipher.txt \
  --ngram-dir assets/ngrams_paisa_alphabet25 \
  --decode-only \
  --known-keyword INTELLIGENCE \
  --output-dir output/test_decode

Verificare esistenza:
- decoded_plaintext.txt
- known_key.txt
- decode_report.md
- decode_result.json

TEST 8: nessun annealing

In decode-only:
- non devono partire worker;
- non deve essere eseguito simulated annealing;
- log deve indicare chiaramente:
  "Decode-only mode: using known key/matrix, annealing disabled."

TEST 9: compatibilità con CORE

Se viene passato --core-file anche in decode-only:
- decifrare anche i core block;
- riportare nel report:
  - core cipher;
  - core plaintext;
  - score core.

SEZIONE REPORT PER CORE

Aggiungere nel decode_report.md:

## Core blocks

| # | Cipher | Plaintext | Quad score |
|---|--------|-----------|------------|

COMPORTAMENTO IN CASO DI ERRORI

- Se manca file quadrigrammi: errore chiaro.
- Se known-keyword normalizzata è vuota: errore.
- Se known-matrix non valida: errore.
- Se ciphertext vuoto: errore.
- Se ciphertext contiene caratteri rimossi: warning nel report.
- Se lunghezza dispari e non strict: warning e ultimo carattere ignorato.

NOTA DI PROGETTAZIONE

Questa funzionalità serve a validare il motore:
- se decode-only con chiave nota fallisce, il problema è in preprocessing, matrice o decifratura;
- se decode-only produce plaintext corretto ma scoring basso, il problema è nei modelli n-grammi o nel mapping degli indici;
- se decode-only funziona ma annealing non converge, il problema è nei parametri SA, mutazioni, scoring o rumore nel ciphertext.