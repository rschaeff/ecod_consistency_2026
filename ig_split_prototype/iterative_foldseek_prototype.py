#!/usr/bin/env python3
"""
Prototype: Iterative FoldSeek for Ig Domain Splitting

This script tests whether iterative structural alignment with FoldSeek can identify
individual Ig domains within merged/overlong domain definitions.

FoldSeek is ~20,000x faster than DALI while achieving similar sensitivity.

Test case: Q60ZN5_nD12 (740aa merged Ig domain, should be ~7 separate domains)
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Set, Optional
import subprocess


FOLDSEEK_BIN = "/sw/apps/Anaconda3-2023.09-0/bin/foldseek"


def get_domain_range(resids: List[int], gap_tolerance: int = None) -> str:
    """
    Calculate domain range with gap tolerance.
    Gap tolerance: max(5, len(resids) * 0.05)
    """
    if not resids:
        return ""

    resids = sorted(resids)

    if gap_tolerance is None:
        cutoff1 = 5
        cutoff2 = len(resids) * 0.05
        gap_tolerance = max(cutoff1, cutoff2)

    segs = []
    for resid in resids:
        if not segs:
            segs.append([resid])
        else:
            if resid > segs[-1][-1] + gap_tolerance:
                segs.append([resid])
            else:
                segs[-1].append(resid)

    seg_string = []
    for seg in segs:
        start = str(seg[0])
        end = str(seg[-1])
        seg_string.append(f"{start}-{end}")

    return ','.join(seg_string)


def range_to_residues(range_str: str) -> Set[int]:
    """Convert range string like '1-10,20-30' to set of residue numbers."""
    residues = set()
    for seg in range_str.split(','):
        if '-' in seg:
            parts = seg.split('-')
            start, end = int(parts[0]), int(parts[1])
            for r in range(start, end + 1):
                residues.add(r)
    return residues


def read_pdb_residues(pdb_path: Path) -> List[int]:
    """Read residue IDs from PDB file, preserving order."""
    resids = []
    seen = set()
    with open(pdb_path, 'r') as f:
        for line in f:
            if line.startswith('ATOM'):
                resid = int(line[22:26])
                if resid not in seen:
                    resids.append(resid)
                    seen.add(resid)
    return resids


def write_pdb_subset(input_pdb: Path, output_pdb: Path, keep_resids: Set[int]):
    """Write PDB with only specified residues."""
    with open(input_pdb, 'r') as fin:
        with open(output_pdb, 'w') as fout:
            for line in fin:
                if line.startswith('ATOM'):
                    resid = int(line[22:26])
                    if resid in keep_resids:
                        fout.write(line)
                elif line.startswith(('CRYST', 'END', 'TER')):
                    fout.write(line)


def run_foldseek_pairwise(query_pdb: Path, template_pdb: Path, work_dir: Path) -> Tuple[Optional[float], List[Tuple[int, int]], dict]:
    """
    Run FoldSeek pairwise alignment.

    Returns:
        Tuple of (score, alignments, stats) where:
        - score: TM-score or bit score
        - alignments: list of (query_resid, template_resid) pairs
        - stats: dict with additional alignment statistics
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous output
    for f in work_dir.glob("*"):
        try:
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)
        except:
            pass

    # Output file
    output_file = work_dir / "result.m8"

    # FoldSeek environment - must unset OMP_PROC_BIND (SLURM sets it)
    env = os.environ.copy()
    env.pop('OMP_PROC_BIND', None)

    # FoldSeek easy-search command
    # Output format: query,target,fident,alnlen,mismatch,gapopen,qstart,qend,tstart,tend,evalue,bits,alntmscore
    cmd = [
        FOLDSEEK_BIN, "easy-search",
        str(query_pdb),
        str(template_pdb),
        str(output_file),
        str(work_dir / "tmp"),
        "--format-output", "query,target,fident,alnlen,mismatch,gapopen,qstart,qend,tstart,tend,evalue,bits,alntmscore,qaln,taln",
        "-e", "10",  # E-value threshold (permissive)
        "--exhaustive-search", "1",  # More sensitive
        "-v", "0"  # Quiet
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            cwd=work_dir
        )

        if result.returncode != 0:
            print(f"  FoldSeek error: {result.stderr[:200] if result.stderr else 'unknown'}")

        # Parse output
        if not output_file.exists():
            return None, [], {}

        with open(output_file, 'r') as f:
            lines = f.readlines()

        if not lines:
            return None, [], {}

        # Parse first (best) hit
        parts = lines[0].strip().split('\t')
        if len(parts) < 15:
            return None, [], {}

        # Extract fields
        fident = float(parts[2])  # Fraction identity
        alnlen = int(parts[3])    # Alignment length
        qstart = int(parts[6])    # Query start (1-based)
        qend = int(parts[7])      # Query end
        tstart = int(parts[8])    # Target start
        tend = int(parts[9])      # Target end
        evalue = float(parts[10])
        bits = float(parts[11])
        alntmscore = float(parts[12]) if parts[12] else 0.0
        qaln = parts[13] if len(parts) > 13 else ""  # Query alignment string
        taln = parts[14] if len(parts) > 14 else ""  # Target alignment string

        stats = {
            'fident': fident,
            'alnlen': alnlen,
            'qstart': qstart,
            'qend': qend,
            'tstart': tstart,
            'tend': tend,
            'evalue': evalue,
            'bits': bits,
            'tmscore': alntmscore
        }

        # Build alignment from alignment strings
        alignments = []
        if qaln and taln and len(qaln) == len(taln):
            q_pos = qstart
            t_pos = tstart
            for q_char, t_char in zip(qaln, taln):
                if q_char != '-' and t_char != '-':
                    alignments.append((q_pos, t_pos))
                if q_char != '-':
                    q_pos += 1
                if t_char != '-':
                    t_pos += 1
        else:
            # Fallback: assume ungapped alignment
            for i in range(min(qend - qstart + 1, tend - tstart + 1)):
                alignments.append((qstart + i, tstart + i))

        return alntmscore, alignments, stats

    except subprocess.TimeoutExpired:
        print("  WARNING: FoldSeek timed out")
        return None, [], {}
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, [], {}


def iterative_foldseek_split(
    domain_pdb: Path,
    template_pdb: Path,
    output_dir: Path,
    min_aligned: int = 20,
    min_remaining: int = 20,
    min_tmscore: float = 0.3,
    max_iterations: int = 20
) -> List[dict]:
    """
    Run iterative FoldSeek to identify individual domain repeats.

    Algorithm:
    1. Align domain against template
    2. If significant hit found, record boundaries
    3. Remove aligned residues from domain
    4. Repeat until no more hits

    Returns:
        List of identified domain regions with boundaries
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use short path for FoldSeek work directory
    work_base = Path("/tmp/foldseek_iter")
    if work_base.exists():
        shutil.rmtree(work_base)
    work_base.mkdir()

    # Copy domain PDB to working file
    work_pdb = output_dir / "query_working.pdb"
    shutil.copy(domain_pdb, work_pdb)

    # Get ordered list of residue IDs in the domain
    all_resids = read_pdb_residues(domain_pdb)

    current_resids = set(all_resids)
    hits = []
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")
        print(f"Current residues: {len(current_resids)}")

        if len(current_resids) < min_remaining:
            print(f"Stopping: fewer than {min_remaining} residues remaining")
            break

        # Create iteration work directory
        iter_dir = work_base / f"i{iteration}"
        iter_dir.mkdir()

        # Run FoldSeek
        tmscore, alignments, stats = run_foldseek_pairwise(work_pdb, template_pdb, iter_dir)

        if stats:
            print(f"FoldSeek result: TM={tmscore:.3f}, alnlen={stats.get('alnlen', 0)}, "
                  f"E={stats.get('evalue', 'N/A'):.2e}, bits={stats.get('bits', 0):.1f}")
        else:
            print(f"FoldSeek result: no hit")

        if tmscore is None or tmscore < min_tmscore:
            print(f"Stopping: no significant alignment (TM={tmscore}, min={min_tmscore})")
            break

        if len(alignments) < min_aligned:
            print(f"Stopping: too few aligned residues ({len(alignments)} < {min_aligned})")
            break

        # Map alignment positions to actual residue numbers
        # FoldSeek uses 1-based positions into the current PDB
        current_resids_ordered = read_pdb_residues(work_pdb)

        aligned_resids = []
        for q_idx, t_idx in alignments:
            if 1 <= q_idx <= len(current_resids_ordered):
                actual_resid = current_resids_ordered[q_idx - 1]
                aligned_resids.append(actual_resid)

        if not aligned_resids:
            print("ERROR: Could not map aligned residues")
            break

        hit_range = get_domain_range(aligned_resids)

        hit = {
            'iteration': iteration,
            'tmscore': tmscore,
            'n_aligned': len(alignments),
            'range': hit_range,
            'resids': sorted(aligned_resids),
            'stats': stats
        }
        hits.append(hit)

        print(f"HIT {iteration}: TM={tmscore:.3f}, n={len(alignments)}, range={hit_range}")

        # Expand range to include gaps, then remove
        resids_to_remove = range_to_residues(hit_range)

        remaining_resids = current_resids - resids_to_remove
        print(f"Removing {len(resids_to_remove)} residues, {len(remaining_resids)} remaining")

        if len(remaining_resids) < min_remaining:
            print(f"Stopping: fewer than {min_remaining} residues would remain")
            break

        # Write new PDB with only remaining residues
        temp_pdb = output_dir / "query_temp.pdb"
        write_pdb_subset(work_pdb, temp_pdb, remaining_resids)
        shutil.move(str(temp_pdb), str(work_pdb))
        current_resids = remaining_resids

        # Clean up iteration directory
        shutil.rmtree(iter_dir, ignore_errors=True)

    return hits


def main():
    # Paths for test case
    domain_pdb = Path("/data/ecod/af2_pdb_domain_data/40829/004082943/004082943.pdb")  # Q60ZN5_nD12
    template_pdb = Path("/home/rschaeff/data/dpam_reference/ecod_data/ECOD70/000327604.pdb")  # e2o5nA1 (Ig)
    output_dir = Path("/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/output_foldseek")

    print("=" * 70)
    print("ITERATIVE FOLDSEEK IG DOMAIN SPLITTING PROTOTYPE")
    print("=" * 70)
    print(f"Domain: Q60ZN5_nD12")
    print(f"Template: e2o5nA1 (Ig domain)")
    print(f"FoldSeek: {FOLDSEEK_BIN}")

    # Verify files exist
    for p, name in [(domain_pdb, "Domain"), (template_pdb, "Template")]:
        if not p.exists():
            print(f"ERROR: {name} not found: {p}")
            sys.exit(1)

    if not Path(FOLDSEEK_BIN).exists():
        print(f"ERROR: FoldSeek not found: {FOLDSEEK_BIN}")
        sys.exit(1)

    # Get domain info
    resids = read_pdb_residues(domain_pdb)
    print(f"\nDomain: {len(resids)} residues ({min(resids)}-{max(resids)})")

    template_resids = read_pdb_residues(template_pdb)
    print(f"Template: {len(template_resids)} residues")

    expected = len(resids) // len(template_resids)
    print(f"Expected ~{expected} Ig domains")

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Run iterative FoldSeek
    print("\n" + "=" * 70)
    print("STARTING ITERATIVE FOLDSEEK")
    print("=" * 70)

    import time
    start_time = time.time()

    hits = iterative_foldseek_split(domain_pdb, template_pdb, output_dir)

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Ig domains identified: {len(hits)}")
    print(f"Expected: ~{expected}")
    print(f"Time elapsed: {elapsed:.1f} seconds")

    if hits:
        print("\nIdentified domains:")
        total_covered = set()
        for hit in hits:
            print(f"  {hit['iteration']}: TM={hit['tmscore']:.3f}, n={hit['n_aligned']}, range={hit['range']}")
            total_covered.update(hit['resids'])

        coverage = len(total_covered) / len(resids) * 100
        print(f"\nCoverage: {len(total_covered)}/{len(resids)} ({coverage:.1f}%)")

    # Save results
    results_file = output_dir / "results.txt"
    with open(results_file, 'w') as f:
        f.write("# Iterative FoldSeek Ig Domain Splitting Results\n")
        f.write(f"# Domain: Q60ZN5_nD12 ({len(resids)}aa)\n")
        f.write(f"# Template: e2o5nA1 ({len(template_resids)}aa)\n")
        f.write(f"# Expected: ~{expected} domains\n")
        f.write(f"# Found: {len(hits)} domains\n")
        f.write(f"# Time: {elapsed:.1f} seconds\n\n")

        for hit in hits:
            f.write(f"Domain {hit['iteration']}:\n")
            f.write(f"  TM-score: {hit['tmscore']:.3f}\n")
            f.write(f"  Aligned: {hit['n_aligned']}\n")
            f.write(f"  Range: {hit['range']}\n")
            if hit.get('stats'):
                f.write(f"  E-value: {hit['stats'].get('evalue', 'N/A')}\n")
                f.write(f"  Bits: {hit['stats'].get('bits', 'N/A')}\n")
            f.write("\n")

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
