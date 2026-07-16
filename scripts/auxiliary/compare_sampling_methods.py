#!/usr/bin/env python3
"""
Script para comparar muestreo aleatorio vs muestreo estratificado equilibrado

Uso:
    python scripts/auxiliary/compare_sampling_methods.py
"""

import re
import random
from collections import defaultdict

def load_pdf_inventory(list_file):
    """Cargar el listado de PDFs"""
    with open(list_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def extract_path_parts(relative_path):
    """Extraer PB y SDG del path"""
    parts = relative_path.split("/")
    pb_folder = parts[0] if parts else None
    source_folder = parts[1] if len(parts) > 1 else None
    return pb_folder, source_folder

def simulate_random_sampling(all_paths, sample_size=1000):
    """Simular muestreo aleatorio"""
    selected = random.sample(all_paths, min(sample_size, len(all_paths)))
    
    distribution = defaultdict(int)
    for path in selected:
        pb_folder, _ = extract_path_parts(path)
        distribution[pb_folder] += 1
    
    return distribution

def simulate_stratified_sampling(all_paths, sample_size=1000):
    """Simular muestreo estratificado equilibrado"""
    # Agrupar por PB
    pb_groups = defaultdict(list)
    for path in all_paths:
        pb_folder, _ = extract_path_parts(path)
        pb_groups[pb_folder].append(path)
    
    # Calcular cantidad por PB
    num_pbs = len(pb_groups)
    papers_per_pb = sample_size // num_pbs
    remainder = sample_size % num_pbs
    
    distribution = {}
    for pb_index, (pb_folder, paths) in enumerate(sorted(pb_groups.items()), 1):
        size_for_pb = papers_per_pb + (1 if pb_index <= remainder else 0)
        distribution[pb_folder] = min(size_for_pb, len(paths))
    
    return distribution

def main():
    list_file = "muestras/listado_pdfs.txt"
    sample_size = 1000
    
    print("=" * 80)
    print("COMPARACIÓN DE MÉTODOS DE MUESTREO")
    print("=" * 80)
    
    # Cargar inventario
    all_paths = load_pdf_inventory(list_file)
    print(f"\nTotal de PDFs en inventario: {len(all_paths):,}\n")
    
    # Muestreo aleatorio
    print("-" * 80)
    print("MÉTODO 1: MUESTREO ALEATORIO (Actual)")
    print("-" * 80)
    random_dist = simulate_random_sampling(all_paths, sample_size)
    
    total_random = sum(random_dist.values())
    print(f"\n{'PB':<35} {'Papers':>6} {'%':>6} {'Dev. Ideal':>10}")
    print("-" * 60)
    
    for pb in sorted(random_dist.keys()):
        count = random_dist[pb]
        pct = (count / total_random) * 100
        ideal = (sample_size / len(random_dist))
        deviation = count - ideal
        print(f"{pb:<35} {count:>6} {pct:>5.1f}% {deviation:>10.1f}")
    
    print(f"\nTotal: {total_random}")
    
    # Muestreo estratificado
    print("\n" + "-" * 80)
    print("MÉTODO 2: MUESTREO ESTRATIFICADO EQUILIBRADO (Propuesto)")
    print("-" * 80)
    stratified_dist = simulate_stratified_sampling(all_paths, sample_size)
    
    total_stratified = sum(stratified_dist.values())
    print(f"\n{'PB':<35} {'Papers':>6} {'%':>6} {'Dev. Ideal':>10}")
    print("-" * 60)
    
    for pb in sorted(stratified_dist.keys()):
        count = stratified_dist[pb]
        pct = (count / total_stratified) * 100
        ideal = (sample_size / len(stratified_dist))
        deviation = count - ideal
        print(f"{pb:<35} {count:>6} {pct:>5.1f}% {deviation:>10.1f}")
    
    print(f"\nTotal: {total_stratified}")
    
    # Comparación
    print("\n" + "=" * 80)
    print("ANÁLISIS COMPARATIVO")
    print("=" * 80)
    
    print(f"\nDesviación estándar de distribución:")
    
    ideal_per_pb = sample_size / len(random_dist)
    
    random_values = list(random_dist.values())
    random_mean = sum(random_values) / len(random_values)
    random_variance = sum((x - random_mean) ** 2 for x in random_values) / len(random_values)
    random_std = random_variance ** 0.5
    
    stratified_values = list(stratified_dist.values())
    stratified_mean = sum(stratified_values) / len(stratified_values)
    stratified_variance = sum((x - stratified_mean) ** 2 for x in stratified_values) / len(stratified_values)
    stratified_std = stratified_variance ** 0.5
    
    print(f"  Aleatorio:        σ = {random_std:.2f} papers")
    print(f"  Estratificado:    σ = {stratified_std:.2f} papers")
    print(f"  Mejora:           {((random_std - stratified_std) / random_std * 100):.1f}%")
    
    print(f"\nRango de distribución (papers por PB):")
    print(f"  Aleatorio:        {min(random_values)} - {max(random_values)} (rango: {max(random_values) - min(random_values)})")
    print(f"  Estratificado:    {min(stratified_values)} - {max(stratified_values)} (rango: {max(stratified_values) - min(stratified_values)})")
    
    print(f"\nEquilibrio:")
    random_coeff_var = (random_std / random_mean) * 100 if random_mean > 0 else 0
    stratified_coeff_var = (stratified_std / stratified_mean) * 100 if stratified_mean > 0 else 0
    
    print(f"  Aleatorio (CV%):       {random_coeff_var:.1f}%")
    print(f"  Estratificado (CV%):   {stratified_coeff_var:.1f}%")
    
    print("\n" + "=" * 80)
    print("RECOMENDACIÓN")
    print("=" * 80)
    print(f"""
El muestreo ESTRATIFICADO EQUILIBRADO garantiza:

✓ Representación equitativa de cada Planetary Boundary
✓ Evita sesgos hacia PBs con más papers disponibles
✓ Mejor distribución estadística para análisis comparativos
✓ Varianza reducida en la distribución (~{((random_std - stratified_std) / random_std * 100):.0f}%)

Para usar el método estratificado, ejecuta:

    python pipeline/extract_corpus_balanced.py

Este generará una muestra en:
    muestras/muestra_seleccionada_1000_balanced.csv

En lugar de:
    muestras/muestra_seleccionada_1000.csv
""")
    print("=" * 80)

if __name__ == "__main__":
    main()
