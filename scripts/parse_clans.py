#!/usr/bin/env python3
"""Parse CLANS output files.

Extracts sequences, coordinates, and connection data from .clans files.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Domain:
    """A domain from the CLANS file."""
    index: int
    name: str
    ecod_uid: int
    f_group_id: str
    t_group_id: str
    sequence: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class ClansData:
    """Parsed data from a CLANS file."""
    domains: List[Domain]
    parameters: Dict[str, str]
    connections: List[Tuple[int, int, float]]  # (idx1, idx2, evalue)

    @property
    def f_groups(self) -> List[str]:
        """Get unique F-group IDs."""
        return sorted(set(d.f_group_id for d in self.domains))

    @property
    def coordinates(self) -> np.ndarray:
        """Get Nx3 coordinate array."""
        return np.array([[d.x, d.y, d.z] for d in self.domains])

    def get_domains_by_fgroup(self, f_group_id: str) -> List[Domain]:
        """Get all domains belonging to an F-group."""
        return [d for d in self.domains if d.f_group_id == f_group_id]

    def get_indices_by_fgroup(self, f_group_id: str) -> List[int]:
        """Get domain indices for an F-group."""
        return [d.index for d in self.domains if d.f_group_id == f_group_id]


def parse_header(header: str) -> Tuple[str, int, str, str]:
    """Parse FASTA header to extract domain info.

    Supports multiple formats:
    1. Pipe-separated: >domain_name|ecod_uid|f_group_id|t_group_id
    2. Space-separated: >domain_name f_group_id
    3. Simple: >domain_name

    Returns:
        (domain_name, ecod_uid, f_group_id, t_group_id)
    """
    # Remove '>' prefix if present
    header = header.lstrip('>')

    # Try pipe-separated format first (our standard format)
    if '|' in header:
        parts = header.split('|')
        if len(parts) >= 4:
            try:
                return parts[0], int(parts[1]), parts[2], parts[3]
            except ValueError:
                return parts[0], 0, parts[2], parts[3]
        elif len(parts) == 2:
            return parts[0], 0, parts[1], parts[1].rsplit('.', 1)[0]

    # Try space-separated format (legacy CLANS format)
    if ' ' in header:
        parts = header.split(None, 1)  # Split on whitespace, max 2 parts
        if len(parts) == 2:
            name = parts[0]
            f_group = parts[1].strip()
            # Derive t_group from f_group (remove last component)
            t_group = '.'.join(f_group.split('.')[:-1]) if '.' in f_group else f_group
            return name, 0, f_group, t_group

    # Single value - no F-group info
    return header.strip(), 0, "unknown", "unknown"


def parse_clans_file(filepath: Path) -> ClansData:
    """Parse a CLANS format file.

    Args:
        filepath: Path to .clans file

    Returns:
        ClansData object with parsed content
    """
    content = filepath.read_text()

    domains = []
    parameters = {}
    connections = []

    # Parse parameters
    param_match = re.search(r'<param>(.*?)</param>', content, re.DOTALL)
    if param_match:
        for line in param_match.group(1).strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                parameters[key.strip()] = value.strip()

    # Parse sequences
    seq_match = re.search(r'<seq>(.*?)</seq>', content, re.DOTALL)
    if seq_match:
        seq_text = seq_match.group(1).strip()
        current_header = None
        current_seq = []
        idx = 0

        for line in seq_text.split('\n'):
            line = line.strip()
            if line.startswith('>'):
                # Save previous sequence
                if current_header is not None:
                    name, uid, fgroup, tgroup = parse_header(current_header)
                    domains.append(Domain(
                        index=idx,
                        name=name,
                        ecod_uid=uid,
                        f_group_id=fgroup,
                        t_group_id=tgroup,
                        sequence=''.join(current_seq)
                    ))
                    idx += 1
                current_header = line
                current_seq = []
            elif line:
                current_seq.append(line)

        # Don't forget the last sequence
        if current_header is not None:
            name, uid, fgroup, tgroup = parse_header(current_header)
            domains.append(Domain(
                index=idx,
                name=name,
                ecod_uid=uid,
                f_group_id=fgroup,
                t_group_id=tgroup,
                sequence=''.join(current_seq)
            ))

    # Parse positions
    pos_match = re.search(r'<pos>(.*?)</pos>', content, re.DOTALL)
    if pos_match:
        for line in pos_match.group(1).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 4:
                idx = int(parts[0])
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                if idx < len(domains):
                    domains[idx].x = x
                    domains[idx].y = y
                    domains[idx].z = z

    # Parse connections (HSP or attraction values)
    # Format: <hsp>idx1 idx2 evalue</hsp> or <att>idx1 idx2 value</att>
    for tag in ['hsp', 'att']:
        conn_match = re.search(f'<{tag}>(.*?)</{tag}>', content, re.DOTALL)
        if conn_match:
            for line in conn_match.group(1).strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        idx1, idx2 = int(parts[0]), int(parts[1])
                        value = float(parts[2])
                        connections.append((idx1, idx2, value))
                    except ValueError:
                        continue
            break  # Only parse one type

    return ClansData(domains=domains, parameters=parameters, connections=connections)


def validate_clans_data(data: ClansData) -> List[str]:
    """Validate parsed CLANS data.

    Returns list of warning messages.
    """
    warnings = []

    if not data.domains:
        warnings.append("No domains found")
        return warnings

    # Check for missing coordinates
    zero_coords = sum(1 for d in data.domains if d.x == 0 and d.y == 0 and d.z == 0)
    if zero_coords == len(data.domains):
        warnings.append("All coordinates are zero - CLANS may not have run")
    elif zero_coords > 0:
        warnings.append(f"{zero_coords} domains have zero coordinates")

    # Check F-group distribution
    fgroup_counts = {}
    for d in data.domains:
        fgroup_counts[d.f_group_id] = fgroup_counts.get(d.f_group_id, 0) + 1

    single_member_fgroups = sum(1 for c in fgroup_counts.values() if c == 1)
    if single_member_fgroups > 0:
        warnings.append(f"{single_member_fgroups} F-groups have only 1 member")

    return warnings


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: parse_clans.py <clans_file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    data = parse_clans_file(filepath)

    print(f"Parsed {filepath.name}:")
    print(f"  Domains: {len(data.domains)}")
    print(f"  F-groups: {len(data.f_groups)}")
    print(f"  Connections: {len(data.connections)}")
    print(f"  Parameters: {data.parameters.get('rounds_done', 'unknown')} rounds")

    warnings = validate_clans_data(data)
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    print("\nF-group distribution:")
    for fg in data.f_groups:
        domains = data.get_domains_by_fgroup(fg)
        print(f"  {fg}: {len(domains)} domains")
