#!/usr/bin/env python3
"""
Generate PyMOL visualizations for Ig domain splitting analysis.

Creates three images:
1. Original merged domain highlighted on protein
2. New putative domains + disordered regions
3. Superposition of new domains colored by secondary structure (R->B)
"""

import os
import subprocess
from pathlib import Path

# Set PYMOL_PATH for license
os.environ['PYMOL_PATH'] = os.path.expanduser('~/.pymol')

# Paths
DOMAIN_PDB = Path("/data/ecod/af2_pdb_domain_data/40829/004082943/004082943.pdb")
TEMPLATE_PDB = Path("/home/rschaeff/data/dpam_reference/ecod_data/ECOD70/000327604.pdb")
OUTPUT_DIR = Path("/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/figures")
OUTPUT_DIR.mkdir(exist_ok=True)

# Domain definitions
# Original merged domain range
ORIGINAL_RANGE = "641-855,1056-1155,1671-1770,1871-2010,2066-2100,2111-2140,2151-2245,2276-2300"

# New domains identified by FoldSeek (approximate ranges from results)
NEW_DOMAINS = [
    ("Ig1", "648-750"),      # First Ig from 641-855
    ("Ig2", "760-852"),      # Second Ig from 641-855
    ("Ig3", "1063-1154"),    # From 1056-1155
    ("Ig4", "1671-1769"),    # From 1671-1770
    ("Ig5", "1878-1911"),    # Partial from 1871-2010
]

# Disordered regions (pLDDT < 30)
DISORDERED = [
    ("dis1", "2066-2100"),
    ("dis2", "2111-2140"),
    ("dis3", "2151-2245"),
    ("dis4", "2276-2300"),
]

# Colors for new domains
DOMAIN_COLORS = [
    "forest",      # Ig1 - green
    "marine",      # Ig2 - blue
    "orange",      # Ig3 - orange
    "magenta",     # Ig4 - magenta
    "cyan",        # Ig5 - cyan
]

def range_to_pymol(range_str):
    """Convert '641-855,1056-1155' to PyMOL selection 'resi 641-855+1056-1155'"""
    parts = range_str.replace(',', '+')
    return f"resi {parts}"


# PyMOL script 1: Original domain
SCRIPT1 = f'''
# Image 1: Original merged Ig domain
load {DOMAIN_PDB}, protein
bg_color white

# Color whole protein gray
color gray80, protein
show cartoon, protein

# Highlight original domain in red
select original_domain, {range_to_pymol(ORIGINAL_RANGE)}
color firebrick, original_domain

# Set up view
orient protein
zoom protein, 5
set ray_shadows, 0
set antialias, 2
set ray_trace_mode, 1

# Add label
#set label_size, 20
#pseudoatom label_atom, pos=[0, 0, 100]
#label label_atom, "Original: Q60ZN5_nD12 (740aa merged)"

ray 1600, 1200
png {OUTPUT_DIR}/1_original_domain.png, dpi=300
quit
'''

# PyMOL script 2: New domains + disordered
domain_selections = []
for i, (name, rng) in enumerate(NEW_DOMAINS):
    domain_selections.append(f"select {name}, {range_to_pymol(rng)}")
    domain_selections.append(f"color {DOMAIN_COLORS[i]}, {name}")

disordered_selections = []
for name, rng in DISORDERED:
    disordered_selections.append(f"select {name}, {range_to_pymol(rng)}")
    disordered_selections.append(f"color yellow, {name}")
    disordered_selections.append(f"set cartoon_transparency, 0.5, {name}")

SCRIPT2 = f'''
# Image 2: New domains + disordered regions
load {DOMAIN_PDB}, protein
bg_color white

# Color whole protein light gray (non-domain regions)
color gray80, protein
show cartoon, protein

# Color new Ig domains
{chr(10).join(domain_selections)}

# Color disordered regions yellow with transparency
{chr(10).join(disordered_selections)}

# Set up view
orient protein
zoom protein, 5
set ray_shadows, 0
set antialias, 2
set ray_trace_mode, 1

ray 1600, 1200
png {OUTPUT_DIR}/2_new_domains_disordered.png, dpi=300
quit
'''

# PyMOL script 3: Superposition colored by SSE
# We need to extract each domain, align to template, then color by SSE order
SCRIPT3 = f'''
# Image 3: Superposition of Ig domains colored by secondary structure (R->B)
load {TEMPLATE_PDB}, template
bg_color white

# Load each domain region separately
load {DOMAIN_PDB}, full_protein

# Create objects for each domain
create Ig1, full_protein and resi 648-750
create Ig2, full_protein and resi 760-852
create Ig3, full_protein and resi 1063-1154
create Ig4, full_protein and resi 1671-1769
create Ig5, full_protein and resi 1878-1911

delete full_protein

# Align all to template
align Ig1, template
align Ig2, template
align Ig3, template
align Ig4, template
align Ig5, template

# Hide template or show as reference
hide everything, template
#show cartoon, template
#color white, template
#set cartoon_transparency, 0.7, template

# Show as cartoon
show cartoon, Ig1
show cartoon, Ig2
show cartoon, Ig3
show cartoon, Ig4
show cartoon, Ig5

# Color each domain with a spectrum
# Ig1 - red tones
spectrum count, red_orange, Ig1
# Ig2 - orange tones
spectrum count, orange_yellow, Ig2
# Ig3 - yellow-green
spectrum count, yellow_green, Ig3
# Ig4 - green-cyan
spectrum count, green_cyan, Ig4
# Ig5 - blue tones
spectrum count, cyan_blue, Ig5

# Alternative: color by domain with distinct colors
color tv_red, Ig1
color tv_orange, Ig2
color tv_yellow, Ig3
color tv_green, Ig4
color tv_blue, Ig5

# Set up view
orient all
zoom all, 5
set ray_shadows, 0
set antialias, 2
set ray_trace_mode, 1

ray 1600, 1200
png {OUTPUT_DIR}/3_superposition_by_domain.png, dpi=300
quit
'''

# Alternative Script 3 with SSE coloring
SCRIPT3_SSE = f'''
# Image 3: Superposition of Ig domains colored by SSE position (R->B)
load {TEMPLATE_PDB}, template
bg_color white

# Load each domain region separately
load {DOMAIN_PDB}, full_protein

# Create objects for each domain
create Ig1, full_protein and resi 648-750
create Ig2, full_protein and resi 760-852
create Ig3, full_protein and resi 1063-1154
create Ig4, full_protein and resi 1671-1769
create Ig5, full_protein and resi 1878-1911

delete full_protein

# Align all to template
align Ig1, template
align Ig2, template
align Ig3, template
align Ig4, template
align Ig5, template

# Create combined object
create all_domains, Ig1 or Ig2 or Ig3 or Ig4 or Ig5

# Hide individual and template
hide everything, Ig1
hide everything, Ig2
hide everything, Ig3
hide everything, Ig4
hide everything, Ig5
hide everything, template

# Show combined
show cartoon, all_domains

# Color by secondary structure with spectrum
# First assign secondary structure
dss all_domains

# Color sheets and helices differently
# Use spectrum along the chain to show SSE order
spectrum count, rainbow, all_domains

# Or color by secondary structure type with position
#color red, all_domains and ss h  # helices
#color blue, all_domains and ss s  # sheets

# Set up view - orient to show Ig fold nicely
orient all_domains
turn y, 30
turn x, -20
zoom all_domains, 3

set ray_shadows, 0
set antialias, 2
set ray_trace_mode, 1
set cartoon_fancy_helices, 1
set cartoon_flat_sheets, 1

ray 1600, 1200
png {OUTPUT_DIR}/3_superposition_rainbow.png, dpi=300
quit
'''

def run_pymol(script_content, script_name):
    """Run a PyMOL script."""
    script_file = OUTPUT_DIR / f"{script_name}.pml"
    with open(script_file, 'w') as f:
        f.write(script_content)

    print(f"Running {script_name}...")
    result = subprocess.run(
        ['pymol', '-cq', str(script_file)],
        capture_output=True,
        text=True,
        env={**os.environ, 'PYMOL_PATH': os.path.expanduser('~/.pymol')}
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"  Done: {script_name}")
    return result.returncode == 0


if __name__ == "__main__":
    print("Generating domain visualization images...")
    print(f"Output directory: {OUTPUT_DIR}")

    # Check files exist
    if not DOMAIN_PDB.exists():
        print(f"ERROR: Domain PDB not found: {DOMAIN_PDB}")
        exit(1)
    if not TEMPLATE_PDB.exists():
        print(f"ERROR: Template PDB not found: {TEMPLATE_PDB}")
        exit(1)

    # Run scripts
    run_pymol(SCRIPT1, "script1_original")
    run_pymol(SCRIPT2, "script2_new_domains")
    run_pymol(SCRIPT3, "script3_superposition")
    run_pymol(SCRIPT3_SSE, "script3_sse")

    print("\nDone! Images saved to:")
    for img in OUTPUT_DIR.glob("*.png"):
        print(f"  {img}")
