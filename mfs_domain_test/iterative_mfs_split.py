#!/usr/bin/env python3
"""
Iterative FoldSeek Splitting for LIM Domains

Identifies individual LIM domains within merged domain definitions.
Fixes the position-to-residue mapping issue for proper iterative masking.
"""

import subprocess
import os
import shutil
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set


@dataclass
class DomainHit:
    """A detected domain"""
    start: int  # PDB residue number
    end: int    # PDB residue number
    length: int
    tmscore: float
    aligned_length: int
    iteration: int


def run_foldseek(query_pdb: str, target_pdb: str, prefix: str,
                 work_dir: str = ".") -> Optional[dict]:
    """Run FoldSeek structural alignment."""
    env = os.environ.copy()
    env.pop('OMP_PROC_BIND', None)

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
        result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            return None

    try:
        with open(f'{prefix_path}.m8', 'r') as f:
            line = f.readline().strip()
            if line:
                parts = line.split('\t')
                return {
                    'tstart': int(parts[6]),  # 1-indexed position in target
                    'tend': int(parts[7]),
                    'tmscore': float(parts[10]),
                    'alnlen': int(parts[3])
                }
    except (FileNotFoundError, IndexError, ValueError):
        pass

    return None


def get_residue_list(pdb_file: str) -> List[int]:
    """Get ordered list of residue numbers in PDB file."""
    residues = set()
    with open(pdb_file, 'r') as f:
        for line in f:
            if line.startswith('ATOM'):
                try:
                    resnum = int(line[22:26])
                    residues.add(resnum)
                except ValueError:
                    continue
    return sorted(residues)


def extract_pdb_excluding_residues(pdb_file: str, exclude_residues: Set[int],
                                    output_file: str) -> List[int]:
    """Extract PDB atoms excluding specified residues. Returns list of kept residue numbers."""
    with open(pdb_file, 'r') as f:
        lines = f.readlines()

    kept_residues = set()
    with open(output_file, 'w') as f:
        for line in lines:
            if line.startswith('ATOM'):
                try:
                    resnum = int(line[22:26])
                    if resnum not in exclude_residues:
                        f.write(line)
                        kept_residues.add(resnum)
                except ValueError:
                    continue
        f.write('END\n')

    return sorted(kept_residues)


def position_to_residue(position: int, residue_list: List[int]) -> int:
    """Convert 1-indexed position to actual residue number."""
    if 1 <= position <= len(residue_list):
        return residue_list[position - 1]
    raise ValueError(f"Position {position} out of range [1, {len(residue_list)}]")


def iterative_split(target_pdb: str, template_pdb: str,
                    min_tmscore: float = 0.3,
                    min_aligned_length: int = 25,
                    min_remaining_residues: int = 25,
                    max_iterations: int = 10,
                    work_dir: str = ".",
                    verbose: bool = True):
    """Iteratively detect domains in a merged structure."""
    os.makedirs(work_dir, exist_ok=True)

    # Get original residue list
    original_residues = get_residue_list(target_pdb)
    excluded_residues: Set[int] = set()
    hits: List[DomainHit] = []

    if verbose:
        print(f"Starting iterative split: {len(original_residues)} residues")
        print(f"Residue range: {min(original_residues)}-{max(original_residues)}")
        print(f"Parameters: min_TM={min_tmscore}, min_len={min_aligned_length}")
        print("-" * 60)

    for iteration in range(1, max_iterations + 1):
        # Create masked target
        if excluded_residues:
            current_target = os.path.join(work_dir, f'target_iter{iteration}.pdb')
            current_residues = extract_pdb_excluding_residues(
                target_pdb, excluded_residues, current_target
            )
        else:
            current_target = target_pdb
            current_residues = original_residues

        remaining = len(current_residues)

        if verbose:
            print(f"Iteration {iteration}: {remaining} residues remaining")

        if remaining < min_remaining_residues:
            if verbose:
                print(f"  Too few residues remaining, stopping")
            break

        # Run FoldSeek
        hit = run_foldseek(template_pdb, current_target, f'iter{iteration}', work_dir)

        if hit is None:
            if verbose:
                print(f"  No hit found, stopping")
            break

        # Convert positions to residue numbers
        try:
            res_start = position_to_residue(hit['tstart'], current_residues)
            res_end = position_to_residue(hit['tend'], current_residues)
        except ValueError as e:
            if verbose:
                print(f"  Position conversion error: {e}")
            break

        if verbose:
            print(f"  Hit: positions {hit['tstart']}-{hit['tend']} -> "
                  f"residues {res_start}-{res_end}, TM={hit['tmscore']:.3f}, len={hit['alnlen']}")

        # Check thresholds
        if hit['tmscore'] < min_tmscore:
            if verbose:
                print(f"  TM-score below threshold, stopping")
            break

        if hit['alnlen'] < min_aligned_length:
            if verbose:
                print(f"  Alignment too short, stopping")
            break

        # Record hit and exclude these residues
        hit_residues = set(r for r in current_residues if res_start <= r <= res_end)
        excluded_residues.update(hit_residues)

        hits.append(DomainHit(
            start=res_start,
            end=res_end,
            length=len(hit_residues),
            tmscore=hit['tmscore'],
            aligned_length=hit['alnlen'],
            iteration=iteration
        ))

    # Calculate coverage
    total_coverage = sum(h.length for h in hits)
    coverage_pct = 100 * total_coverage / len(original_residues)

    if verbose:
        print("-" * 60)
        print(f"RESULTS: {len(hits)} domains detected")
        for i, h in enumerate(hits, 1):
            print(f"  Domain {i}: {h.start}-{h.end} ({h.length} aa, TM={h.tmscore:.3f})")
        print(f"Coverage: {total_coverage}/{len(original_residues)} ({coverage_pct:.1f}%)")
        print(f"Unmatched: {len(original_residues) - total_coverage} residues")

    return {
        'original_residues': len(original_residues),
        'domains': hits,
        'total_coverage': total_coverage,
        'coverage_pct': coverage_pct
    }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python iterative_lim_split.py <target_pdb> <template_pdb>")
        sys.exit(1)

    result = iterative_split(
        sys.argv[1], sys.argv[2],
        min_tmscore=0.3,
        min_aligned_length=25,
        min_remaining_residues=25,
        work_dir='./foldseek_work'
    )
