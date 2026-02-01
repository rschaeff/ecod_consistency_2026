#!/usr/bin/env python3
"""Evaluate F-group consistency from CLANS embeddings.

Computes centroid distances and consistency metrics for each H-group.
"""

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from parse_clans import parse_clans_file, ClansData, validate_clans_data


@dataclass
class DomainResult:
    """Consistency result for a single domain."""
    domain_name: str
    ecod_uid: int
    f_group_id: str
    own_centroid_distance: float
    nearest_other_centroid: str
    nearest_other_distance: float
    distance_ratio: float  # own/nearest_other, <1 means consistent
    silhouette: float  # silhouette coefficient for this domain
    is_consistent: bool


@dataclass
class FGroupResult:
    """Summary for an F-group."""
    f_group_id: str
    domain_count: int
    centroid: List[float]
    mean_intra_distance: float  # mean distance to own centroid
    std_intra_distance: float
    consistent_count: int
    consistency_rate: float


@dataclass
class HGroupResult:
    """Complete evaluation result for an H-group."""
    h_group_id: str
    total_domains: int
    f_group_count: int
    overall_consistency_rate: float
    mean_silhouette: float
    f_groups: List[FGroupResult]
    inconsistent_domains: List[DomainResult]
    warnings: List[str]


def compute_centroid(coordinates: np.ndarray) -> np.ndarray:
    """Compute centroid of a set of points."""
    return np.mean(coordinates, axis=0)


def compute_distances(points: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    """Compute Euclidean distances from points to centroid."""
    return np.linalg.norm(points - centroid, axis=1)


def compute_silhouette(domain_idx: int, own_fgroup_indices: List[int],
                       other_fgroup_indices: Dict[str, List[int]],
                       coordinates: np.ndarray) -> float:
    """Compute silhouette coefficient for a single domain.

    silhouette = (b - a) / max(a, b)
    where:
        a = mean distance to other points in same cluster
        b = mean distance to points in nearest other cluster
    """
    point = coordinates[domain_idx]

    # Compute a: mean intra-cluster distance
    own_indices = [i for i in own_fgroup_indices if i != domain_idx]
    if not own_indices:
        return 0.0  # Single-member cluster

    own_distances = np.linalg.norm(coordinates[own_indices] - point, axis=1)
    a = np.mean(own_distances)

    # Compute b: mean distance to nearest other cluster
    if not other_fgroup_indices:
        return 0.0  # Only one cluster

    b = float('inf')
    for fg, indices in other_fgroup_indices.items():
        if indices:
            other_distances = np.linalg.norm(coordinates[indices] - point, axis=1)
            mean_dist = np.mean(other_distances)
            b = min(b, mean_dist)

    if b == float('inf'):
        return 0.0

    # Silhouette coefficient
    return (b - a) / max(a, b)


def evaluate_hgroup(data: ClansData, h_group_id: str) -> HGroupResult:
    """Evaluate F-group consistency for an H-group.

    Args:
        data: Parsed CLANS data
        h_group_id: H-group identifier for reporting

    Returns:
        HGroupResult with complete evaluation
    """
    warnings = validate_clans_data(data)
    coordinates = data.coordinates
    f_groups = data.f_groups

    # Compute centroids for each F-group
    centroids: Dict[str, np.ndarray] = {}
    fgroup_indices: Dict[str, List[int]] = {}

    for fg in f_groups:
        indices = data.get_indices_by_fgroup(fg)
        fgroup_indices[fg] = indices
        if indices:
            centroids[fg] = compute_centroid(coordinates[indices])

    # Evaluate each domain
    domain_results: List[DomainResult] = []
    fgroup_results: Dict[str, dict] = {fg: {
        'distances': [],
        'consistent': 0,
        'total': 0
    } for fg in f_groups}

    for domain in data.domains:
        fg = domain.f_group_id
        point = coordinates[domain.index]

        # Distance to own centroid
        own_dist = float(np.linalg.norm(point - centroids[fg]))

        # Distance to other centroids
        other_distances = {}
        for other_fg, centroid in centroids.items():
            if other_fg != fg:
                other_distances[other_fg] = float(np.linalg.norm(point - centroid))

        # Find nearest other centroid
        if other_distances:
            nearest_fg = min(other_distances, key=other_distances.get)
            nearest_dist = other_distances[nearest_fg]
        else:
            nearest_fg = "none"
            nearest_dist = float('inf')

        # Compute ratio and consistency
        if nearest_dist > 0:
            ratio = own_dist / nearest_dist
        else:
            ratio = float('inf')

        is_consistent = ratio < 1.0

        # Compute silhouette
        other_indices = {k: v for k, v in fgroup_indices.items() if k != fg}
        silhouette = compute_silhouette(
            domain.index, fgroup_indices[fg], other_indices, coordinates
        )

        result = DomainResult(
            domain_name=domain.name,
            ecod_uid=domain.ecod_uid,
            f_group_id=fg,
            own_centroid_distance=own_dist,
            nearest_other_centroid=nearest_fg,
            nearest_other_distance=nearest_dist,
            distance_ratio=ratio,
            silhouette=silhouette,
            is_consistent=is_consistent
        )
        domain_results.append(result)

        # Accumulate F-group stats
        fgroup_results[fg]['distances'].append(own_dist)
        fgroup_results[fg]['total'] += 1
        if is_consistent:
            fgroup_results[fg]['consistent'] += 1

    # Build F-group summaries
    fgroup_summaries = []
    for fg in f_groups:
        stats = fgroup_results[fg]
        distances = np.array(stats['distances'])

        fgroup_summaries.append(FGroupResult(
            f_group_id=fg,
            domain_count=stats['total'],
            centroid=centroids[fg].tolist(),
            mean_intra_distance=float(np.mean(distances)) if len(distances) > 0 else 0,
            std_intra_distance=float(np.std(distances)) if len(distances) > 0 else 0,
            consistent_count=stats['consistent'],
            consistency_rate=stats['consistent'] / stats['total'] if stats['total'] > 0 else 0
        ))

    # Compute overall metrics
    total_consistent = sum(1 for r in domain_results if r.is_consistent)
    overall_consistency = total_consistent / len(domain_results) if domain_results else 0
    mean_silhouette = float(np.mean([r.silhouette for r in domain_results])) if domain_results else 0

    # Get inconsistent domains (sorted by worst ratio)
    inconsistent = [r for r in domain_results if not r.is_consistent]
    inconsistent.sort(key=lambda x: x.distance_ratio, reverse=True)

    return HGroupResult(
        h_group_id=h_group_id,
        total_domains=len(data.domains),
        f_group_count=len(f_groups),
        overall_consistency_rate=overall_consistency,
        mean_silhouette=mean_silhouette,
        f_groups=fgroup_summaries,
        inconsistent_domains=inconsistent,
        warnings=warnings
    )


def result_to_dict(result: HGroupResult) -> dict:
    """Convert result to JSON-serializable dict."""
    return {
        'h_group_id': result.h_group_id,
        'total_domains': result.total_domains,
        'f_group_count': result.f_group_count,
        'overall_consistency_rate': result.overall_consistency_rate,
        'mean_silhouette': result.mean_silhouette,
        'f_groups': [asdict(fg) for fg in result.f_groups],
        'inconsistent_domains': [asdict(d) for d in result.inconsistent_domains],
        'inconsistent_count': len(result.inconsistent_domains),
        'warnings': result.warnings
    }


def evaluate_clans_file(clans_path: Path, h_group_id: Optional[str] = None) -> HGroupResult:
    """Evaluate a single CLANS file.

    Args:
        clans_path: Path to .clans file
        h_group_id: Optional H-group ID (inferred from filename if not provided)

    Returns:
        HGroupResult
    """
    if h_group_id is None:
        # Infer from filename: 10_1.clans -> 10.1
        h_group_id = clans_path.stem.replace('_', '.')

    data = parse_clans_file(clans_path)
    return evaluate_hgroup(data, h_group_id)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate F-group consistency from CLANS output"
    )
    parser.add_argument(
        "clans_file", type=Path,
        help="Path to .clans file"
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output JSON file (default: print to stdout)"
    )
    parser.add_argument(
        "--h-group", type=str, default=None,
        help="H-group ID (default: infer from filename)"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print summary only (not full JSON)"
    )
    args = parser.parse_args()

    result = evaluate_clans_file(args.clans_file, args.h_group)

    if args.summary:
        print(f"H-group: {result.h_group_id}")
        print(f"Domains: {result.total_domains}")
        print(f"F-groups: {result.f_group_count}")
        print(f"Consistency: {result.overall_consistency_rate:.1%}")
        print(f"Mean silhouette: {result.mean_silhouette:.3f}")
        print(f"Inconsistent domains: {len(result.inconsistent_domains)}")

        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")

        if result.inconsistent_domains:
            print("\nTop inconsistent domains:")
            for d in result.inconsistent_domains[:10]:
                print(f"  {d.domain_name} ({d.f_group_id}): "
                      f"ratio={d.distance_ratio:.2f}, nearest={d.nearest_other_centroid}")
    else:
        output_dict = result_to_dict(result)

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_dict, f, indent=2)
            print(f"Results written to {args.output}")
        else:
            print(json.dumps(output_dict, indent=2))


if __name__ == "__main__":
    main()
