"""
Boundary determination methods for curator classification changes.

Two methods:
  1. HMMER-based: Use Pfam HMM envelope coordinates to determine domain
     boundaries. Best when splitting domains at the junction of two distinct
     Pfam families (e.g., Kringle/WSC split, Change 2C).

  2. Pairwise alignment: Align each domain to a reference sequence to
     determine where the homologous region ends. Best for trimming
     over-extended domains (e.g., OSCP fix, Change 3B).
"""

import logging
import os
import re
import subprocess
import tempfile

from Bio.Align import PairwiseAligner

logger = logging.getLogger(__name__)

HMMER_BIN = '/data/ecod/hmmer-3.1b2/binaries'
HMMSCAN = os.path.join(HMMER_BIN, 'hmmscan')
HMMFETCH = os.path.join(HMMER_BIN, 'hmmfetch')
HMMPRESS = os.path.join(HMMER_BIN, 'hmmpress')
PFAM_HMM = os.path.expanduser('~/data/pfam/v38.2/Pfam-A.hmm')


# ============================================================
# Sequence extraction from the database
# ============================================================

def extract_domain_sequence(conn, domain_id, protein_id=None, range_definition=None):
    """Extract a domain's amino acid sequence from the protein sequence.

    Uses ecod_commons.protein_sequences and the domain's range_definition
    to extract the subsequence.

    Returns the domain amino acid sequence string, or None.
    """
    from psycopg2.extras import RealDictCursor

    # Look up domain info if not provided
    if protein_id is None or range_definition is None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT d.protein_id, d.range_definition
                FROM ecod_commons.domains d
                WHERE d.domain_id = %s AND d.is_obsolete = false
            """, (domain_id,))
            row = cur.fetchone()
            if not row:
                return None
            protein_id = row['protein_id']
            range_definition = row['range_definition']

    # Get full protein sequence
    with conn.cursor() as cur:
        cur.execute("""
            SELECT sequence FROM ecod_commons.protein_sequences
            WHERE protein_id = %s
        """, (protein_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        protein_seq = row[0]

    # Parse range and extract subsequence
    return _extract_subsequence(protein_seq, range_definition)


def _extract_subsequence(protein_seq, range_definition):
    """Extract a subsequence from a protein given a range definition.

    Handles formats like 'A:1-105', '296-385', '251-280,306-345'.
    Range coordinates are 1-based inclusive.
    """
    parts = []
    for segment in range_definition.split(','):
        segment = segment.strip()
        # Match optional chain prefix
        match = re.match(r'(?:[A-Za-z]+:)?(\d+)-(\d+)', segment)
        if not match:
            continue
        start = int(match.group(1))
        end = int(match.group(2))
        # Convert to 0-based for Python slicing
        subseq = protein_seq[start - 1:end]
        parts.append(subseq)

    return ''.join(parts) if parts else None


# ============================================================
# HMMER-based boundary determination (Change 2C)
# ============================================================

def get_hmmer_boundaries_from_db(conn, domain_id, pfam_accs):
    """Check swissprot.domain_hmmer_results for existing Pfam hits.

    Args:
        domain_id: ecod domain identifier (e.g., 'Q90Y90_nD1')
        pfam_accs: list of Pfam accessions to look for (e.g., ['PF00051', 'PF01822'])

    Returns:
        dict mapping pfam_acc -> {'env_start': int, 'env_end': int, 'evalue': float}
        or empty dict if no hits found.
        Coordinates are 1-based, domain-local.
    """
    from psycopg2.extras import RealDictCursor

    like_clauses = ' OR '.join(["dhr.pfam_acc LIKE %s"] * len(pfam_accs))
    params = [domain_id] + [f"{acc}%" for acc in pfam_accs]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT DISTINCT ON (dhr.pfam_acc)
                   dhr.pfam_acc, dhr.pfam_name,
                   dhr.env_start, dhr.env_end,
                   dhr.ali_start, dhr.ali_end,
                   dhr.domain_evalue
            FROM swissprot.domain sd
            JOIN swissprot.domain_hmmer_results dhr ON dhr.domain_id = sd.id
            WHERE sd.domain_id = %s
            AND ({like_clauses})
            AND dhr.is_significant = true
            ORDER BY dhr.pfam_acc, dhr.domain_evalue ASC
        """, params)

        results = {}
        for row in cur.fetchall():
            # Strip version from pfam_acc (e.g., 'PF00051.23' -> 'PF00051')
            base_acc = row['pfam_acc'].split('.')[0]
            results[base_acc] = {
                'env_start': row['env_start'],
                'env_end': row['env_end'],
                'ali_start': row['ali_start'],
                'ali_end': row['ali_end'],
                'evalue': float(row['domain_evalue']),
                'pfam_name': row['pfam_name'],
            }
        return results


def run_hmmscan_for_domain(sequence, pfam_names, domain_id='query'):
    """Run hmmscan against specific Pfam HMMs for a single sequence.

    Fetches individual HMMs from Pfam-A.hmm by name and scans the sequence.

    Args:
        sequence: amino acid sequence string
        pfam_names: list of Pfam HMM names (e.g., ['Kringle', 'WSC'])
        domain_id: identifier for the sequence (used in FASTA header)

    Returns:
        dict mapping pfam_acc -> {'env_start': int, 'env_end': int, 'evalue': float}
        Coordinates are 1-based, sequence-local.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write query sequence
        seq_file = os.path.join(tmpdir, 'query.fa')
        with open(seq_file, 'w') as f:
            f.write(f">{domain_id}\n{sequence}\n")

        # Fetch specific HMMs by name
        hmm_file = os.path.join(tmpdir, 'target.hmm')
        fetched = []
        for name in pfam_names:
            part = hmm_file + f'.{name}'
            result = subprocess.run(
                [HMMFETCH, '-o', part, PFAM_HMM, name],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                logger.warning("hmmfetch failed for %s: %s", name, result.stderr.strip())
            elif os.path.exists(part) and os.path.getsize(part) > 0:
                fetched.append(part)

        if not fetched:
            return {}

        # Concatenate HMMs
        with open(hmm_file, 'w') as outf:
            for part in fetched:
                with open(part) as inf:
                    outf.write(inf.read())

        # Press the combined HMM database
        subprocess.run(
            [HMMPRESS, hmm_file],
            capture_output=True, text=True,
        )

        # Run hmmscan
        domtbl_file = os.path.join(tmpdir, 'domtbl.out')
        result = subprocess.run(
            [HMMSCAN, '--domtblout', domtbl_file, '--noali',
             '-E', '1e-3', '--domE', '1e-3',
             hmm_file, seq_file],
            capture_output=True, text=True,
        )

        if result.returncode != 0:
            logger.warning("hmmscan failed for %s: %s", domain_id, result.stderr)
            return {}

        # Parse domtblout - accept all hits since we only fetched target HMMs
        return _parse_domtblout(domtbl_file)


def _parse_domtblout(domtbl_file):
    """Parse HMMER domtblout format, returning best hit per Pfam acc.

    Returns dict mapping pfam_acc (unversioned) -> {'env_start', 'env_end', 'evalue', 'pfam_name'}.
    """
    results = {}

    with open(domtbl_file) as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.split()
            if len(fields) < 23:
                continue

            # domtblout columns:
            # 0: target name (HMM name, e.g., 'Kringle')
            # 1: target accession (e.g., 'PF00051.24')
            # 2: tlen
            # 3: query name
            # ...
            # 12: domain c-evalue
            # 19: env_from
            # 20: env_to
            target_name = fields[0]
            target_acc = fields[1].split('.')[0]  # strip version

            evalue = float(fields[12])
            env_start = int(fields[19])
            env_end = int(fields[20])

            # Keep best (lowest e-value) hit per Pfam acc
            if target_acc not in results or evalue < results[target_acc]['evalue']:
                results[target_acc] = {
                    'env_start': env_start,
                    'env_end': env_end,
                    'evalue': evalue,
                    'pfam_name': target_name,
                }

    return results


def get_hmmer_boundaries(conn, domain_id, pfam_accs, pfam_names=None,
                         protein_id=None, range_definition=None):
    """Get HMMER boundaries for a domain, checking DB first, running hmmscan if needed.

    Args:
        conn: database connection
        domain_id: ecod domain identifier
        pfam_accs: list of Pfam accessions to look for (e.g., ['PF00051', 'PF01822'])
        pfam_names: list of Pfam HMM names for hmmscan fallback (e.g., ['Kringle', 'WSC']).
                    Required if DB lookup fails.
        protein_id: optional, for sequence extraction
        range_definition: optional, for sequence extraction

    Returns:
        dict mapping pfam_acc -> {'env_start': int, 'env_end': int, ...}
        Coordinates are 1-based, domain-local.
        Returns empty dict if no hits found.
    """
    # Try database first
    hits = get_hmmer_boundaries_from_db(conn, domain_id, pfam_accs)
    if hits:
        return hits

    if not pfam_names:
        logger.warning("No pfam_names provided for hmmscan fallback on %s", domain_id)
        return {}

    # Fall back to running hmmscan
    seq = extract_domain_sequence(conn, domain_id, protein_id, range_definition)
    if not seq:
        logger.warning("Could not extract sequence for %s", domain_id)
        return {}

    hits = run_hmmscan_for_domain(seq, pfam_names, domain_id)
    return hits


def domain_local_to_absolute(env_start, env_end, range_definition):
    """Convert domain-local coordinates (1-based) to absolute protein coordinates.

    Given a domain with range "296-385", local position 1 = residue 296.
    For multi-segment ranges like "251-280,306-345", walks through segments.

    Returns (chain, abs_start, abs_end) or None if out of range.
    chain is None for non-PDB ranges.
    """
    segments = []
    for part in range_definition.split(','):
        part = part.strip()
        match = re.match(r'([A-Za-z]+):(\d+)-(\d+)', part)
        if match:
            segments.append((match.group(1), int(match.group(2)), int(match.group(3))))
            continue
        match = re.match(r'(\d+)-(\d+)', part)
        if match:
            segments.append((None, int(match.group(1)), int(match.group(2))))

    if not segments:
        return None

    # Walk through segments to find absolute positions for env_start and env_end
    abs_start = _local_to_abs(segments, env_start)
    abs_end = _local_to_abs(segments, env_end)

    if abs_start is None or abs_end is None:
        return None

    return abs_start, abs_end


def _local_to_abs(segments, local_pos):
    """Convert a 1-based domain-local position to (chain, absolute_pos).

    Returns (chain, abs_pos) tuple.
    """
    residues_consumed = 0
    for chain, start, end in segments:
        seg_len = end - start + 1
        if residues_consumed + seg_len >= local_pos:
            offset = local_pos - residues_consumed - 1
            return (chain, start + offset)
        residues_consumed += seg_len
    return None


def format_absolute_range(start_info, end_info):
    """Format absolute coordinates back to a range string.

    start_info and end_info are (chain, pos) tuples from _local_to_abs.
    Handles single-segment output only (for split products that don't span gaps).
    """
    if start_info is None or end_info is None:
        return None

    chain_s, pos_s = start_info
    chain_e, pos_e = end_info

    if chain_s != chain_e:
        # Cross-segment range - for now, just use start chain
        logger.warning("Cross-chain range: %s:%d - %s:%d", chain_s, pos_s, chain_e, pos_e)

    if chain_s:
        return f"{chain_s}:{pos_s}-{pos_e}"
    else:
        return f"{pos_s}-{pos_e}"


# ============================================================
# Pairwise alignment boundary determination (Change 3B)
# ============================================================

def align_to_reference(reference_seq, query_seq):
    """Align a query domain to a reference using BioPython PairwiseAligner.

    Uses local alignment (Smith-Waterman style) so the reference can match
    a subset of the query, identifying where the homologous region is.

    Returns:
        dict with keys:
            'ref_start': 0-based start on reference
            'ref_end': 0-based end on reference (exclusive)
            'query_start': 0-based start on query
            'query_end': 0-based end on query (exclusive)
            'score': alignment score
            'query_aligned_length': number of query residues in aligned region
        or None if alignment fails.
    """
    aligner = PairwiseAligner()
    aligner.mode = 'local'
    # BLOSUM62-like scoring
    aligner.substitution_matrix = _get_blosum62()
    aligner.open_gap_score = -11
    aligner.extend_gap_score = -1

    alignments = aligner.align(reference_seq, query_seq)
    if not alignments:
        return None

    best = alignments[0]

    # Extract alignment coordinates
    # aligned is a list of (start, end) tuples for each sequence
    ref_aligned = best.aligned[0]  # reference coordinate blocks
    query_aligned = best.aligned[1]  # query coordinate blocks

    if len(ref_aligned) == 0 or len(query_aligned) == 0:
        return None

    ref_start = ref_aligned[0][0]
    ref_end = ref_aligned[-1][1]
    query_start = query_aligned[0][0]
    query_end = query_aligned[-1][1]

    # Count aligned query residues (excluding gaps)
    query_aligned_length = sum(end - start for start, end in query_aligned)

    return {
        'ref_start': ref_start,
        'ref_end': ref_end,
        'query_start': query_start,
        'query_end': query_end,
        'score': best.score,
        'query_aligned_length': query_aligned_length,
    }


_blosum62_cache = None

def _get_blosum62():
    """Load BLOSUM62 substitution matrix."""
    global _blosum62_cache
    if _blosum62_cache is None:
        from Bio.Align import substitution_matrices
        _blosum62_cache = substitution_matrices.load("BLOSUM62")
    return _blosum62_cache


def compute_cterminal_trim(reference_seq, query_seq, range_definition,
                           min_ref_coverage=0.5):
    """Determine C-terminal trim point for an over-extended domain.

    Aligns the query to the reference. The alignment endpoint on the query
    tells us where the homologous region ends. The original N-terminal
    start is preserved; only the C-terminus is trimmed.

    Args:
        reference_seq: reference domain sequence (e.g., e1abvA1 for OSCP)
        query_seq: over-extended domain sequence
        range_definition: original range string of the query domain
        min_ref_coverage: minimum fraction of reference covered by alignment
                          to consider the result reliable (default 0.5)

    Returns:
        (new_range_str, new_length, alignment_info) or (None, None, alignment_info)
        alignment_info includes a 'ref_coverage' field for confidence assessment.
    """
    aln = align_to_reference(reference_seq, query_seq)
    if aln is None:
        return None, None, None

    ref_len = len(reference_seq)
    ref_covered = aln['ref_end'] - aln['ref_start']
    aln['ref_coverage'] = ref_covered / ref_len

    # Check confidence: alignment should cover a substantial fraction of reference
    if aln['ref_coverage'] < min_ref_coverage:
        logger.warning("Low reference coverage (%.1f%%) for alignment to %s",
                        aln['ref_coverage'] * 100, range_definition)
        return None, None, aln

    segments = _parse_segments(range_definition)
    total_domain_length = sum(end - start + 1 for _, start, end in segments)

    # The C-terminal cutoff: where the alignment ends on the query (0-based exclusive)
    # Convert to 1-based domain-local position
    # Cast to int to avoid numpy.int64 issues with psycopg2
    query_end_local = int(aln['query_end'])  # 0-based exclusive = 1-based inclusive

    # Keep original N-terminal start, trim C-terminal to alignment end
    # New length = from domain start to alignment end
    new_length = query_end_local  # since domain starts at local pos 1

    if new_length >= total_domain_length:
        # Alignment says domain isn't actually over-extended
        return None, None, aln

    # Build new range: walk through segments, keeping up to new_length residues
    new_parts = []
    residues_remaining = new_length
    for chain, start, end in segments:
        seg_len = end - start + 1
        if residues_remaining <= 0:
            break
        if seg_len <= residues_remaining:
            new_parts.append(format_range_segment(chain, start, end))
            residues_remaining -= seg_len
        else:
            new_end = start + residues_remaining - 1
            new_parts.append(format_range_segment(chain, start, new_end))
            residues_remaining = 0

    new_range = ','.join(new_parts) if new_parts else None
    if new_range is None:
        return None, None, aln

    return new_range, new_length, aln


def format_range_segment(chain, start, end):
    """Format a single range segment."""
    if chain:
        return f"{chain}:{start}-{end}"
    return f"{start}-{end}"


def _parse_segments(range_definition):
    """Parse range definition into list of (chain, start, end) tuples."""
    segments = []
    for part in range_definition.split(','):
        part = part.strip()
        match = re.match(r'([A-Za-z]+):(\d+)-(\d+)', part)
        if match:
            segments.append((match.group(1), int(match.group(2)), int(match.group(3))))
            continue
        match = re.match(r'(\d+)-(\d+)', part)
        if match:
            segments.append((None, int(match.group(1)), int(match.group(2))))
    return segments
