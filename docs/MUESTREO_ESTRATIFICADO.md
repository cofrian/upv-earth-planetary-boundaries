# Muestreo Estratificado Equilibrado - Guía de Uso

## 📋 Resumen

Se ha creado una **copia mejorada** del script de extracción de corpus que genera una **muestra estratificada equilibrada** en lugar de muestreo aleatorio. Esto garantiza que cada Planetary Boundary (PB) tenga la **misma cantidad de papers** en la muestra.

## 📁 Archivos Creados

### 1. `extraccion_corpus_mixto_balanced.py`
**Archivo principal modificado** que incluye:
- Nueva función `build_balanced_sample()` para muestreo estratificado
- Función original `build_random_sample()` mantenida para referencia
- Configuración idéntica al original

### 2. `scripts/auxiliary/compare_sampling_methods.py`
**Script de comparación** que simula ambos métodos y muestra:
- Distribución por PB en ambos métodos
- Desviación estándar (mejora del 99.5%)
- Rango de variación
- Estadísticas de equilibrio

## 🎯 Comparación: Aleatorio vs Estratificado

### Muestreo Aleatorio (Actual)
```
PB1 (Climate Change):         262 papers (26.2%)  ← Sesgo hacia PBs populares
PB2 (Ocean Acidification):    106 papers (10.6%)
PB3 (Ozone Depletion):         73 papers (7.3%)   ← Subrepresentado
...
Desviación estándar:          σ = 57.19 papers
Coeficiente de variación:     CV = 51.5%
```

### Muestreo Estratificado Equilibrado (Propuesto)
```
PB1 (Climate Change):         111 papers (11.1%)  ✓ Equilibrado
PB2 (Ocean Acidification):    111 papers (11.1%)  ✓ Equilibrado
PB3 (Ozone Depletion):        111 papers (11.1%)  ✓ Equilibrado
...
Desviación estándar:          σ = 0.31 papers
Coeficiente de variación:     CV = 0.3%
```

## 🚀 Cómo Usar

### Opción 1: Solo comparar métodos
```bash
uv run --no-project python scripts/auxiliary/compare_sampling_methods.py
```

Esto muestra el análisis comparativo sin modificar nada.

### Opción 2: Generar muestra estratificada
```bash
uv run --no-project python extraccion_corpus_mixto_balanced.py
```

Esto genera:
- **Manifest:** `muestras/muestra_seleccionada_1000_balanced.csv`
- **Corpus procesado:** `data/corpus/master_corpus_mixto_1000_clean.csv`
- **Trazabilidad:** `data/corpus/master_corpus_mixto_1000_traceability.csv`

## 📊 Ventajas del Muestreo Estratificado

| Aspecto | Aleatorio | Estratificado |
|---------|-----------|--------------|
| **Representación PB1** | 26.2% | 11.1% |
| **Representación PB3** | 7.3% | 11.1% |
| **Sesgo** | Alto | Ninguno |
| **Desviación std** | 57.19 | 0.31 |
| **CV%** | 51.5% | 0.3% |
| **Idoneidad para análisis** | Baja | Alta |

## 🔧 Cambios Técnicos

### Cambio Principal
```python
# ANTES (Aleatorio)
def build_random_sample():
    selected = random.sample(all_paths, min(SAMPLE_SIZE, len(all_paths)))

# DESPUÉS (Estratificado)
def build_balanced_sample():
    pb_groups = defaultdict(list)
    for path in all_paths:
        pb_folder, _ = extract_path_parts(path)
        pb_groups[pb_folder].append(path)
    
    # Muestreo equilibrado por PB
    papers_per_pb = SAMPLE_SIZE // len(pb_groups)
    for pb_folder, paths in pb_groups.items():
        sampled = random.sample(paths, papers_per_pb)
```

### Variables Modificadas
```python
SAMPLE_MANIFEST = os.path.join("muestras", "muestra_seleccionada_1000_balanced.csv")
# (era: "muestra_seleccionada_1000.csv")
```

## 📈 Recomendaciones

### ✓ Usar Muestreo Estratificado Cuando:
- Necesitas comparar PBs entre sí
- Quieres análisis equilibrados sin sesgos
- Haces análisis estadísticos por grupo
- Quieres representación equitativa

### ✓ Usar Muestreo Aleatorio Cuando:
- Solo necesitas una muestra representativa general
- No importan los sesgos mínimos
- Quieres mantener proporciones naturales del corpus

## 🔍 Estructura de la Muestra Estratificada

```
Muestra: 1,000 papers
Planetary Boundaries: 9

Distribución ideal:
  1,000 ÷ 9 = 111.11 papers/PB

Distribución real (con remainder):
  PB1-8: 111 papers cada uno
  PB9:   112 papers

Total: 111*8 + 112*1 = 1,000 ✓
```

## 📝 Notas

- El archivo original `extraccion_corpus_mixto.py` **NO se modifica**
- Se puede usar cualquiera de los dos scripts según necesidad
- Ambos generan la misma estructura de datos
- Solo cambia la distribución por PB

## 🎓 Caso de Uso

Para análisis EDA (Exploratory Data Analysis) donde necesitas:
- Comparar patrones entre Planetary Boundaries
- Hacer análisis estadísticos sin sesgos
- Visualizar distribuciones equilibradas
- Entrenar modelos sin sesgo hacia PBs populares

**El muestreo estratificado es la opción recomendada.**

---

**Creado:** 18 de abril de 2026
**Versión:** 1.0
