"""
Numba-optimized core functions for Playfair cipher cracking.
All hot loop functions are JIT-compiled for maximum performance.
"""

import numpy as np
from numba import njit


@njit(cache=True)
def build_inverse_positions(key, pos_out):
    """
    Build inverse position lookup.

    Args:
        key: uint8[25] - position to letter mapping
        pos_out: uint8[25] - output array for letter to position mapping
    """
    for i in range(25):
        pos_out[key[i]] = i


@njit(cache=False)  # Cache disabled to force recompilation after overflow fix
def decrypt_pair_id(pair_id, key, pos):
    """
    Decrypt a single pair ID.

    Args:
        pair_id: c1 * 25 + c2
        key: uint8[25]
        pos: uint8[25] inverse positions

    Returns:
        plain_pair_id: p1 * 25 + p2
    """
    c1 = pair_id // 25
    c2 = pair_id % 25

    pos1 = pos[c1]
    pos2 = pos[c2]

    row1, col1 = pos1 // 5, pos1 % 5
    row2, col2 = pos2 // 5, pos2 % 5

    if row1 == row2:
        # Same row - shift left
        col1 = (col1 - 1) % 5
        col2 = (col2 - 1) % 5
        p1 = key[row1 * 5 + col1]
        p2 = key[row2 * 5 + col2]
    elif col1 == col2:
        # Same column - shift up
        row1 = (row1 - 1) % 5
        row2 = (row2 - 1) % 5
        p1 = key[row1 * 5 + col1]
        p2 = key[row2 * 5 + col2]
    else:
        # Rectangle - swap columns
        p1 = key[row1 * 5 + col2]
        p2 = key[row2 * 5 + col1]

    # Cast to uint16 to prevent overflow (max: 24*25+24 = 624)
    return np.uint16(p1) * np.uint16(25) + np.uint16(p2)


@njit(cache=False)  # Cache disabled to force recompilation
def decrypt_unique_pairs(unique_pair_ids, key, pos, decoded_unique_out):
    """
    Decrypt all unique pair IDs.

    Args:
        unique_pair_ids: uint16 array of unique pair IDs
        key: uint8[25]
        pos: uint8[25] inverse positions
        decoded_unique_out: uint16 output array
    """
    for i in range(len(unique_pair_ids)):
        decoded_unique_out[i] = decrypt_pair_id(unique_pair_ids[i], key, pos)


@njit(cache=False)  # Cache disabled to force recompilation
def rebuild_plain(decoded_unique, inverse_unique_index, plain_out):
    """
    Rebuild full plaintext from decoded unique pairs.

    Args:
        decoded_unique: uint16 array of decoded unique pairs
        inverse_unique_index: indices to map back
        plain_out: uint8 output array
    """
    for i in range(len(inverse_unique_index)):
        pair = decoded_unique[inverse_unique_index[i]]
        # Explicit cast to uint8 to ensure valid letter IDs (must be 0-24)
        plain_out[2 * i] = np.uint8(pair // np.uint16(25))
        plain_out[2 * i + 1] = np.uint8(pair % np.uint16(25))


@njit(cache=True)
def score_quadgrams(plain, quad_scores):
    """
    Score plaintext using quadgram log probabilities.

    Args:
        plain: uint8 array of plaintext letter IDs
        quad_scores: float32 array of shape (390625,) with log probabilities

    Returns:
        Average quadgram score
    """
    n = len(plain)
    if n < 4:
        return -999.0

    total = 0.0
    count = 0

    for i in range(n - 3):
        a = plain[i]
        b = plain[i + 1]
        c = plain[i + 2]
        d = plain[i + 3]

        # Cast to int64 to prevent overflow (max index: 390624)
        idx = int((int(a) * 25 + int(b)) * 25 + int(c)) * 25 + int(d)
        total += quad_scores[idx]
        count += 1

    if count == 0:
        return -999.0

    return total / count


@njit(cache=True)
def score_trigrams(plain, tri_scores):
    """
    Score plaintext using trigram log probabilities.

    Returns:
        Average trigram score
    """
    n = len(plain)
    if n < 3:
        return -999.0

    total = 0.0
    count = 0

    for i in range(n - 2):
        a = plain[i]
        b = plain[i + 1]
        c = plain[i + 2]

        # Cast to int to prevent overflow (max index: 15624)
        idx = int((int(a) * 25 + int(b)) * 25 + int(c))
        total += tri_scores[idx]
        count += 1

    if count == 0:
        return -999.0

    return total / count


@njit(cache=True)
def score_letters(plain, letter_scores):
    """
    Score plaintext using letter log probabilities.

    Returns:
        Average letter score
    """
    n = len(plain)
    if n == 0:
        return -999.0

    total = 0.0

    for i in range(n):
        total += letter_scores[plain[i]]

    return total / n


@njit(cache=True)
def penalty_consonant_runs(plain):
    """
    Penalize long consonant runs.

    Vowels are: A(0), E(4), I(8), O(14), U(20)
    """
    vowels = np.array([0, 4, 8, 14, 20], dtype=np.uint8)

    n = len(plain)
    if n == 0:
        return 0.0

    max_cons_run = 0
    current_run = 0

    for i in range(n):
        letter = plain[i]
        is_vowel = False

        for v in vowels:
            if letter == v:
                is_vowel = True
                break

        if is_vowel:
            current_run = 0
        else:
            current_run += 1
            if current_run > max_cons_run:
                max_cons_run = current_run

    # Penalize runs longer than 4 consonants
    if max_cons_run <= 4:
        return 0.0
    else:
        return -0.5 * (max_cons_run - 4)


@njit(cache=True)
def penalty_repeated_plain_digrams(plain):
    """
    Penalize too many repeated digrams in plaintext.
    """
    n = len(plain)
    if n < 2:
        return 0.0

    # Count consecutive repeated letters (doubles)
    doubles = 0
    for i in range(n - 1):
        if plain[i] == plain[i + 1]:
            doubles += 1

    # Light penalty for too many doubles (Italian has some but not too many)
    if doubles > n // 20:  # More than 5% doubles
        return -0.3

    return 0.0


@njit(cache=True)
def bonus_endings(plain):
    """
    Give bonus for plausible Italian endings.

    This is a small bonus, not a hard constraint.
    """
    n = len(plain)
    if n < 2:
        return 0.0

    bonus = 0.0

    # Check last letter
    last = plain[n - 1]
    vowels = np.array([0, 4, 8, 13, 19], dtype=np.uint8)

    for v in vowels:
        if last == v:
            bonus += 0.1
            break

    # Check common 2-letter endings
    if n >= 2:
        last2 = plain[n - 2:n]
        # RE(17,4), TO(19,14), TA(19,0), TE(19,4), NE(13,4), NO(13,14)
        # NA(13,0), LA(11,0), LE(11,4), LO(11,14), DI(3,8), SI(18,8)

        common_endings = [
            (17, 4),  # RE
            (19, 14), # TO
            (19, 0),  # TA
            (19, 4),  # TE
            (13, 4),  # NE
            (13, 14), # NO
            (13, 0),  # NA
            (11, 0),  # LA
            (11, 4),  # LE
            (11, 14), # LO
            (3, 8),   # DI
            (18, 8),  # SI
        ]

        for ending in common_endings:
            if last2[0] == ending[0] and last2[1] == ending[1]:
                bonus += 0.2
                break

    # Check suffixes (if long enough)
    if n >= 5:
        # ZIONE -> 25,8,14,13,4 (but Z=24 in our alphabet)... Actually our alphabet has no Z in position 24
        # Let me reconsider: ABCDEFGHIKLMNOPQRSTUVWXYZ
        # Z is at position 24
        # Check ARE(0,17,4), ERE(4,17,4), IRE(8,17,4)

        last3 = plain[n - 3:n]
        # ARE
        if last3[0] == 0 and last3[1] == 17 and last3[2] == 4:
            bonus += 0.3
        # ERE
        elif last3[0] == 4 and last3[1] == 17 and last3[2] == 4:
            bonus += 0.3
        # IRE
        elif last3[0] == 8 and last3[1] == 17 and last3[2] == 4:
            bonus += 0.3

    if n >= 6:
        # MENTO -> M=11, E=4, N=12, T=18, O=13
        last5 = plain[n - 5:n]
        if (last5[0] == 11 and last5[1] == 4 and last5[2] == 12 and
            last5[3] == 18 and last5[4] == 13):
            bonus += 0.4

        # ZIONE -> Z=24, I=8, O=13, N=12, E=4
        if (last5[0] == 24 and last5[1] == 8 and last5[2] == 13 and
            last5[3] == 12 and last5[4] == 4):
            bonus += 0.5

    return bonus


@njit(cache=True)
def evaluate_key(
    key,
    full_unique_pair_ids,
    full_inverse_unique_index,
    full_n_chars,
    core_unique_pair_ids,
    core_inverse_unique_index,
    core_n_chars,
    quad_scores,
    tri_scores,
    inword_scores,
    letter_scores,
    w_full,
    w_core,
    w_tri,
    w_inword,
    w_letter,
    pos_buffer,
    decoded_unique_buffer_full,
    plain_buffer_full,
    decoded_unique_buffer_core,
    plain_buffer_core,
):
    """
    Evaluate a key using all scoring components.

    Returns total score (higher is better).
    """
    # Build inverse positions
    build_inverse_positions(key, pos_buffer)

    score = 0.0

    # Score FULL cipher
    if len(full_unique_pair_ids) > 0:
        decrypt_unique_pairs(full_unique_pair_ids, key, pos_buffer, decoded_unique_buffer_full)
        rebuild_plain(decoded_unique_buffer_full, full_inverse_unique_index, plain_buffer_full)

        score_full = score_quadgrams(plain_buffer_full, quad_scores)
        score += w_full * score_full

        # Add optional scorers for full text
        if tri_scores is not None and w_tri > 0:
            score += w_tri * score_trigrams(plain_buffer_full, tri_scores)

        if letter_scores is not None and w_letter > 0:
            score += w_letter * score_letters(plain_buffer_full, letter_scores)

        # Penalties and bonuses on full text
        score += penalty_consonant_runs(plain_buffer_full)
        score += penalty_repeated_plain_digrams(plain_buffer_full)
        score += bonus_endings(plain_buffer_full)

    # Score CORE blocks (if provided)
    if len(core_unique_pair_ids) > 0:
        decrypt_unique_pairs(core_unique_pair_ids, key, pos_buffer, decoded_unique_buffer_core)
        rebuild_plain(decoded_unique_buffer_core, core_inverse_unique_index, plain_buffer_core)

        score_core = score_quadgrams(plain_buffer_core, quad_scores)

        # Use inword scores for core if available
        if inword_scores is not None and w_inword > 0:
            score_core_inword = score_quadgrams(plain_buffer_core, inword_scores)
            score += w_core * score_core
            score += w_inword * score_core_inword
        else:
            score += w_core * score_core

    return score


@njit(cache=True)
def mutate_key(current_key, candidate_key, phase):
    """
    Generate candidate key by mutating current key.

    Args:
        current_key: uint8[25]
        candidate_key: uint8[25] output buffer
        phase: float in [0, 1] indicating annealing phase
    """
    # Copy current to candidate
    for i in range(25):
        candidate_key[i] = current_key[i]

    # Choose mutation type based on phase
    r = np.random.random()

    if phase < 0.5:
        # Warm phase - more diverse mutations
        if r < 0.45:
            # Swap two letters
            i, j = np.random.randint(0, 25), np.random.randint(0, 25)
            candidate_key[i], candidate_key[j] = candidate_key[j], candidate_key[i]

        elif r < 0.60:
            # Swap two rows
            row1, row2 = np.random.randint(0, 5), np.random.randint(0, 5)
            for col in range(5):
                idx1 = row1 * 5 + col
                idx2 = row2 * 5 + col
                candidate_key[idx1], candidate_key[idx2] = candidate_key[idx2], candidate_key[idx1]

        elif r < 0.75:
            # Swap two columns
            col1, col2 = np.random.randint(0, 5), np.random.randint(0, 5)
            for row in range(5):
                idx1 = row * 5 + col1
                idx2 = row * 5 + col2
                candidate_key[idx1], candidate_key[idx2] = candidate_key[idx2], candidate_key[idx1]

        elif r < 0.83:
            # Rotate a row
            row = np.random.randint(0, 5)
            shift = np.random.randint(1, 5)
            temp = np.empty(5, dtype=np.uint8)
            for col in range(5):
                temp[col] = candidate_key[row * 5 + col]
            for col in range(5):
                candidate_key[row * 5 + col] = temp[(col - shift) % 5]

        elif r < 0.91:
            # Reverse a row
            row = np.random.randint(0, 5)
            for col in range(5 // 2):
                idx1 = row * 5 + col
                idx2 = row * 5 + (4 - col)
                candidate_key[idx1], candidate_key[idx2] = candidate_key[idx2], candidate_key[idx1]

        elif r < 0.95:
            # Transpose matrix
            temp = np.empty(25, dtype=np.uint8)
            for i in range(25):
                temp[i] = candidate_key[i]
            for row in range(5):
                for col in range(5):
                    candidate_key[row * 5 + col] = temp[col * 5 + row]

        else:
            # Large jump - multiple swaps
            n_swaps = np.random.randint(3, 9)
            for _ in range(n_swaps):
                i, j = np.random.randint(0, 25), np.random.randint(0, 25)
                candidate_key[i], candidate_key[j] = candidate_key[j], candidate_key[i]

    else:
        # Cool phase - mostly letter swaps for fine-tuning
        if r < 0.85:
            # Swap two letters
            i, j = np.random.randint(0, 25), np.random.randint(0, 25)
            candidate_key[i], candidate_key[j] = candidate_key[j], candidate_key[i]

        elif r < 0.95:
            # Swap row or column
            if np.random.random() < 0.5:
                row1, row2 = np.random.randint(0, 5), np.random.randint(0, 5)
                for col in range(5):
                    idx1 = row1 * 5 + col
                    idx2 = row2 * 5 + col
                    candidate_key[idx1], candidate_key[idx2] = candidate_key[idx2], candidate_key[idx1]
            else:
                col1, col2 = np.random.randint(0, 5), np.random.randint(0, 5)
                for row in range(5):
                    idx1 = row * 5 + col1
                    idx2 = row * 5 + col2
                    candidate_key[idx1], candidate_key[idx2] = candidate_key[idx2], candidate_key[idx1]

        else:
            # Small jump
            n_swaps = np.random.randint(2, 4)
            for _ in range(n_swaps):
                i, j = np.random.randint(0, 25), np.random.randint(0, 25)
                candidate_key[i], candidate_key[j] = candidate_key[j], candidate_key[i]


@njit(cache=True)
def annealing_run(
    initial_key,
    seed,
    iters,
    T0,
    cooling,
    full_unique_pair_ids,
    full_inverse_unique_index,
    full_n_chars,
    core_unique_pair_ids,
    core_inverse_unique_index,
    core_n_chars,
    quad_scores,
    tri_scores,
    inword_scores,
    letter_scores,
    w_full,
    w_core,
    w_tri,
    w_inword,
    w_letter,
):
    """
    Run simulated annealing to find best key.

    Returns:
        best_key: uint8[25]
        best_score: float64
    """
    # Set random seed
    np.random.seed(seed)

    # Allocate buffers
    pos_buffer = np.empty(25, dtype=np.uint8)

    n_unique_full = len(full_unique_pair_ids)
    decoded_unique_buffer_full = np.empty(n_unique_full, dtype=np.uint16)
    plain_buffer_full = np.empty(full_n_chars, dtype=np.uint8)

    n_unique_core = len(core_unique_pair_ids)
    decoded_unique_buffer_core = np.empty(n_unique_core, dtype=np.uint16)
    plain_buffer_core = np.empty(core_n_chars, dtype=np.uint8)

    # Initialize keys
    current_key = np.empty(25, dtype=np.uint8)
    candidate_key = np.empty(25, dtype=np.uint8)
    best_key = np.empty(25, dtype=np.uint8)

    for i in range(25):
        current_key[i] = initial_key[i]
        best_key[i] = initial_key[i]

    # Evaluate initial key
    current_score = evaluate_key(
        current_key,
        full_unique_pair_ids, full_inverse_unique_index, full_n_chars,
        core_unique_pair_ids, core_inverse_unique_index, core_n_chars,
        quad_scores, tri_scores, inword_scores, letter_scores,
        w_full, w_core, w_tri, w_inword, w_letter,
        pos_buffer,
        decoded_unique_buffer_full, plain_buffer_full,
        decoded_unique_buffer_core, plain_buffer_core,
    )

    best_score = current_score

    # Annealing loop
    T = T0

    for iteration in range(iters):
        phase = iteration / iters

        # Generate candidate
        mutate_key(current_key, candidate_key, phase)

        # Evaluate candidate
        candidate_score = evaluate_key(
            candidate_key,
            full_unique_pair_ids, full_inverse_unique_index, full_n_chars,
            core_unique_pair_ids, core_inverse_unique_index, core_n_chars,
            quad_scores, tri_scores, inword_scores, letter_scores,
            w_full, w_core, w_tri, w_inword, w_letter,
            pos_buffer,
            decoded_unique_buffer_full, plain_buffer_full,
            decoded_unique_buffer_core, plain_buffer_core,
        )

        # Accept or reject
        delta = candidate_score - current_score

        if delta > 0:
            accept = True
        else:
            accept = np.random.random() < np.exp(delta / T)

        if accept:
            # Swap keys (reuse buffers)
            temp = current_key
            current_key = candidate_key
            candidate_key = temp
            current_score = candidate_score

            # Update best if improved
            if current_score > best_score:
                best_score = current_score
                for i in range(25):
                    best_key[i] = current_key[i]

        # Cool down
        T *= cooling

    return best_key, best_score

