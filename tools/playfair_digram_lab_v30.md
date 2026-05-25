# Playfair Digram Lab v30

**Playfair Digram Lab v30** è un tool web interattivo per la **crittanalisi manuale assistita di cifrari Playfair**.

### 🎯 Cosa Fa

È un laboratorio visuale che guida l'analisi di un crittogramma attraverso **11 pannelli specializzati**:

1. **Input cipher** → carica testo cifrato, normalizza (J→I, rimuove spazi)
2. **Vista digrammi interattiva** → visualizza tutti i digrammi come chip colorati, editing inline delle ipotesi, context menu (blocca/sblocca/modifica)
3. **Bigrammi italiani frequenti** → riferimento statistico (DI, IN, CO, RE...)
4. **Assegnazione guidata** → tabella top-N digrammi cifrati + mapping verso italiani frequenti
5. **Gestione ipotesi** → tabella master delle associazioni cipher→plain con import/export, lock/unlock
6. **Confronto frequenze** → grafici comparativi messaggio vs italiano
7. **Controlli Playfair strutturali** → verifica digrammi doppi (QQ, LL → impossibili in Playfair standard)
8. **Statistiche crittoanalitiche** → entropia, distribuzione, segnali utili
9. **Sequenze ricorrenti** → trova pattern ripetuti (es. "ABCD" ripetuto 5 volte), filtrabile per lunghezza
10. **Dettaglio sequenza** → contesto delle occorrenze, ipotesi globale
11. **Supporto Playfair** → prova chiavi, genera matrice 5×5, decifratura automatica

### ⚡ Funzionalità Chiave

- **Editing visuale drag-and-drop**: scambia ipotesi tra digrammi
- **Evidenziazione sincronizzata**: seleziona una sequenza → highlight in tutti i pannelli
- **Lock mechanism**: blocca ipotesi corrette per non sovrascriverle
- **Validazione real-time**: rileva conflitti (stessa ipotesi assegnata a 2+ cipher)
- **Modalità "Applica Playfair"**: data una chiave candidata, calcola automaticamente TUTTE le trasformazioni Playfair e popola le ipotesi
- **Import/export configurazione**: salva/carica l'intero stato di lavoro (JSON)

### 🧠 Workflow Tipico

```
Cipher → Analizza frequenze → Assegna ipotesi ai top digrammi 
      → Trova sequenze ripetute → Valida con contesto 
      → Prova chiave Playfair candidata → Itera
```

### 💡 Casi d'Uso

- **Didattico**: studenti imparano crittanalisi Playfair con feedback visuale
- **CTF**: risolvere challenge Playfair in gare di sicurezza informatica
- **Ricerca**: analizzare cifrari storici (comunicazioni militari, messaggi diplomatici)

**In sintesi:** un IDE visuale per la crittanalisi Playfair, che combina analisi statistiche automatiche con manipolazione manuale delle ipotesi, progettato per ridurre il lavoro ripetitivo e accelerare il processo di decifratura.