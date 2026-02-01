#!/usr/bin/env python3
"""
ECOD Length Anomaly Detector

Identifies domain length anomalies that may indicate boundary errors:
1. Within-F-group outliers: domains significantly different from F-group median
2. Rep-vs-children mismatches: representatives with different length than their children

Usage:
    python length_anomaly_detector.py --help
    python length_anomaly_detector.py fgroup --h-group 11.1  # Ig domains
    python length_anomaly_detector.py fgroup --h-group 5.1   # Beta propellers
    python length_anomaly_detector.py rep-children --h-group 11.1
    python length_anomaly_detector.py both --output results/
"""

import argparse
import psycopg2
import csv
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class FGroupStats:
    """Statistics for an F-group"""
    f_group_id: str
    t_group_id: str
    h_group_id: str
    f_name: Optional[str]
    domain_count: int
    min_length: int
    max_length: int
    mean_length: float
    median_length: float
    stddev_length: float
    pdb_count: int
    afdb_count: int


@dataclass
class LengthOutlier:
    """A domain with anomalous length"""
    domain_id: str
    sequence_length: int
    f_group_id: str
    t_group_id: str
    h_group_id: str
    f_name: Optional[str]
    fgroup_median: float
    fgroup_stddev: float
    ratio_to_median: float
    z_score: float
    is_discontinuous: bool
    range_definition: str
    source: str  # PDB or AFDB
    anomaly_type: str  # 'too_long' or 'too_short'


@dataclass
class RepChildMismatch:
    """A representative with length mismatch to children"""
    rep_domain_id: str
    rep_length: int
    rep_f_group_id: str
    rep_t_group_id: str
    rep_h_group_id: str
    f_name: Optional[str]
    child_count: int
    child_mean_length: float
    child_median_length: float
    child_min_length: int
    child_max_length: int
    length_ratio: float  # rep_length / child_median
    mismatch_type: str  # 'rep_longer' or 'rep_shorter'


class LengthAnomalyDetector:
    """Detects length anomalies in ECOD domain assignments"""

    def __init__(self, host: str, port: int, user: str, password: str,
                 database: str, verbose: bool = True):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.verbose = verbose

    def close(self):
        self.conn.close()

    def log(self, msg: str):
        if self.verbose:
            print(msg, file=sys.stderr)

    def get_fgroup_stats(self, h_group: Optional[str] = None,
                         t_group: Optional[str] = None,
                         min_members: int = 5) -> List[FGroupStats]:
        """Get length statistics for each F-group"""

        where_clauses = ["d.sequence_length IS NOT NULL"]
        if h_group:
            where_clauses.append(f"fa.h_group_id = '{h_group}'")
        if t_group:
            where_clauses.append(f"fa.t_group_id = '{t_group}'")

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT
                fa.f_group_id,
                fa.t_group_id,
                fa.h_group_id,
                c.name as f_name,
                COUNT(*) as domain_count,
                MIN(d.sequence_length) as min_length,
                MAX(d.sequence_length) as max_length,
                AVG(d.sequence_length) as mean_length,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.sequence_length) as median_length,
                COALESCE(STDDEV(d.sequence_length), 0) as stddev_length,
                COUNT(*) FILTER (WHERE d.domain_id LIKE 'e%') as pdb_count,
                COUNT(*) FILTER (WHERE d.domain_id NOT LIKE 'e%') as afdb_count
            FROM ecod_commons.f_group_assignments fa
            JOIN ecod_commons.domains d ON fa.domain_id = d.id
            LEFT JOIN ecod_rep.cluster c ON c.id = fa.f_group_id
            WHERE {where_sql}
            GROUP BY fa.f_group_id, fa.t_group_id, fa.h_group_id, c.name
            HAVING COUNT(*) >= {min_members}
            ORDER BY fa.h_group_id, fa.t_group_id, fa.f_group_id
        """

        cur = self.conn.cursor()
        cur.execute(query)

        results = []
        for row in cur.fetchall():
            results.append(FGroupStats(
                f_group_id=row[0],
                t_group_id=row[1],
                h_group_id=row[2],
                f_name=row[3],
                domain_count=row[4],
                min_length=row[5],
                max_length=row[6],
                mean_length=float(row[7]),
                median_length=float(row[8]),
                stddev_length=float(row[9]),
                pdb_count=row[10],
                afdb_count=row[11]
            ))

        cur.close()
        return results

    def find_fgroup_outliers(self, h_group: Optional[str] = None,
                              t_group: Optional[str] = None,
                              ratio_threshold: float = 1.5,
                              z_threshold: float = 2.0,
                              min_fgroup_members: int = 5) -> List[LengthOutlier]:
        """
        Find domains that are length outliers within their F-group.

        A domain is flagged if:
        - ratio_to_median > ratio_threshold OR < 1/ratio_threshold
        - OR z_score > z_threshold OR < -z_threshold
        """

        self.log(f"Finding F-group outliers (ratio>{ratio_threshold} or z>{z_threshold})...")

        # Build WHERE clause for filtering
        where_clauses = ["d.sequence_length IS NOT NULL"]
        if h_group:
            where_clauses.append(f"fa.h_group_id = '{h_group}'")
        if t_group:
            where_clauses.append(f"fa.t_group_id = '{t_group}'")

        where_sql = " AND ".join(where_clauses)

        query = f"""
            WITH fgroup_stats AS (
                SELECT
                    fa.f_group_id,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.sequence_length) as median_len,
                    COALESCE(STDDEV(d.sequence_length), 0) as stddev_len,
                    COUNT(*) as member_count
                FROM ecod_commons.f_group_assignments fa
                JOIN ecod_commons.domains d ON fa.domain_id = d.id
                WHERE {where_sql}
                GROUP BY fa.f_group_id
                HAVING COUNT(*) >= {min_fgroup_members}
            )
            SELECT
                d.domain_id,
                d.sequence_length,
                fa.f_group_id,
                fa.t_group_id,
                fa.h_group_id,
                c.name as f_name,
                fs.median_len,
                fs.stddev_len,
                d.sequence_length::numeric / NULLIF(fs.median_len, 0) as ratio_to_median,
                CASE WHEN fs.stddev_len > 0
                     THEN (d.sequence_length - fs.median_len) / fs.stddev_len
                     ELSE 0 END as z_score,
                COALESCE(d.is_discontinuous, false) as is_discontinuous,
                COALESCE(d.range_definition, '') as range_definition,
                CASE WHEN d.domain_id LIKE 'e%' THEN 'PDB' ELSE 'AFDB' END as source
            FROM ecod_commons.f_group_assignments fa
            JOIN ecod_commons.domains d ON fa.domain_id = d.id
            JOIN fgroup_stats fs ON fa.f_group_id = fs.f_group_id
            LEFT JOIN ecod_rep.cluster c ON c.id = fa.f_group_id
            WHERE d.sequence_length IS NOT NULL
              AND (
                  d.sequence_length::numeric / NULLIF(fs.median_len, 0) > {ratio_threshold}
                  OR d.sequence_length::numeric / NULLIF(fs.median_len, 0) < {1/ratio_threshold}
                  OR (fs.stddev_len > 0 AND ABS((d.sequence_length - fs.median_len) / fs.stddev_len) > {z_threshold})
              )
            ORDER BY ABS((d.sequence_length - fs.median_len) / NULLIF(fs.stddev_len, 1)) DESC
        """

        cur = self.conn.cursor()
        cur.execute(query)

        results = []
        for row in cur.fetchall():
            ratio = float(row[8]) if row[8] else 0
            anomaly_type = 'too_long' if ratio > 1 else 'too_short'

            results.append(LengthOutlier(
                domain_id=row[0],
                sequence_length=row[1],
                f_group_id=row[2],
                t_group_id=row[3],
                h_group_id=row[4],
                f_name=row[5],
                fgroup_median=float(row[6]),
                fgroup_stddev=float(row[7]),
                ratio_to_median=ratio,
                z_score=float(row[9]),
                is_discontinuous=row[10],
                range_definition=row[11],
                source=row[12],
                anomaly_type=anomaly_type
            ))

        cur.close()
        self.log(f"Found {len(results)} outliers")
        return results

    def find_rep_child_mismatches(self, h_group: Optional[str] = None,
                                   t_group: Optional[str] = None,
                                   ratio_threshold: float = 1.3,
                                   min_children: int = 3) -> List[RepChildMismatch]:
        """
        Find representatives whose length differs significantly from their children.

        A mismatch is flagged if:
        - rep_length / child_median > ratio_threshold
        - OR rep_length / child_median < 1/ratio_threshold
        """

        self.log(f"Finding rep-child mismatches (ratio>{ratio_threshold})...")

        where_clauses = ["d.sequence_length IS NOT NULL", "rep.sequence_length IS NOT NULL"]
        if h_group:
            where_clauses.append(f"fa.h_group_id = '{h_group}'")
        if t_group:
            where_clauses.append(f"fa.t_group_id = '{t_group}'")

        where_sql = " AND ".join(where_clauses)

        query = f"""
            WITH rep_children AS (
                SELECT
                    rep.domain_id as rep_domain_id,
                    rep.sequence_length as rep_length,
                    fa.f_group_id,
                    fa.t_group_id,
                    fa.h_group_id,
                    d.sequence_length as child_length
                FROM ecod_commons.domains d
                JOIN ecod_commons.f_group_assignments fa ON fa.domain_id = d.id
                JOIN ecod_commons.domains rep ON d.representative_domain_id = rep.id
                WHERE {where_sql}
                  AND d.is_representative = false
                  AND rep.is_representative = true
            ),
            rep_stats AS (
                SELECT
                    rep_domain_id,
                    rep_length,
                    f_group_id,
                    t_group_id,
                    h_group_id,
                    COUNT(*) as child_count,
                    AVG(child_length) as child_mean,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY child_length) as child_median,
                    MIN(child_length) as child_min,
                    MAX(child_length) as child_max
                FROM rep_children
                GROUP BY rep_domain_id, rep_length, f_group_id, t_group_id, h_group_id
                HAVING COUNT(*) >= {min_children}
            )
            SELECT
                rs.*,
                c.name as f_name,
                rs.rep_length::numeric / NULLIF(rs.child_median, 0) as length_ratio
            FROM rep_stats rs
            LEFT JOIN ecod_rep.cluster c ON c.id = rs.f_group_id
            WHERE rs.rep_length::numeric / NULLIF(rs.child_median, 0) > {ratio_threshold}
               OR rs.rep_length::numeric / NULLIF(rs.child_median, 0) < {1/ratio_threshold}
            ORDER BY ABS(LN(rs.rep_length::numeric / NULLIF(rs.child_median, 0))) DESC
        """

        cur = self.conn.cursor()
        cur.execute(query)

        results = []
        for row in cur.fetchall():
            ratio = float(row[11]) if row[11] else 0
            mismatch_type = 'rep_longer' if ratio > 1 else 'rep_shorter'

            results.append(RepChildMismatch(
                rep_domain_id=row[0],
                rep_length=row[1],
                rep_f_group_id=row[2],
                rep_t_group_id=row[3],
                rep_h_group_id=row[4],
                child_count=row[5],
                child_mean_length=float(row[6]),
                child_median_length=float(row[7]),
                child_min_length=row[8],
                child_max_length=row[9],
                f_name=row[10],
                length_ratio=ratio,
                mismatch_type=mismatch_type
            ))

        cur.close()
        self.log(f"Found {len(results)} mismatches")
        return results

    def get_summary_by_hgroup(self, outliers: List[LengthOutlier]) -> Dict[str, Dict[str, int]]:
        """Summarize outliers by H-group"""
        summary = {}
        for o in outliers:
            if o.h_group_id not in summary:
                summary[o.h_group_id] = {'too_long': 0, 'too_short': 0, 'total': 0}
            summary[o.h_group_id][o.anomaly_type] += 1
            summary[o.h_group_id]['total'] += 1
        return summary


def write_csv(data: List[Any], filename: str, fieldnames: List[str]):
    """Write dataclass list to CSV"""
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow(asdict(item))


def write_json(data: List[Any], filename: str):
    """Write dataclass list to JSON"""
    with open(filename, 'w') as f:
        json.dump([asdict(item) for item in data], f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='ECOD Length Anomaly Detector',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze beta propeller F-groups
  python length_anomaly_detector.py fgroup --h-group 5.1

  # Analyze Ig domain rep-child relationships
  python length_anomaly_detector.py rep-children --h-group 11.1

  # Full analysis with custom thresholds
  python length_anomaly_detector.py both --ratio 2.0 --zscore 3.0 --output results/

  # Database-wide scan (slow)
  python length_anomaly_detector.py both --output full_scan/
        """
    )

    parser.add_argument('mode', choices=['fgroup', 'rep-children', 'both', 'stats'],
                        help='Analysis mode')
    parser.add_argument('--h-group', dest='h_group',
                        help='Filter by H-group (e.g., 5.1, 11.1)')
    parser.add_argument('--t-group', dest='t_group',
                        help='Filter by T-group')
    parser.add_argument('--ratio', type=float, default=1.5,
                        help='Ratio threshold for outlier detection (default: 1.5)')
    parser.add_argument('--zscore', type=float, default=2.0,
                        help='Z-score threshold for outlier detection (default: 2.0)')
    parser.add_argument('--min-members', type=int, default=5,
                        help='Minimum F-group members for analysis (default: 5)')
    parser.add_argument('--min-children', type=int, default=3,
                        help='Minimum children for rep analysis (default: 3)')
    parser.add_argument('--output', '-o', default='.',
                        help='Output directory (default: current)')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='csv',
                        help='Output format (default: csv)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress messages')

    # Database connection
    parser.add_argument('--host', default='dione')
    parser.add_argument('--port', type=int, default=45000)
    parser.add_argument('--user', default='ecod')
    parser.add_argument('--password', default=os.environ.get('DB_PASSWORD'),
                        help='Database password (default: $DB_PASSWORD env var)')
    parser.add_argument('--database', default='ecod_protein')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Connect
    detector = LengthAnomalyDetector(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        verbose=not args.quiet
    )

    try:
        # Generate filename prefix
        prefix = ""
        if args.h_group:
            prefix = f"h{args.h_group.replace('.', '_')}_"
        elif args.t_group:
            prefix = f"t{args.t_group.replace('.', '_')}_"

        timestamp = datetime.now().strftime("%Y%m%d")

        # Run requested analysis
        if args.mode in ['stats', 'both']:
            detector.log("Collecting F-group statistics...")
            stats = detector.get_fgroup_stats(
                h_group=args.h_group,
                t_group=args.t_group,
                min_members=args.min_members
            )

            filename = os.path.join(args.output, f"{prefix}fgroup_stats_{timestamp}")
            if args.format in ['csv', 'both']:
                write_csv(stats, f"{filename}.csv",
                         [f.name for f in FGroupStats.__dataclass_fields__.values()])
                print(f"Wrote {len(stats)} F-group stats to {filename}.csv")
            if args.format in ['json', 'both']:
                write_json(stats, f"{filename}.json")
                print(f"Wrote {len(stats)} F-group stats to {filename}.json")

        if args.mode in ['fgroup', 'both']:
            outliers = detector.find_fgroup_outliers(
                h_group=args.h_group,
                t_group=args.t_group,
                ratio_threshold=args.ratio,
                z_threshold=args.zscore,
                min_fgroup_members=args.min_members
            )

            filename = os.path.join(args.output, f"{prefix}fgroup_outliers_{timestamp}")
            if args.format in ['csv', 'both']:
                write_csv(outliers, f"{filename}.csv",
                         [f.name for f in LengthOutlier.__dataclass_fields__.values()])
                print(f"Wrote {len(outliers)} outliers to {filename}.csv")
            if args.format in ['json', 'both']:
                write_json(outliers, f"{filename}.json")
                print(f"Wrote {len(outliers)} outliers to {filename}.json")

            # Print summary
            if not args.quiet:
                summary = detector.get_summary_by_hgroup(outliers)
                print("\nSummary by H-group:")
                print(f"{'H-group':<12} {'Too Long':>10} {'Too Short':>10} {'Total':>10}")
                print("-" * 45)
                for hg in sorted(summary.keys()):
                    s = summary[hg]
                    print(f"{hg:<12} {s['too_long']:>10} {s['too_short']:>10} {s['total']:>10}")

        if args.mode in ['rep-children', 'both']:
            mismatches = detector.find_rep_child_mismatches(
                h_group=args.h_group,
                t_group=args.t_group,
                ratio_threshold=args.ratio,
                min_children=args.min_children
            )

            filename = os.path.join(args.output, f"{prefix}rep_child_mismatches_{timestamp}")
            if args.format in ['csv', 'both']:
                write_csv(mismatches, f"{filename}.csv",
                         [f.name for f in RepChildMismatch.__dataclass_fields__.values()])
                print(f"Wrote {len(mismatches)} mismatches to {filename}.csv")
            if args.format in ['json', 'both']:
                write_json(mismatches, f"{filename}.json")
                print(f"Wrote {len(mismatches)} mismatches to {filename}.json")

            # Print summary
            if not args.quiet and mismatches:
                print("\nTop rep-child mismatches:")
                print(f"{'Rep Domain':<25} {'Rep Len':>8} {'Child Med':>10} {'Ratio':>8} {'Type'}")
                print("-" * 65)
                for m in mismatches[:20]:
                    print(f"{m.rep_domain_id:<25} {m.rep_length:>8} {m.child_median_length:>10.0f} {m.length_ratio:>8.2f} {m.mismatch_type}")

    finally:
        detector.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
