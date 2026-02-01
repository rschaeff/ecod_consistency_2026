#!/usr/bin/env python3
"""Batch evaluate all completed CLANS jobs.

Generates per-job evaluations and summary reports for triage.
"""

import json
import sys
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
sys.path.insert(0, str(Path(__file__).parent))

from config import PROJECT_ROOT
from evaluate_consistency import evaluate_clans_file, result_to_dict


def find_completed_jobs() -> List[Dict[str, Any]]:
    """Find all completed CLANS jobs."""
    results_dir = Path(PROJECT_ROOT) / "results"
    completed = []

    if not results_dir.exists():
        return completed

    for job_dir in sorted(results_dir.iterdir()):
        if not job_dir.is_dir():
            continue

        # Look for .clans file
        clans_files = list(job_dir.glob("*.clans"))
        if not clans_files:
            continue

        # Get job info if available
        complete_marker = job_dir / "job_complete.json"
        job_info = {}
        if complete_marker.exists():
            try:
                with open(complete_marker) as f:
                    job_info = json.load(f)
            except:
                pass

        completed.append({
            'h_group_id': job_dir.name.replace('_', '.'),
            'clans_file': clans_files[0],
            'job_dir': job_dir,
            'job_info': job_info
        })

    return completed


def evaluate_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single job and return results."""
    try:
        result = evaluate_clans_file(job['clans_file'], job['h_group_id'])
        return {
            'status': 'success',
            'h_group_id': job['h_group_id'],
            'result': result_to_dict(result)
        }
    except Exception as e:
        return {
            'status': 'error',
            'h_group_id': job['h_group_id'],
            'error': str(e)
        }


def generate_summary_csv(results: List[Dict], output_path: Path):
    """Generate summary CSV for all H-groups."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'h_group_id',
            'total_domains',
            'f_group_count',
            'consistency_rate',
            'mean_silhouette',
            'inconsistent_count',
            'needs_review',
            'warnings'
        ])

        for r in results:
            if r['status'] != 'success':
                writer.writerow([
                    r['h_group_id'],
                    '', '', '', '', '',
                    'ERROR',
                    r.get('error', 'Unknown error')
                ])
                continue

            result = r['result']
            consistency = result['overall_consistency_rate']
            silhouette = result['mean_silhouette']
            inconsistent = result['inconsistent_count']

            # Flag for review if consistency < 90% or silhouette < 0.1
            needs_review = 'YES' if consistency < 0.90 or silhouette < 0.1 else 'NO'

            writer.writerow([
                result['h_group_id'],
                result['total_domains'],
                result['f_group_count'],
                f"{consistency:.3f}",
                f"{silhouette:.3f}",
                inconsistent,
                needs_review,
                '; '.join(result.get('warnings', []))
            ])


def generate_inconsistent_domains_csv(results: List[Dict], output_path: Path):
    """Generate CSV of all inconsistent domains across all H-groups."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'h_group_id',
            'domain_name',
            'ecod_uid',
            'f_group_id',
            'own_centroid_dist',
            'nearest_other_fgroup',
            'nearest_other_dist',
            'distance_ratio',
            'silhouette'
        ])

        for r in results:
            if r['status'] != 'success':
                continue

            result = r['result']
            for domain in result['inconsistent_domains']:
                writer.writerow([
                    result['h_group_id'],
                    domain['domain_name'],
                    domain['ecod_uid'],
                    domain['f_group_id'],
                    f"{domain['own_centroid_distance']:.3f}",
                    domain['nearest_other_centroid'],
                    f"{domain['nearest_other_distance']:.3f}",
                    f"{domain['distance_ratio']:.3f}",
                    f"{domain['silhouette']:.3f}"
                ])


def generate_triage_report(results: List[Dict], output_path: Path):
    """Generate markdown triage report highlighting problematic H-groups."""
    # Sort by consistency rate (worst first)
    successful = [r for r in results if r['status'] == 'success']
    successful.sort(key=lambda x: x['result']['overall_consistency_rate'])

    with open(output_path, 'w') as f:
        f.write("# ECOD F-group Consistency Triage Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        # Overall statistics
        total = len(results)
        success = len(successful)
        errors = total - success

        if successful:
            avg_consistency = sum(r['result']['overall_consistency_rate'] for r in successful) / success
            avg_silhouette = sum(r['result']['mean_silhouette'] for r in successful) / success
            total_inconsistent = sum(r['result']['inconsistent_count'] for r in successful)
        else:
            avg_consistency = avg_silhouette = total_inconsistent = 0

        f.write("## Summary\n\n")
        f.write(f"- Total H-groups evaluated: {total}\n")
        f.write(f"- Successful evaluations: {success}\n")
        f.write(f"- Errors: {errors}\n")
        f.write(f"- Average consistency rate: {avg_consistency:.1%}\n")
        f.write(f"- Average silhouette score: {avg_silhouette:.3f}\n")
        f.write(f"- Total inconsistent domains: {total_inconsistent}\n\n")

        # Consistency distribution
        f.write("## Consistency Distribution\n\n")
        bins = {'>=95%': 0, '90-95%': 0, '80-90%': 0, '70-80%': 0, '<70%': 0}
        for r in successful:
            c = r['result']['overall_consistency_rate']
            if c >= 0.95:
                bins['>=95%'] += 1
            elif c >= 0.90:
                bins['90-95%'] += 1
            elif c >= 0.80:
                bins['80-90%'] += 1
            elif c >= 0.70:
                bins['70-80%'] += 1
            else:
                bins['<70%'] += 1

        f.write("| Consistency | Count | Percentage |\n")
        f.write("|-------------|-------|------------|\n")
        for bin_name, count in bins.items():
            pct = count / success * 100 if success > 0 else 0
            f.write(f"| {bin_name} | {count} | {pct:.1f}% |\n")
        f.write("\n")

        # H-groups needing review (consistency < 90%)
        needs_review = [r for r in successful if r['result']['overall_consistency_rate'] < 0.90]

        f.write(f"## H-groups Requiring Review ({len(needs_review)})\n\n")

        if needs_review:
            f.write("| H-group | Domains | F-groups | Consistency | Silhouette | Inconsistent |\n")
            f.write("|---------|---------|----------|-------------|------------|-------------|\n")

            for r in needs_review[:50]:  # Top 50 worst
                result = r['result']
                f.write(f"| {result['h_group_id']} | {result['total_domains']} | ")
                f.write(f"{result['f_group_count']} | {result['overall_consistency_rate']:.1%} | ")
                f.write(f"{result['mean_silhouette']:.3f} | {result['inconsistent_count']} |\n")

            if len(needs_review) > 50:
                f.write(f"\n... and {len(needs_review) - 50} more\n")
        else:
            f.write("No H-groups require review.\n")

        f.write("\n")

        # Worst individual domains
        f.write("## Worst Inconsistent Domains (Top 50)\n\n")
        f.write("Domains with highest distance ratio (own centroid / nearest other centroid):\n\n")

        all_inconsistent = []
        for r in successful:
            for domain in r['result']['inconsistent_domains']:
                domain['h_group_id'] = r['result']['h_group_id']
                all_inconsistent.append(domain)

        all_inconsistent.sort(key=lambda x: x['distance_ratio'], reverse=True)

        if all_inconsistent:
            f.write("| Domain | H-group | F-group | Nearest Other | Ratio | Silhouette |\n")
            f.write("|--------|---------|---------|---------------|-------|------------|\n")

            for d in all_inconsistent[:50]:
                f.write(f"| {d['domain_name']} | {d['h_group_id']} | ")
                f.write(f"{d['f_group_id']} | {d['nearest_other_centroid']} | ")
                f.write(f"{d['distance_ratio']:.2f} | {d['silhouette']:.3f} |\n")
        else:
            f.write("No inconsistent domains found.\n")

        # Errors section
        if errors > 0:
            f.write("\n## Evaluation Errors\n\n")
            error_results = [r for r in results if r['status'] == 'error']
            for r in error_results[:20]:
                f.write(f"- **{r['h_group_id']}**: {r.get('error', 'Unknown')}\n")
            if len(error_results) > 20:
                f.write(f"\n... and {len(error_results) - 20} more errors\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch evaluate all completed CLANS jobs"
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path,
        default=Path(PROJECT_ROOT) / "evaluation",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of jobs to evaluate (for testing)"
    )
    parser.add_argument(
        "--h-groups", nargs="+", default=None,
        help="Specific H-groups to evaluate"
    )
    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(exist_ok=True)

    print("Finding completed jobs...")
    jobs = find_completed_jobs()
    print(f"Found {len(jobs)} completed jobs")

    if args.h_groups:
        jobs = [j for j in jobs if j['h_group_id'] in args.h_groups]
        print(f"Filtered to {len(jobs)} jobs")

    if args.limit:
        jobs = jobs[:args.limit]

    if not jobs:
        print("No jobs to evaluate!")
        return

    # Evaluate all jobs
    print(f"\nEvaluating {len(jobs)} jobs...")
    results = []
    for i, job in enumerate(jobs):
        result = evaluate_job(job)
        results.append(result)

        # Save individual result
        result_path = job['job_dir'] / "evaluation.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)

        if (i + 1) % 100 == 0:
            print(f"  Evaluated {i + 1}/{len(jobs)} jobs...")

    # Generate reports
    print("\nGenerating reports...")

    # Summary CSV
    summary_csv = args.output_dir / "summary.csv"
    generate_summary_csv(results, summary_csv)
    print(f"  Summary CSV: {summary_csv}")

    # Inconsistent domains CSV
    inconsistent_csv = args.output_dir / "inconsistent_domains.csv"
    generate_inconsistent_domains_csv(results, inconsistent_csv)
    print(f"  Inconsistent domains: {inconsistent_csv}")

    # Triage report
    triage_report = args.output_dir / "TRIAGE_REPORT.md"
    generate_triage_report(results, triage_report)
    print(f"  Triage report: {triage_report}")

    # Save all results as JSON
    all_results_path = args.output_dir / "all_results.json"
    with open(all_results_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'total_jobs': len(jobs),
            'results': results
        }, f, indent=2)
    print(f"  All results: {all_results_path}")

    # Print summary
    successful = [r for r in results if r['status'] == 'success']
    errors = len(results) - len(successful)

    print(f"\nEvaluation complete:")
    print(f"  Successful: {len(successful)}")
    print(f"  Errors: {errors}")

    if successful:
        avg_consistency = sum(r['result']['overall_consistency_rate'] for r in successful) / len(successful)
        needs_review = sum(1 for r in successful if r['result']['overall_consistency_rate'] < 0.90)
        print(f"  Average consistency: {avg_consistency:.1%}")
        print(f"  H-groups needing review: {needs_review}")


if __name__ == "__main__":
    main()
