#!/usr/bin/env python3
"""
Prototype: Iterative DALI for Ig Domain Splitting

This script tests whether iterative structural alignment can identify
individual Ig domains within merged/overlong domain definitions.

Based on DPAM approach with DaliLite.v5.

Test case: Q60ZN5_nD12 (740aa merged Ig domain, should be ~7 separate domains)
"""

import os
import sys
import shutil
import re
from pathlib import Path
from typing import List, Tuple, Set, Optional
import subprocess


DALI_BIN = Path("/home/rschaeff/src/Dali_v5/DaliLite.v5/bin/dali.pl")


def get_domain_range(resids: List[int], gap_tolerance: int = None) -> str:
    """
    Calculate domain range with gap tolerance (from DPAM v1.0).
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


def parse_dali_txt(txt_file: Path) -> Tuple[Optional[float], List[Tuple[int, int]]]:
    """
    Parse DALI mol*.txt output file.

    Returns:
        Tuple of (z_score, alignments) where alignments is list of (query_idx, template_idx)
        Note: indices are 1-based internal positions, not actual residue numbers
    """
    if not txt_file.exists():
        return None, []

    with open(txt_file, 'r') as f:
        content = f.read()

    z_score = None
    alignments = []

    for line in content.split('\n'):
        words = line.split()

        # Parse Z-score from hit line
        # Format: "   1:  mol2-A  3.0  3.5   66    92    3"
        if len(words) >= 3 and words[0].endswith(':') and '<=>' not in line:
            if words[0].rstrip(':') == '1':
                try:
                    z_score = float(words[2])
                except (ValueError, IndexError):
                    pass

        # Parse structural equivalences
        # Format: "   1: mol1-A mol2-A     9 -  20 <=>    9 -  20"
        elif '<=>' in line and len(words) >= 10:
            try:
                arrow_idx = words.index('<=>')
                # Query range
                q_start = int(words[3])
                q_end = int(words[5])
                # Template range
                t_start = int(words[arrow_idx + 1])
                t_end = int(words[arrow_idx + 3])

                q_len = q_end - q_start + 1
                t_len = t_end - t_start + 1

                if q_len == t_len:
                    for i in range(q_len):
                        alignments.append((q_start + i, t_start + i))
            except (ValueError, IndexError):
                pass

    return z_score, alignments


def run_dali_pairwise(query_pdb: Path, template_pdb: Path, work_dir: Path) -> Tuple[Optional[float], List[Tuple[int, int]]]:
    """
    Run DALI pairwise alignment using DaliLite.v5.
    Uses short paths to avoid 80-char limit.

    Returns:
        Tuple of (z_score, alignments) where alignments uses internal indices
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous output
    for pattern in ['mol*.txt', 'mol*.dccp', 'mol*.dat', '*.dssp', '*.puu', 'dali.lock']:
        for f in work_dir.glob(pattern):
            try:
                f.unlink()
            except:
                pass

    # Copy files to work_dir with short names (80-char limit)
    query_local = work_dir / "q.pdb"
    template_local = work_dir / "t.pdb"
    shutil.copy(query_pdb, query_local)
    shutil.copy(template_pdb, template_local)

    orig_dir = os.getcwd()
    os.chdir(work_dir)

    try:
        cmd = [
            "perl", str(DALI_BIN),
            "--pdbfile1", "q.pdb",
            "--pdbfile2", "t.pdb",
            "--dat1", ".",
            "--dat2", ".",
            "--clean"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        # Parse output
        txt_files = list(work_dir.glob("mol*.txt"))
        if txt_files:
            z_score, alignments = parse_dali_txt(txt_files[0])
            return z_score, alignments

        return None, []

    except subprocess.TimeoutExpired:
        print("  WARNING: DALI timed out")
        return None, []
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, []
    finally:
        os.chdir(orig_dir)


def iterative_dali_split(
    domain_pdb: Path,
    template_pdb: Path,
    output_dir: Path,
    min_aligned: int = 20,
    min_remaining: int = 20,
    min_zscore: float = 2.0,
    max_iterations: int = 20
) -> List[dict]:
    """
    Run iterative DALI to identify individual domain repeats.

    Algorithm:
    1. Align domain against template
    2. If significant hit found, record boundaries
    3. Remove aligned residues from domain
    4. Repeat until no more hits

    Returns:
        List of identified domain regions with boundaries
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use short path for DALI work directory
    work_base = Path("/tmp/dali_iter")
    work_base.mkdir(exist_ok=True)

    # Copy domain PDB to working file
    work_pdb = output_dir / "query_working.pdb"
    shutil.copy(domain_pdb, work_pdb)

    # Get ordered list of residue IDs in the domain
    all_resids = read_pdb_residues(domain_pdb)
    resid_to_idx = {r: i+1 for i, r in enumerate(all_resids)}  # 1-based
    idx_to_resid = {i+1: r for i, r in enumerate(all_resids)}

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

        # Create iteration work directory with short path
        iter_dir = work_base / f"i{iteration}"
        if iter_dir.exists():
            shutil.rmtree(iter_dir)
        iter_dir.mkdir()

        # Run DALI
        z_score, alignments = run_dali_pairwise(work_pdb, template_pdb, iter_dir)

        print(f"DALI result: z={z_score}, n_aligned={len(alignments)}")

        if z_score is None or z_score < min_zscore:
            print(f"Stopping: no significant alignment (z={z_score}, min={min_zscore})")
            break

        if len(alignments) < min_aligned:
            print(f"Stopping: too few aligned residues ({len(alignments)} < {min_aligned})")
            break

        # Map internal indices back to actual residue numbers
        # The alignment uses internal 1-based indices into the CURRENT working PDB
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
            'z_score': z_score,
            'n_aligned': len(alignments),
            'range': hit_range,
            'resids': sorted(aligned_resids)
        }
        hits.append(hit)

        print(f"HIT {iteration}: z={z_score:.1f}, n={len(alignments)}, range={hit_range}")

        # Expand range to include gaps, then remove
        resids_to_remove = range_to_residues(hit_range)

        remaining_resids = current_resids - resids_to_remove
        print(f"Removing {len(resids_to_remove)} residues, {len(remaining_resids)} remaining")

        if len(remaining_resids) < min_remaining:
            print(f"Stopping: fewer than {min_remaining} residues would remain")
            break

        # Write new PDB with only remaining residues
        # Must use temp file to avoid reading/writing same file
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
    output_dir = Path("/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/output")

    print("=" * 70)
    print("ITERATIVE DALI IG DOMAIN SPLITTING PROTOTYPE")
    print("=" * 70)
    print(f"Domain: Q60ZN5_nD12")
    print(f"Template: e2o5nA1 (Ig domain)")
    print(f"DALI: {DALI_BIN}")

    # Verify files exist
    for p, name in [(domain_pdb, "Domain"), (template_pdb, "Template"), (DALI_BIN, "DALI")]:
        if not p.exists():
            print(f"ERROR: {name} not found: {p}")
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

    # Run iterative DALI
    print("\n" + "=" * 70)
    print("STARTING ITERATIVE DALI")
    print("=" * 70)

    hits = iterative_dali_split(domain_pdb, template_pdb, output_dir)

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Ig domains identified: {len(hits)}")
    print(f"Expected: ~{expected}")

    if hits:
        print("\nIdentified domains:")
        total_covered = set()
        for hit in hits:
            print(f"  {hit['iteration']}: z={hit['z_score']:.1f}, n={hit['n_aligned']}, range={hit['range']}")
            total_covered.update(hit['resids'])

        coverage = len(total_covered) / len(resids) * 100
        print(f"\nCoverage: {len(total_covered)}/{len(resids)} ({coverage:.1f}%)")

    # Save results
    results_file = output_dir / "results.txt"
    with open(results_file, 'w') as f:
        f.write("# Iterative DALI Ig Domain Splitting Results\n")
        f.write(f"# Domain: Q60ZN5_nD12 ({len(resids)}aa)\n")
        f.write(f"# Template: e2o5nA1 ({len(template_resids)}aa)\n")
        f.write(f"# Expected: ~{expected} domains\n")
        f.write(f"# Found: {len(hits)} domains\n\n")

        for hit in hits:
            f.write(f"Domain {hit['iteration']}:\n")
            f.write(f"  Z-score: {hit['z_score']:.1f}\n")
            f.write(f"  Aligned: {hit['n_aligned']}\n")
            f.write(f"  Range: {hit['range']}\n\n")

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
