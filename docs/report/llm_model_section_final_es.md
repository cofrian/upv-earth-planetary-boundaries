# Sección para el report final: clasificación LLM de Planetary Boundaries

> Esta sección está pensada para integrarse en el informe final de UPV-EARTH dentro de los apartados de metodología, modelos, evaluación e iteración. Está escrita con foco en la parte de modelos de la rúbrica: elección técnica justificada, comparación de alternativas, protocolo de evaluación, mejora incremental, limitaciones y valor real del sistema.

## 1. Objetivo de modelado

La parte LLM del proyecto UPV-EARTH aborda la clasificación automática de publicaciones científicas de la UPV respecto al marco de las 9 Planetary Boundaries (PBs). La unidad de análisis es el abstract limpio de cada publicación, enriquecido con metadatos auxiliares cuando están disponibles. La salida del sistema no es una etiqueta temática genérica, sino una decisión científica estructurada: una PB primaria, posibles PBs secundarias, una lista de PBs rechazadas y una explicación textual del razonamiento.

Desde el inicio se descartó tratar el problema como una simple búsqueda de palabras clave. En un corpus politécnico aparecen términos como "water", "climate", "aerosol", "soil", "energy" o "biodiversity" en contextos muy distintos. Un paper puede mencionar el cambio climático como motivación de fondo sin estudiar ninguna variable climática; otro puede ser de ingeniería hidráulica y usar "water" sin tratar consumo global de agua dulce; otro puede hablar de sostenibilidad o política ambiental sin medir procesos biofísicos. El riesgo principal era por tanto el positivity bias o green hallucination: asignar PBs a cualquier documento con vocabulario ambiental superficial.

Por esa razón, el problema se formuló como una tarea de clasificación científica con abstención. El modelo debe poder responder `None` cuando no hay una PB activamente estudiada. En términos operativos, una PB se considera activa si el abstract mide, modela o impone experimentalmente una variable relacionada con esa frontera. Esta definición fue clave para separar tres niveles que suelen confundirse:

- **Mención contextual**: el abstract usa vocabulario ambiental como motivación, pero no lo estudia.
- **Afinidad temática**: el abstract pertenece a un área próxima, como ingeniería, agricultura o planificación urbana, pero no cuantifica el proceso PB.
- **Activación PB real**: el abstract mide, modela o manipula una variable que encaja con la definición y la lógica de activación de una PB.

Esta distinción convirtió el prompt en una pieza metodológica central, no en un simple envoltorio de inferencia.

## 2. Datos, ground truth y protocolo de validación

El desarrollo se realizó sobre el corpus curado definido en la entrega M2. La muestra inicial de 1,000 documentos se filtró mediante deduplicación y umbral mínimo de 500 caracteres en el abstract, produciendo una vista minable de 696 documentos con abstract suficientemente informativo. Para la fase final también existe un corpus institucional ampliado de 31,634 documentos limpios, pero la evaluación controlada de modelos se hizo sobre el subconjunto manualmente validado, porque es el único que permite medir rendimiento de forma honesta.

El ground truth está en `nlp/llm/outputs/ground_truth/validacion_real.csv`. Contiene 208 filas revisadas manualmente, con columnas `1stpb`, `2ndpb` y `3rdpb`. Al cruzarlo con el corpus enriquecido usado por los runners LLM, se obtienen aproximadamente 150 decisiones evaluables. Hay 149 doc_ids únicos y 150 filas de evaluación porque el ground truth contiene algún documento duplicado con criterios de etiquetado distintos; esto se mantiene en las métricas para ser consistente con los notebooks de análisis, pero se documenta como una fuente de ruido.

El ground truth tiene naturaleza multi-etiqueta: un paper puede pertenecer a PB1 y PB4, o a PB9 y PB1, etc. Sin embargo, la evaluación principal se hizo sobre la primera PB humana (`1stpb`) frente a la PB primaria del modelo. Para no perder información multi-etiqueta, también se midieron métricas relajadas:

- **Top-1 estricto**: la PB primaria del modelo coincide exactamente con `1stpb`.
- **Hit@K / Top-2**: la PB humana aparece en la salida del modelo, ya sea como primaria o secundaria.
- **Exact Match de conjunto**: el conjunto de PBs predicho coincide con el conjunto humano.
- **Jaccard**: solapamiento entre conjunto humano y conjunto predicho.
- **Hamming Loss**: fracción de errores sobre las 9 PBs posibles.
- **True Negative / Rigorousness**: proporción de documentos humanos `None` que el modelo rechaza correctamente.
- **Positivity Bias**: proporción de documentos humanos `None` a los que el modelo asigna alguna PB.
- **PB-only accuracy**: rendimiento sobre documentos donde sí hay PB humana.
- **None-only accuracy**: rendimiento sobre documentos sin PB humana.

Esta batería de métricas evita optimizar una única cifra. En este problema, subir recall asignando PBs a casi todo no sirve, porque contamina el mapa institucional. Tampoco sirve rechazar casi todo como `None`, porque se pierden contribuciones reales. La evaluación debe capturar el equilibrio entre cobertura y rigor.

## 3. Marco de referencia PB como base del prompt

La pieza semántica central del sistema es `corpus_PB/data/pb_reference.csv`. Este archivo operacionaliza las 9 Planetary Boundaries en columnas utilizables por modelos y módulos deterministas:

- `pb_code` y `pb_name`: identificador y nombre de la frontera.
- `short_definition`: definición científica breve.
- `core_keywords`, `extended_keywords`, `applied_keywords_upv`: vocabulario estratificado.
- `activation_logic`: condiciones bajo las cuales la PB debe activarse.
- `exclusion_notes`: condiciones que obligan a rechazar la PB aunque haya vocabulario superficial.
- `source_basis`: trazabilidad hacia documentos de referencia del proyecto.

La evolución metodológica importante fue pasar de "definiciones de PB" a "reglas de activación y exclusión". Por ejemplo:

- PB1 no se activa por cualquier paper de energía; requiere emisiones, calentamiento, forzamiento radiativo, escenarios climáticos o impacto climático explícito.
- PB2 no se activa por cualquier estudio marino; requiere acidificación, pH, carbonato, aragonito o efectos de acidez.
- PB4 no se activa por agricultura en general; requiere nitrógeno, fósforo, eutrofización, fertilización o alteración de ciclos biogeoquímicos.
- PB5 no se activa por calidad de agua o tratamiento de aguas; requiere cantidad, extracción, escasez, caudal, riego o presión sobre agua dulce.
- PB7 no se activa por "naturaleza" o "conservación" genérica; requiere biodiversidad, especies, integridad ecosistémica, diversidad funcional/genética, pérdida de hábitat, etc.
- PB8 exige sustancia o entidad novedosa concreta: plásticos, PFAS, pesticidas, fármacos, nanomateriales, sustancias persistentes o tóxicas.
- PB9 exige partículas o aerosoles: PM2.5, PM10, AOD, black carbon, sulfate aerosols, aerosol-cloud interactions, etc.

Estas reglas se inyectan dinámicamente en cada prompt, de modo que la decisión del LLM queda anclada en el marco del proyecto y no solo en el conocimiento pre-entrenado del modelo.

## 4. Infraestructura de inferencia

Los modelos se ejecutaron localmente mediante Ollama. Esto fue importante por tres motivos: coste cero por llamada, privacidad del corpus institucional y reproducibilidad en una VM controlada. Los runners usan Python, peticiones HTTP al endpoint local de Ollama y guardado incremental en CSV para no perder ejecuciones largas.

Las decisiones técnicas más relevantes fueron:

- **Modelos locales open-weight**: principalmente `qwen2.5:14b` para clasificación, `qwen2.5:3b` para extracción auxiliar y pruebas con `gemma4:26b` como modelo más grande.
- **Temperatura 0.0**: se prioriza determinismo y comparabilidad entre versiones.
- **JSON mode**: las salidas se fuerzan a JSON para poder parsear `primary_pb`, `secondary_pbs`, `rejected_pbs`, `confidence` y `reasoning_process`.
- **Preflight de modelos**: el pipeline comprueba que Ollama responde y que los modelos están descargados antes de empezar, evitando runs corruptos por errores 404.
- **Guardado incremental**: cada fila se escribe inmediatamente en CSV para tolerar caídas.
- **Pipeline resumible**: los doc_ids ya procesados se omiten salvo que se use `--no-resume`.
- **Control de VRAM**: `keep_alive="10m"` evita que modelos cargados indefinidamente bloqueen la GPU.

La explicación generada por el LLM se guarda como parte del output. Esto no es solo "texto bonito": permite auditoría cualitativa de errores, identificación de patrones de fallo y revisión humana posterior.

## 5. Evolución de modelos y prompts

La parte más importante para la rúbrica es que no se probó un único modelo, sino una secuencia de hipótesis, errores medidos e iteraciones. La evolución puede resumirse como un proceso de calibración entre dos fallos opuestos:

- **Sobre-asignación**: el modelo ve PBs en cualquier paper con lenguaje ambiental.
- **Infra-asignación**: el modelo se vuelve tan estricto que rechaza papers realmente relevantes.

### 5.1 Baseline zero-shot estricto

El primer baseline fuerte fue `qwen2.5:14b` con un prompt zero-shot estructurado. Incluía rol de evaluador científico, reglas PB, exclusiones, extracción conceptual y salida JSON. El objetivo era medir si un LLM mediano podía aplicar el marco PB sin ejemplos.

Resultados sobre 150 filas:

- Top-1: **63.3%**
- PB-only accuracy: **52.5%**
- None-only accuracy / rigorousness: **84.3%**
- Positivity bias: **15.7%**
- Jaccard: **0.626**
- Hamming loss: **0.064**

El comportamiento fue conservador. Rechazaba bien documentos irrelevantes, pero perdía demasiados papers con PB real. Los errores más frecuentes fueron `PB1 -> None`, `PB7 -> None` y `PB9 -> None`. Este baseline demostró que las reglas de exclusión funcionaban, pero también que el modelo se "acobardaba" ante casos complejos.

### 5.2 Few-shot v1: el fallo del ejemplo rígido

La siguiente hipótesis fue añadir ejemplos few-shot para enseñar casos frontera. Intuitivamente, esto debería ayudar. Empíricamente ocurrió lo contrario.

Resultados:

- Top-1: **57.3%**
- PB-only accuracy: **44.4%**
- None-only accuracy: **82.4%**
- Positivity bias: **17.6%**
- PB7 recall: **0%**
- Jaccard: **0.573**

El análisis cualitativo reveló el "efecto loro": el modelo reutilizaba frases del prompt en vez de razonar sobre el abstract. En particular, internalizó reglas espurias, como tratar PB7 como un efecto secundario de PB1 en vez de permitir que biodiversidad fuese la frontera primaria. También usó la exclusión social/política como comodín incluso cuando el paper sí contenía métricas biofísicas. Esta iteración es valiosa precisamente porque muestra una decisión negativa justificada: no todo few-shot mejora un LLM; ejemplos mal diseñados pueden producir sobreajuste narrativo.

### 5.3 Few-shot v2 / zero-shot CoT: checklist deductivo

Para corregir v1, se eliminaron los ejemplos rígidos y se sustituyeron por un algoritmo deductivo obligatorio:

1. Extraer métricas físicas, químicas, biológicas o ecológicas explícitas.
2. Mapear cada métrica candidata a PBs.
3. Aplicar reglas de exclusión.
4. Jerarquizar primaria y secundarias.
5. Emitir JSON.

Resultados:

- Top-1: **64.0%**
- PB-only accuracy: **69.7%**
- None-only accuracy: **52.9%**
- Positivity bias: **47.1%**
- Jaccard: **0.596**

V2 solucionó parte del problema de recall: encontraba muchos más papers con PB real. Pero lo hizo a costa de disparar falsos positivos. El positivity bias subió a casi la mitad de los documentos humanos `None`, lo que hacía la versión inaceptable para producción. Esta iteración enseñó que un checklist demasiado imperativo puede empujar al modelo a "pescar" cualquier métrica posible.

### 5.4 Few-shot v3: filtro background-vs-focus

V3 mantuvo el razonamiento paso a paso, pero reforzó la distinción entre lo que el paper realmente mide/modela y lo que aparece solo como contexto. También añadió una reverificación para textos sociales, legales, de gobernanza, educación o software.

Resultados:

- Top-1: **65.3%**
- PB-only accuracy: **58.6%**
- None-only accuracy: **78.4%**
- Positivity bias: **21.6%**
- Jaccard: **0.604**

V3 corrigió gran parte del exceso de positividad de v2, pero volvió a perder recall en algunas clases. Es una versión más equilibrada que v2, aunque todavía por debajo del potencial del modelo.

### 5.5 V4 principle-driven: objeto operacional y calibration cases

La versión v4 fue el salto principal. Se reformuló el prompt con etiquetas XML y con un principio explícito: la PB primaria es la variable que el paper cuantifica, modela o impone experimentalmente, no la PB más mencionada retóricamente en la introducción.

La diferencia con v1 es importante. V4 no usa ejemplos como plantillas de respuesta, sino como calibration cases. Además, el prompt prohíbe reutilizar frases de esos casos. Los tres documentos usados como calibración se excluyen de la evaluación para no medir memorización.

El prompt introduce confusiones frecuentes:

- Aerosoles, PM y AOD son PB9, no PB1.
- PB1 requiere clima activo: medido, modelado o impuesto como escenario/tratamiento.
- Papers de gestión de agua con clima solo como motivación son PB5, no PB1.
- Respuestas ecológicas y biodiversidad pueden ser PB7 primaria.
- Nutrientes N/P apuntan a PB4.

Resultados sobre 147 filas cruzadas:

- Top-1: **72.1%**
- PB-only accuracy: **70.1%**
- None-only accuracy: **76.0%**
- Hit@K: **74.8%**
- Exact Match de conjunto: **60.5%**
- Jaccard: **0.688**
- Hamming loss: **0.060**
- Positivity bias: **24.0%**
- Macro-F1: **0.679**
- Weighted-F1: **0.718**
- Tiempo medio por inferencia: aproximadamente **5 s/documento** en el análisis comparativo.

V4 fue la mejor versión single-model. Su mejora no viene de sacrificar una métrica por otra: gana claramente en las métricas de acierto y se mantiene razonablemente alto en rechazo de `None`. Frente a v3, el análisis pareado mostró 15 documentos donde v4 acierta y v3 falla, frente a solo 4 donde ocurre lo contrario. Por tanto, la mejora no es un artefacto agregado, sino una ganancia real a nivel documento.

## 6. Comparativa global de sistemas LLM

Tabla recomputada desde los CSV actuales de `nlp/llm/outputs/inferences/` y `nlp/llm/outputs/pipeline_cascada/`.

| Sistema | n eval | Top-1 | PB-only | None-only | Hit@K / Top-2 | Exact set | Jaccard | Hamming ↓ | Positivity bias ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen 14B zero-shot | 150 | 63.3% | 52.5% | 84.3% | 66.0% | 56.0% | 0.626 | 0.064 | 15.7% |
| Qwen 14B v1 contrastivo | 150 | 57.3% | 44.4% | 82.4% | 61.3% | 52.0% | 0.573 | 0.067 | 17.6% |
| Qwen 14B v2 CoT guiado | 150 | 64.0% | 69.7% | 52.9% | 66.0% | 50.7% | 0.596 | 0.070 | 47.1% |
| Qwen 14B v3 focus filter | 150 | 65.3% | 58.6% | 78.4% | 67.3% | 53.3% | 0.604 | 0.071 | 21.6% |
| Qwen 14B v4 principle | 147 | **72.1%** | 70.1% | **76.0%** | 74.8% | **60.5%** | **0.688** | **0.060** | 24.0% |
| Cascada multi-agente base | 150 | 64.0% | 60.6% | 70.6% | 68.0% | 54.0% | 0.623 | 0.073 | 29.4% |
| Cascada + critic inicial | 150 | 65.3% | 62.6% | 70.6% | 69.3% | 54.7% | 0.633 | 0.072 | 29.4% |
| Cascada v3 lean + critic (último run) | 150 | **71.3%** | **71.7%** | 70.6% | **80.0%** | 58.0% | 0.666 | 0.064 | 29.4% |

La mejor variante estrictamente por Top-1 sigue siendo Qwen v4 single-model, con 72.1%. La última cascada queda muy cerca, con 71.3%, y mejora la cobertura Top-2 hasta 80.0%. Esta diferencia explica la recomendación final:

- Para **batch labeling** donde importa maximizar exactitud primaria, v4 principle-driven es la opción más limpia.
- Para **sistema auditable y human-in-the-loop**, la cascada es más defendible porque produce trazas intermedias: extracción del agente pequeño, evidencias léxicas, razonamiento del juez y posible revisión del critic.

## 7. Modelos grandes: Gemma 26B y selección de Qwen

Durante M2 se compararon escalas de modelo: Llama 3.1 8B, Qwen 2.5 14B y Gemma 4 26B. La conclusión cualitativa fue que Gemma era mejor como auditor conceptual: detectaba rutas químicas o biofísicas más profundas, por ejemplo relacionando SO2 con sulfatos particulados o distinguiendo un estudio literario sobre crisis climática de un paper climático real. Sin embargo, Gemma tenía dos problemas para producción:

- **Latencia**: en la evaluación M2 rondaba 22.9 s/documento frente a unos 6.1 s/documento de Qwen.
- **Robustez operativa**: los runners finales muestran que Gemma requería más cuidado con formato chat y JSON schema para evitar outputs inválidos o tokens basura.

Por esto, Gemma se mantuvo como referencia cualitativa y posible fuente de destilación futura, pero Qwen 2.5 14B fue seleccionado como compromiso operativo: suficientemente razonador, mucho más rápido y estable en Ollama.

Esta decisión no fue solo "elegir el que más acierta". Fue una decisión de sistema: el objetivo final es procesar miles o decenas de miles de publicaciones, no solo ganar una tabla pequeña. En ese contexto, una arquitectura mediana con prompts robustos y auditoría posterior es más viable que un modelo grande lento y difícil de estabilizar.

## 8. Arquitectura multi-agente final

La iteración final exploró una cascada multi-agente implementada en `nlp/llm/runners/pipeline_agentes.py`. La idea no era reemplazar el prompt v4, sino enriquecerlo con señales independientes.

### 8.1 Agente 1: extractor estructurado (`qwen2.5:3b`)

El agente pequeño no decide la PB. Extrae campos estructurados:

- `chemical_species`
- `physical_metrics`
- `biological_observations`
- `methodology`: `measured`, `modelled`, `mentioned` o `none`
- `disciplinary_frame`: ingeniería, earth sciences, biología, química, social sciences, economics, law/policy, education u other

Para evitar alucinaciones, el prompt exige que cada string extraído aparezca literalmente en el título o abstract. Además, el código aplica un filtro posterior de grounding: cualquier item que no aparezca en el texto se descarta. Esto responde directamente a un fallo observado en prompts anteriores: los modelos pequeños copian ejemplos o inventan variables si se les deja demasiado margen.

### 8.2 Scorer determinista por vocabulario

El segundo módulo no usa LLM. Calcula overlap entre `title + clean_abstract + top_terms_no_stopwords` y el vocabulario de `pb_reference.csv`, con pesos:

- `core_keywords`: peso 3
- `extended_keywords`: peso 2
- `applied_keywords_upv`: peso 1

Cada keyword cuenta como máximo una vez y se descartan términos de menos de 4 caracteres. El resultado es una lista de candidatos tipo `PB1(6); PB5(3)` junto con las keywords que activaron la señal.

Este módulo es transparente y barato. Su limitación es la cobertura léxica: si PB8 no contiene heavy metals, un paper sobre Pb, Cu o Mn puede quedar sin candidato aunque sea relevante. Por eso el scorer se usa como pista, no como verdad.

### 8.3 Router de consenso

El router solo evita llamar al modelo grande cuando hay consenso fuerte de irrelevancia:

1. El Agente 1 devuelve cero items y un marco no biofísico.
2. El scorer no encuentra candidatos con score suficiente.

En el último run el fast-skip se activó en 5 casos y no introdujo errores, pero su impacto en coste es pequeño. Su valor principal es demostrar que el sistema puede incorporar rutas baratas sin sacrificar calidad.

### 8.4 Agente 3: juez experto (`qwen2.5:14b`)

El Agente 3 es el clasificador principal. Recibe:

- El abstract crudo.
- Las reglas PB completas.
- Los calibration cases v4.
- La extracción del Agente 1.
- El ranking del scorer.

En la versión final, las señales auxiliares se colocan después del abstract y se etiquetan explícitamente como no autoritativas. Esto fue una corrección importante: en runs previos, el 14B se anclaba demasiado en `kw_top` o en la salida del extractor. Si `kw_top` empataba PB1 y PB2, el modelo podía elegir PB1 por posición, aunque el abstract tratase ocean acidification. La versión final avisa al modelo de que los empates no son significativos y de que debe resolver leyendo el abstract.

### 8.5 Agente 4: critic asimétrico

El critic se invoca solo cuando:

- El Agente 3 responde `None`.
- El scorer sí encontró al menos una PB candidata.

El critic solo puede cambiar `None -> PBx`. No puede degradar `PBx -> None` ni inventar una PB fuera de los candidatos. Esta asimetría se diseñó a partir de un diagnóstico empírico: una parte de los errores eran falsos negativos, pero no queríamos abrir una segunda pasada que destruyese aciertos o aumentase aún más el positivity bias.

En el último run (`pipeline_20260510_192035.log`) la cascada procesó 149 doc_ids únicos, generó 150 filas de evaluación al cruzar con el GT, activó fast-skip 5 veces, llamó al juez grande 144 veces, invocó el critic 5 veces y produjo 2 overrides. El resultado final fue:

- Accuracy vs GT 1st PB: **107/150 = 71.3%**
- Top-2 hit: **120/150 = 80.0%**

La cascada no supera claramente a v4 en Top-1, pero ofrece la mejor cobertura Top-2 y un diseño más auditable. Este es un resultado honesto y defendible: la arquitectura multi-agente aporta trazabilidad y capacidad de revisión, aunque no siempre aumenta la métrica primaria.

## 9. Diagnóstico de errores

El análisis de errores reveló patrones útiles para futuras iteraciones.

### 9.1 Falsos positivos por ground truth discutible

Algunos casos donde el humano etiquetó `None` y el modelo predijo una PB no son necesariamente errores obvios del modelo. Por ejemplo, papers sobre PM2.5, black carbon, aerosol optical depth o aerosoles urbanos pueden haber sido marcados como `None` en la validación inicial, pero desde el marco PB9 sí contienen variables activas. Esto sugiere ruido de ground truth y falta de doble anotación independiente.

### 9.2 Confusión macro-driver vs micro-impact

Varios fallos ocurren cuando el abstract menciona cambio climático como driver, pero el fenómeno medido pertenece a otra PB. Ejemplos:

- Warming como causa, pero impacto real en genes microbianos o ecosistemas: PB7 puede ser primaria.
- Clima como escenario, pero variable operacional de agua: PB5.
- Dust o aerosoles como vector, pero medición principal de nutrientes: PB4.

V4 mejora este problema con el principio de "operational object".

### 9.3 Anclaje en señales auxiliares

La cascada introdujo una fuente nueva de error: si el scorer o el extractor proponen una PB incorrecta, el juez 14B puede anclarse en ella. Esto explica que la primera cascada rindiera peor que v4. La mitigación fue reordenar el prompt, mover señales auxiliares al final y declararlas explícitamente como falibles.

### 9.4 Vocabulario incompleto en PB8 y PB1

PB8 tiene baja cobertura cuando aparecen contaminantes como heavy metals no recogidos en la lista de novel entities. PB1 también puede perder paleoclimate proxies o indicadores indirectos si no aparecen términos clásicos de climate change. La mejora natural es expandir `pb_reference.csv` mediante minería de errores.

### 9.5 Clases con bajo soporte

PB5 y PB6 tienen soporte muy bajo en la validación final (`n=4` cada una en varias evaluaciones). No se deben sacar conclusiones fuertes por PB individual con tan pocos ejemplos. Para estas clases conviene informar macro-F1, pero también advertir que la incertidumbre estadística es alta.

## 10. Comparación con modelos embedding/BERT

Además de LLMs, el proyecto evaluó baselines de embeddings y modelos tipo BERT/SciBERT/SPECTER en `nlp/bert_finetuning/outputs/`. La mejor referencia no generativa actual es `baseline_semantic_tfidf` top-1, con:

- Micro-F1: **0.484**
- Macro-F1: **0.439**
- Jaccard: **0.367**
- Exact Match: **0.280**
- LRAP: **0.730**

También se evaluaron BERT, RoBERTa, SciBERT y SPECTER. SPECTER con threshold/delta alcanzó Micro-F1 **0.405** y Macro-F1 **0.399**, y el baseline lexical threshold/delta alcanzó Micro-F1 **0.485**. Estos resultados muestran dos cosas:

1. Los métodos transparentes son sorprendentemente competitivos en vocabulario científico.
2. Los LLMs aportan una capa que los embeddings no capturan bien: capacidad de rechazar usos contextuales, explicar la decisión y distinguir objeto operacional frente a motivación.

La solución final no abandona las señales léxicas; las incorpora como scorer determinista dentro de la cascada.

## 11. Limitaciones

Las limitaciones principales son:

- **Ground truth limitado y ruidoso**: 150 filas evaluables no bastan para estimar con precisión clases minoritarias. Hay duplicados y casos discutibles.
- **Sin acuerdo inter-anotador**: falta medir cuán consistente sería la clasificación humana entre varios revisores.
- **Dependencia del abstract**: algunos papers pueden requerir full text para decidir correctamente.
- **Auto-confianza no calibrada**: `High/Medium/Low` es útil como señal cualitativa, pero no equivale a probabilidad real.
- **Prompts largos**: mejoran contexto, pero aumentan coste y pueden introducir lost-in-the-middle.
- **Riesgo de overfitting al subset**: cada iteración se evaluó sobre el mismo conjunto pequeño; la validación externa sería el siguiente paso.
- **Salida multi-etiqueta infraexplotada**: la cascada predice secundarias, pero gran parte del análisis sigue usando la primera PB humana como referencia principal.

Estas limitaciones no invalidan el sistema; delimitan su modo de uso. El clasificador no debe presentarse como autoridad final automática, sino como herramienta de priorización y auditoría para curación humana.

## 12. Valor del enfoque

El valor del componente LLM no es únicamente subir una métrica. Aporta:

- **Escalabilidad**: permite pasar de revisión manual de decenas de papers a procesamiento de miles.
- **Auditabilidad**: cada decisión incluye razonamiento y evidencias intermedias.
- **Flexibilidad científica**: las reglas PB pueden editarse sin reentrenar un modelo.
- **Privacidad**: la inferencia local evita enviar abstracts institucionales a APIs externas.
- **Human-in-the-loop**: casos con baja confianza o discrepancias pueden priorizarse para revisión.
- **Reutilización**: la arquitectura se puede adaptar a SDGs, áreas estratégicas UPV u otros marcos de impacto.

Para el producto UPV-EARTH, el uso realista es un sistema de screening: el modelo propone PBs, justifica la decisión y permite que un experto revise casos límite. Esto reduce carga manual y mejora trazabilidad institucional, pero evita presentar el LLM como juez final infalible.

## 13. Próximos pasos técnicos

Los siguientes pasos más defendibles son:

1. **Reanotación doble del ground truth**: al menos dos revisores independientes y cálculo de acuerdo.
2. **Evaluación multi-etiqueta completa**: usar todas las columnas `1stpb`, `2ndpb`, `3rdpb`, no solo primaria.
3. **Expansión de `pb_reference.csv` desde errores**: heavy metals para PB8, paleoclimate proxies para PB1, términos de conservación para PB7.
4. **Critic ampliado**: permitir revisión no solo de `None -> PBx`, sino también de casos de baja confianza o desacuerdo fuerte con `kw_top`.
5. **Calibración de abstención**: introducir estado `Uncertain` para enviar a humano.
6. **Destilación de razonamientos Gemma -> Qwen**: usar Gemma como auditor offline para mejorar prompts o crear datos débiles.
7. **Evaluación externa**: aplicar el sistema a un subconjunto nuevo del corpus institucional ampliado.

## 14. Archivos de trazabilidad

Los artefactos principales están versionados en el repositorio:

- Reglas PB: `corpus_PB/data/pb_reference.csv`
- Ground truth: `nlp/llm/outputs/ground_truth/validacion_real.csv`
- Zero-shot runner: `nlp/llm/runners/qwen_zeroshot.py`
- V2 runner: `nlp/llm/runners/qwen_fewshot_v2.py`
- V3 runner/notebook: `nlp/llm/runners/qwen_fewshot_v3.ipynb`
- V4 runner/notebook: `nlp/llm/runners/qwen_fewshot_v4.ipynb`
- Cascada: `nlp/llm/runners/pipeline_agentes.py`
- Critic post-hoc: `nlp/llm/runners/apply_critic.py`
- Análisis v1-v4: `nlp/llm/analysis/comparacion_fewshot_v1_v2_v3_v4_principle.ipynb`
- Análisis cascada: `nlp/llm/analysis/pipeline_cascada_analysis.ipynb`
- Reporte cascada: `docs/report/multi_agent_pipeline_report.md`
- Figuras listas: `docs/report/figures/`

## 15. Texto breve para cerrar la sección en el paper

En síntesis, la evolución del componente LLM muestra una mejora incremental real y bien diagnosticada. El sistema pasó de prompts ingenuos con sesgo de positividad a un clasificador principle-driven basado en reglas explícitas de activación/exclusión, salida JSON y auditoría por razonamiento. Qwen 2.5 14B v4 alcanzó el mejor Top-1 single-model (72.1%), mientras que la cascada multi-agente final alcanzó 71.3% Top-1 y 80.0% Top-2, añadiendo trazabilidad mediante extracción estructurada, scoring determinista y critic asimétrico. El resultado final no debe interpretarse como una sustitución completa del juicio experto, sino como una herramienta escalable y auditable para priorizar, explicar y revisar la contribución científica de la UPV al marco de Planetary Boundaries.
