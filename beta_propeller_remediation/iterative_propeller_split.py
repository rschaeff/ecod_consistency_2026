#!/usr/bin/env python3
"""
Iterative FoldSeek Splitting for Beta Propeller Domains

Identifies individual propeller domains within merged ECOD domain definitions
using iterative structural alignment against propeller templates.

Usage:
    python iterative_propeller_split.py <target_pdb> <template_pdb> [options]

Example:
    python iterative_propeller_split.py merged_domain.pdb wd40_template.pdb --min-tmscore 0.3
"""

import argparse
import subprocess
import os
import shutil
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple


@dataclass
class PropellerHit:
    """A detected propeller domain"""
    start: int
    end: int
    length: int
    tmscore: float
    aligned_length: int
    iteration: int


@dataclass
class SplitResult:
    """Results of iterative splitting"""
    target_file: str
    template_file: str
    original_residues: int
    domains_found: List[PropellerHit]
    total_coverage: int
    coverage_pct: float
    unmatched_residues: int


def run_foldseek(query_pdb: str, target_pdb: str, prefix: str,
                 work_dir: str = ".") -> Optional[dict]:
    """
    Run FoldSeek structural alignment.

    Returns dict with tstart, tend, tmscore, alnlen or None if no hit.
    """
    env = os.environ.copy()
    env.pop('OMP_PROC_BIND', None)  # Required for FoldSeek on SLURM

    prefix_path = os.path.join(work_dir, prefix)

    # Clean up previous runs
    for ext in ['', '_h', '_ss', '_ca', '.dbtype', '.index', '.lookup', '.source']:
        for p in ['q_db', 't_db', 'res_db']:
            try:
                os.remove(f'{prefix_path}_{p}{ext}')
            except FileNotFoundError:
                pass
    shutil.rmtree(f'{prefix_path}_tmp', ignore_errors=True)

    cmds = [
        f'foldseek createdb {query_pdb} {prefix_path}_q_db',
        f'foldseek createdb {target_pdb} {prefix_path}_t_db',
        f'foldseek search {prefix_path}_q_db {prefix_path}_t_db {prefix_path}_res_db {prefix_path}_tmp --exhaustive-search 1 -e inf -a',
        f'foldseek convertalis {prefix_path}_q_db {prefix_path}_t_db {prefix_path}_res_db {prefix_path}.m8 --format-output "query,target,fident,alnlen,qstart,qend,tstart,tend,evalue,bits,alntmscore"'
    ]

    for cmd in cmds:
        result = subprocess.run(
            cmd, shell=True, env=env,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None

    # Parse result
    try:
        with open(f'{prefix_path}.m8', 'r') as f:
            line = f.readline().strip()
            if line:
                parts = line.split('\t')
                return {
                    'tstart': int(parts[6]),
                    'tend': int(parts[7]),
                    'tmscore': float(parts[10]),
                    'alnlen': int(parts[3])
                }
    except (FileNotFoundError, IndexError, ValueError):
        pass

    return None


def extract_pdb_excluding_ranges(pdb_file: str, exclude_ranges: List[Tuple[int, int]],
                                  output_file: str) -> int:
    """
    Extract PDB atoms excluding specified residue ranges.

    Returns number of remaining residues.
    """
    with open(pdb_file, 'r') as f:
        lines = f.readlines()

    atoms = []
    for line in lines:
        if line.startswith('ATOM'):
            try:
                resnum = int(line[22:26])
                exclude = any(start <= resnum <= end for start, end in exclude_ranges)
                if not exclude:
                    atoms.append(line)
            except ValueError:
                continue

    with open(output_file, 'w') as f:
        for atom in atoms:
            f.write(atom)
        f.write('END\n')

    residues = set(int(a[22:26]) for a in atoms)
    return len(residues)


def count_residues(pdb_file: str) -> int:
    """Count unique residues in PDB file."""
    residues = set()
    with open(pdb_file, 'r') as f:
        for line in f:
            if line.startswith('ATOM'):
                try:
                    resnum = int(line[22:26])
                    residues.add(resnum)
                except ValueError:
                    continue
    return len(residues)


def iterative_split(target_pdb: str, template_pdb: str,
                    min_tmscore: float = 0.3,
                    min_aligned_length: int = 100,
                    min_remaining_residues: int = 100,
                    max_iterations: int = 10,
                    work_dir: str = ".",
                    verbose: bool = True) -> SplitResult:
    """
    Iteratively detect propeller domains in a merged structure.

    Args:
        target_pdb: Path to target PDB (merged domain)
        template_pdb: Path to template PDB (single propeller)
        min_tmscore: Minimum TM-score to accept a hit
        min_aligned_length: Minimum aligned residues to accept
        min_remaining_residues: Stop when fewer residues remain
        max_iterations: Maximum iterations
        work_dir: Working directory for temp files
        verbose: Print progress

    Returns:
        SplitResult with detected domains
    """
    os.makedirs(work_dir, exist_ok=True)

    original_residues = count_residues(target_pdb)
    matched_ranges: List[Tuple[int, int]] = []
    hits: List[PropellerHit] = []

    if verbose:
        print(f"Starting iterative split: {original_residues} residues")
        print(f"Parameters: min_TM={min_tmscore}, min_len={min_aligned_length}")
        print("-" * 60)

    for iteration in range(1, max_iterations + 1):
        # Create masked target if we have previous matches
        if matched_ranges:
            current_target = os.path.join(work_dir, f'target_iter{iteration}.pdb')
            remaining = extract_pdb_excluding_ranges(
                target_pdb, matched_ranges, current_target
            )
        else:
            current_target = target_pdb
            remaining = original_residues

        if verbose:
            print(f"Iteration {iteration}: {remaining} residues remaining")

        if remaining < min_remaining_residues:
            if verbose:
                print(f"  Too few residues remaining, stopping")
            break

        # Run FoldSeek
        hit = run_foldseek(
            template_pdb, current_target,
            f'iter{iteration}', work_dir
        )

        if hit is None:
            if verbose:
                print(f"  No hit found, stopping")
            break

        if verbose:
            print(f"  Hit: {hit['tstart']}-{hit['tend']}, "
                  f"TM={hit['tmscore']:.3f}, len={hit['alnlen']}")

        # Check thresholds
        if hit['tmscore'] < min_tmscore:
            if verbose:
                print(f"  TM-score below threshold, stopping")
            break

        if hit['alnlen'] < min_aligned_length:
            if verbose:
                print(f"  Alignment too short, stopping")
            break

        # Record hit
        matched_ranges.append((hit['tstart'], hit['tend']))
        hits.append(PropellerHit(
            start=hit['tstart'],
            end=hit['tend'],
            length=hit['tend'] - hit['tstart'] + 1,
            tmscore=hit['tmscore'],
            aligned_length=hit['alnlen'],
            iteration=iteration
        ))

    # Calculate coverage
    total_coverage = sum(h.length for h in hits)
    coverage_pct = 100 * total_coverage / original_residues if original_residues > 0 else 0

    result = SplitResult(
        target_file=target_pdb,
        template_file=template_pdb,
        original_residues=original_residues,
        domains_found=hits,
        total_coverage=total_coverage,
        coverage_pct=coverage_pct,
        unmatched_residues=original_residues - total_coverage
    )

    if verbose:
        print("-" * 60)
        print(f"RESULTS: {len(hits)} domains detected")
        for i, h in enumerate(hits, 1):
            print(f"  Domain {i}: {h.start}-{h.end} ({h.length} aa, TM={h.tmscore:.3f})")
        print(f"Coverage: {total_coverage}/{original_residues} ({coverage_pct:.1f}%)")

    return result


def cleanup_work_dir(work_dir: str):
    """Remove temporary files from work directory."""
    patterns = ['iter*', 'target_iter*', '*.m8']
    for pattern in patterns:
        import glob
        for f in glob.glob(os.path.join(work_dir, pattern)):
            try:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Iterative FoldSeek splitting for propeller domains'
    )
    parser.add_argument('target', help='Target PDB file (merged domain)')
    parser.add_argument('template', help='Template PDB file (single propeller)')
    parser.add_argument('--min-tmscore', type=float, default=0.3,
                        help='Minimum TM-score threshold (default: 0.3)')
    parser.add_argument('--min-length', type=int, default=100,
                        help='Minimum aligned length (default: 100)')
    parser.add_argument('--min-remaining', type=int, default=100,
                        help='Minimum remaining residues to continue (default: 100)')
    parser.add_argument('--max-iter', type=int, default=10,
                        help='Maximum iterations (default: 10)')
    parser.add_argument('--work-dir', default='./foldseek_work',
                        help='Working directory for temp files')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    parser.add_argument('--cleanup', action='store_true',
                        help='Remove temporary files after completion')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress progress output')

    args = parser.parse_args()

    # Verify files exist
    if not os.path.exists(args.target):
        print(f"Error: Target file not found: {args.target}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.template):
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    # Run splitting
    result = iterative_split(
        target_pdb=args.target,
        template_pdb=args.template,
        min_tmscore=args.min_tmscore,
        min_aligned_length=args.min_length,
        min_remaining_residues=args.min_remaining,
        max_iterations=args.max_iter,
        work_dir=args.work_dir,
        verbose=not args.quiet
    )

    # Output
    if args.json:
        output = {
            'target_file': result.target_file,
            'template_file': result.template_file,
            'original_residues': result.original_residues,
            'domains_found': [asdict(d) for d in result.domains_found],
            'total_coverage': result.total_coverage,
            'coverage_pct': result.coverage_pct,
            'unmatched_residues': result.unmatched_residues
        }
        print(json.dumps(output, indent=2))

    # Cleanup
    if args.cleanup:
        cleanup_work_dir(args.work_dir)

    return 0 if result.domains_found else 1


if __name__ == '__main__':
    sys.exit(main())
