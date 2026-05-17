# AED — UPV-EARTH × Planetary Boundaries

## Rol y objetivo

Quiero que actúes como un **data scientist curioso y experto** y me hagas el mejor AED posible de los papers y los Planetary Boundaries (PBs).

No quiero que seas superficial: pregúntate cosas, ve más allá. Quiero un AED **redactado** (con interpretación, no solo código y plots), y al mismo tiempo quiero **figuras profesionales** —no genéricas— cuidadas en diseño, como si fueran figuras de paper. Quiero gráficos que **digan información**, no un simple gráfico de barras.
El AED tiene que compensarlo con **profundidad interna**: corpus, PBs, evolución, coocurrencias, modelos, errores e interpretación. La clave es que no parezca "hemos hecho cuatro gráficos", sino "hemos entendido científicamente el corpus y la estructura PB de la producción UPV".
IMPORTANTE: El aed quiero de todos los papers , y el pb que miramremos son los que tengamos del spectra2. 
A todo esto, quier oque me añadas todo lo que se te ocurra e eaed entre pb como relaciones más posibles tipo si un paer trate a del pb1 tendra ráelcio ncon el pb2 que se la has saisgnado....
---

## 1. AED del corpus: demostrar que entendemos los datos

Obligatorio. Antes de hablar de PBs, demostrar que sabemos qué dataset tenemos.

### 1.1. Tamaño y trazabilidad del corpus

Mostrar:

- número inicial de abstracts
- número final tras limpieza
- duplicados eliminados
- abstracts sin texto
- abstracts demasiado cortos
- años cubiertos
- fuentes: Scopus / OpenAlex

No es solo administrativo: justifica la calidad del dataset y la muestra final. El paper UPV-ODS trabaja también con ~50.000 abstracts de Scopus filtrados por longitud; lógica parecida.

**Figura recomendada — Corpus flow diagram:**

```text
Raw Scopus + OpenAlex
        ↓
Merged corpus
        ↓
Deduplicated corpus
        ↓
Filtered abstracts
        ↓
Final corpus
```

Con números grandes en cada caja.

### 1.2. Distribución temporal de publicaciones

Cómo evoluciona el número de publicaciones UPV por año.

**Por qué importa:** si luego decimos que aumentan los papers PB, hay que distinguir si:

- la UPV publica más en general, o
- aumenta el peso relativo de ciertos PBs.

**Figuras:** línea o barras de publicaciones/año, área suavizada, evolución acumulada.

### 1.3. Calidad textual de los abstracts

Analizar: longitud, distribución de tokens, abstracts muy cortos, idioma si lo hay, nulos por columna.

**Por qué importa:** los modelos NLP dependen de la calidad del texto.

**Figuras:** histograma de longitud, boxplot por año, heatmap de completitud de metadatos.

---

## 2. AED del corpus PB: demostrar que las etiquetas están bien pensadas

No tratar los PBs como simples etiquetas sin explicar cómo se construyen.

Para cada PB documentar:

- definición corta
- keywords principales
- términos relacionados
- ejemplos de frases
- notas de desambiguación

El paper PB–SDG usa definiciones explícitas de los PBs dentro de la pipeline para evitar clasificación vaga. Esa idea es aplicable: las clases PB deben estar definidas de forma **operativa**.

**Figura recomendada — PB reference map:** panel con los 9 PBs, cada uno con nombre corto, 3–5 keywords, familia temática y color asignado.

---

## 3. AED de distribución PB: qué límites aparecen más y menos

Corazón del AED.

### 3.1. Frecuencia absoluta por PB

Cuántos papers se asignan a cada Planetary Boundary.

### 3.2. Frecuencia relativa

Porcentaje del corpus total o del corpus PB-related.

### 3.3. PBs dominantes e infrarrepresentados

Decir claramente:

- cuáles dominan
- cuáles aparecen poco
- si tiene sentido por el perfil tecnológico de la UPV

El paper UPV-ODS hace una lectura parecida: identifica ODS más representados (energía, industria, innovación) y ODS con impacto potencial más limitado.

**Figuras:**

- **Figura 1:** Ranking horizontal tipo **lollipop** (mejor que barplot básico).
- **Figura 2:** **Radial plot** PB profile (ver sección dedicada más abajo).
- **Figura 3:** **Treemap** por familias PB:
  - clima/atmósfera
  - agua/suelo/biosfera
  - ciclos químicos/contaminación

---

## 4. AED temporal PB: cómo cambia el perfil en el tiempo

No basta con decir "PB1 es el más frecuente". Ver si el perfil cambia.

### 4.1. Evolución absoluta por PB

Número de papers por PB y año.

### 4.2. Evolución relativa por PB

Porcentaje de cada PB dentro del total anual. Importante porque corrige el crecimiento global del corpus.

### 4.3. Crecimiento por periodos

Comparar:

- 1990–2000
- 2001–2010
- 2011–2015
- 2016–2020
- 2021–2024

### 4.4. PBs emergentes

Qué límites crecen más en los últimos años.

**Figuras:**

- **Figura A — Streamgraph / stacked area** (inspirado en evolución por ODS del paper UPV y slides CRUE).
- **Figura B — Heatmap año × PB**: filas = PBs, columnas = años, color = proporción o número de papers. Muy "de paper".
- **Figura C — Slope chart por periodos**: peso de cada PB en dos periodos (antes/después de 2015, o 1990–2010 vs 2011–2024).

---

## 5. AED de multilabelidad: cuántos PBs aparecen por paper

Muy importante, se olvida a menudo. La tarea es multilabel.

Analizar:

- papers con 0 PBs claros
- papers con 1 PB
- papers con 2 PBs
- papers con 3 o más PBs
- media de PBs por paper
- PBs que suelen aparecer solos
- PBs que suelen aparecer acompañados

**Por qué importa:** los PBs son un marco sistémico. Si muchos papers tienen varios PBs, la investigación UPV toca problemas interconectados.

**Figuras:** histograma de nº PBs por paper, violin/boxplot de scores por nº PBs, barras de single-boundary vs multi-boundary papers.

---

## 6. AED de coocurrencias PB × PB: estructura sistémica

De los bloques más importantes para que el AED no sea genérico.

### 6.1. Matriz de coocurrencia

Qué PBs aparecen juntos en los mismos papers.

### 6.2. Asociación normalizada

No solo contar coocurrencias. Calcular Jaccard:

$$\text{Jaccard}(PB_i, PB_j) = \frac{|PB_i \cap PB_j|}{|PB_i \cup PB_j|}$$

Evita que los PBs grandes dominen solo por tener muchos papers.

### 6.3. Red de PBs

Construir red:

- nodos = PBs
- tamaño = frecuencia
- aristas = coocurrencia
- grosor = intensidad
- color = familia o comunidad

### 6.4. Centralidad

Calcular: degree, weighted degree, betweenness.

**Por qué importa:** conecta con la lógica del paper PB–SDG — no se trata solo de contar categorías, sino de entender interacciones entre límites.

**Figuras obligatorias:**

- **Figura 1 — Heatmap PB × PB**
- **Figura 2 — Network graph de PBs**

---

## 7. AED semántico: estructura interna de los papers

Embeddings, UMAP, LDA, Top2Vec, BERTopic, etc.

### 7.1. Mapa semántico de abstracts

Cada paper como punto en 2D usando UMAP/t-SNE. El TFM Aerospace usa t-SNE/UMAP para visualizar abstracts según SDG/PB asignado: línea alineada con los materiales del profesor.

**Colorear por:**

- PB dominante
- cluster
- año o periodo
- tamaño por número de PBs asignados
- borde para papers validados manualmente

**Qué NO debe ser:** un UMAP con puntos sin más. Debe incluir:

- clusters etiquetados
- centroides
- anotaciones tipo "water systems", "climate modelling", "materials/chemical pollution"
- leyenda limpia

### 7.2. Topics y clusters

Si hay LDA/Top2Vec:

- topics principales
- palabras representativas
- evolución de topics
- relación topic → PB

**Figura — Sankey topics → PBs:** izquierda = topics descubiertos, derecha = PBs, flujo = nº papers. Queda muy potente.

---

## 8. AED de modelos: comparar métodos y no solo resultados

### 8.1. Cobertura por método

Cuántos papers etiqueta cada método: baseline, BERT, LLM, LDA/Top2Vec si aplica.

### 8.2. Acuerdo entre métodos

% de papers con mismo PB entre:

- baseline y BERT
- BERT y LLM
- baseline y LLM

### 8.3. Diferencias por PB

Qué PBs detecta mejor cada método.

### 8.4. Casos de desacuerdo

Ejemplos: BERT dice PB5, LLM dice PB4, baseline falla por keyword.

**Por qué importa:** el paper de Larosa insiste en que los LLMs/NLP deben evaluarse con transparencia, no como caja negra.

**Figuras:**

- matriz de acuerdo método × método
- barras de cobertura por PB y método
- panel de casos frontera

---

## 9. AED de evaluación manual y errores

Obligatorio para rigor.

### 9.1. Tamaño de la muestra manual

- cuántos abstracts
- cómo se seleccionaron
- si hubo doble anotación

### 9.2. Métricas (multilabel)

- precision, recall, F1
- macro/micro si es posible

### 9.3. Rendimiento por PB

Qué PBs tienen mejor/peor clasificación.

### 9.4. Tipos de error

- falso positivo por keyword
- confusión PB4/PB5
- confusión PB6/PB7
- abstract demasiado genérico
- falta de contexto
- LLM sobregeneraliza
- BERT se queda corto semánticamente

**Figuras:**

- **A — Performance panel:** F1 global, F1 por PB, barras por modelo.
- **B — Error taxonomy:** barras por tipo de error.
- **C — Confusion conceptual map:** matriz de confusiones principales entre PBs (no la matriz clásica, porque es multilabel).

---

## 10. AED de interpretabilidad: ejemplos representativos

Diferencia un análisis serio de uno automático.

Para cada PB principal mostrar:

- 1 abstract representativo
- PB asignado
- score
- explicación breve
- keywords/frase que justifican la asignación

Mostrar también:

- un caso bien clasificado
- un caso ambiguo
- un caso donde los modelos discrepan

**Figura — Cards de ejemplos:** 6–9 tarjetas con título corto, PB, score, fragmento relevante, explicación. Queda muy bien en presentación.

---

## 11. AED de "contribución": si hay LLM, usarlo para algo más profundo

Aunque no hagamos World Bank, podemos añadir valor con una capa de **tipo de contribución**.

Categorías:

- **Monitoring / Diagnosis:** estudia o mide el problema.
- **Mitigation / Solution:** propone reducción de presión o solución.
- **Pressure / Risk:** describe impactos o presiones negativas.
- **Methodological / Enabling:** desarrolla método, modelo o herramienta.
- **Ambiguous / Weak:** relación débil o no clara.

Analizar:

- tipo de contribución por PB
- qué PBs tienen más soluciones
- qué PBs dominados por diagnóstico
- qué PBs con más presión/riesgo

**Figura — Stacked bars por PB:** cada barra = PB, segmentos = contribution type.

Responde una pregunta más interesante: *¿la UPV solo estudia estos límites o también produce investigación orientada a soluciones?*

---

## 12. AED disciplinar o por áreas (si hay metadatos)

Si hay áreas, journals, departamentos o categorías Scopus/OpenAlex:

- qué áreas contribuyen a cada PB
- qué PBs son más multidisciplinares
- qué áreas conectan varios PBs

**Figuras:** Sankey área → PB, heatmap área × PB, red bipartita disciplinas–PBs.

---

## 13. Set mínimo fuerte de figuras

| # | Figura | Para qué |
|---|---|---|
| 1 | Corpus construction flow | Preparación de datos |
| 2 | Temporal evolution of corpus | Producción total por año |
| 3 | PB profile ranking + radial | Perfil global UPV |
| 4 | Heatmap año × PB | Evolución temporal del perfil PB |
| 5 | UMAP semantic map | Estructura semántica de abstracts |
| 6 | PB × PB co-occurrence heatmap | Interacción entre límites |
| 7 | PB network | Estructura sistémica de coocurrencias |
| 8 | Topics → PBs Sankey | Relación temas–PBs |
| 9 | Model comparison / evaluation panel | Rendimiento y acuerdo entre métodos |
| 10 | Contribution type by PB | Si se usa LLM para esto |

---

## 14. Prioridades

### Imprescindible

- trazabilidad del corpus
- evolución temporal
- distribución PB
- multilabelidad
- coocurrencia PB × PB
- evaluación manual
- comparación de métodos
- interpretación de errores

### Muy recomendable

- UMAP semántico
- radial plot tipo paper UPV
- Sankey topics → PBs
- contribution type con LLM
- red PB
- ejemplos representativos

### Opcional si da tiempo

- análisis por área/departamento
- análisis por revista
- clustering temporal
- dashboard interactivo más avanzado

---

## 15. Estructura de la memoria

1. **Corpus overview** — qué datos tenemos y cómo quedan tras limpieza.
2. **Semantic structure of the corpus** — qué temas aparecen y cómo se agrupan los abstracts.
3. **Planetary Boundaries profile** — qué PBs dominan y cuáles son marginales.
4. **Temporal evolution** — cómo cambia el perfil PB.
5. **Systemic interactions** — coocurrencia y red PB.
6. **Model behaviour and validation** — comparación de métodos, evaluación y errores.
7. **Interpretability and contribution analysis** — ejemplos, contribution type y lectura sustantiva.

---

## 16. Lo que NO se debe hacer

- top palabras genéricas sin interpretación
- wordclouds sin contexto
- barplots básicos sin diseño
- UMAP sin etiquetas
- heatmaps sin normalizar
- gráficos que no respondan una pregunta
- muchas figuras mediocres en vez de pocas buenas

---

## 17. Recomendación final

Cinco ideas centrales:

1. **Perfil PB de la UPV** — qué límites aparecen más y menos.
2. **Evolución temporal** — cómo cambia la agenda investigadora.
3. **Estructura semántica** — qué clusters/topics hay en el corpus.
4. **Interacciones PB** — qué límites aparecen conectados.
5. **Validación e interpretabilidad** — qué tan fiable es la clasificación y por qué.

Con eso no parecerá un análisis genérico; parecerá un estudio serio de producción científica y sostenibilidad.

---

# Especificación detallada del Radial Plot

> Si se hace radial bar, **el fondo debe ser un planeta** pero **no muy oscuro, algo claro**.

Un radial plot de los PBs es buena idea y conecta con el estilo visual del paper UPV-ODS y las slides CRUE (que usan radial plots para perfil ODS).

**Pero no un radar básico de Excel.** Un **radial plot tipo "perfil institucional UPV-EARTH"**.

## 1. Figura radial principal — "UPV Planetary Boundaries Profile"

Círculo dividido en **9 sectores**, uno por PB:

1. PB1 — Climate Change
2. PB2 — Ocean Acidification
3. PB3 — Stratospheric Ozone Depletion
4. PB4 — Biogeochemical Flows
5. PB5 — Freshwater Use
6. PB6 — Land-System Change
7. PB7 — Biosphere Integrity
8. PB8 — Novel Entities
9. PB9 — Atmospheric Aerosol Loading

Cada sector con barra radial cuya longitud representa:

- número de publicaciones, o
- porcentaje del corpus PB-related, o
- score normalizado.

**Recomendado:** porcentaje del corpus PB-related (mejor comparabilidad).

## 2. Diseño "paper-like"

- Círculo central con texto:
  - `UPV-EARTH`
  - `N = XX,XXX abstracts`
  - `% PB-related = XX%`
- 9 barras radiales desde el centro.
- Cada PB con etiqueta corta (`PB1`...), nombre abreviado alrededor, valor numérico al final de la barra.
- Anillo exterior con colores por familia.
- **Fondo: planeta en tono claro** (no muy oscuro).

## 3. Paleta por familias PB

**Clima / atmósfera / océano** (PB1, PB2, PB3, PB9) → azules, cian, morados.
**Agua / suelo / biosfera** (PB5, PB6, PB7) → verdes y teal.
**Ciclos químicos / contaminación** (PB4, PB8) → naranja, rojo, coral.

## 4. Versión potente — radial doble capa

- **Anillo interior:** frecuencia total 1990–2024.
- **Anillo exterior:** crecimiento reciente o peso 2020–2024.

Mensaje: "perfil histórico vs perfil emergente".

## 5. Versión comparativa — antes/después de 2015

Dos barras radiales superpuestas:

- **1990–2015**
- **2016–2024**

Punto de corte = Agenda 2030. Mejor barras radiales dobles que líneas superpuestas (más legible).

## 6. Versión "small multiples"

3 radial plots pequeños, misma escala:

- 1990–2005
- 2006–2015
- 2016–2024

Se ve la evolución sin saturar un único gráfico.

## 7. Versión con "PB families"

Radial con 9 PBs + anillo exterior agrupado:

- **Atmosphere & Climate**
- **Land, Water & Biosphere**
- **Chemical & Biogeochemical Pressure**

El anillo exterior es solo guía visual (sin datos). Aspecto editorial.

## 8. Tabla de datos necesaria

| pb_id | pb_name | family | n_papers | pct_papers | n_recent | pct_recent | growth |
|---|---|---|---:|---:|---:|---:|---:|
| PB1 | Climate Change | Atmosphere | 3250 | 28.4 | 1200 | 31.2 | +2.8 |
| PB5 | Freshwater Use | Water/Land | 2100 | 18.3 | 850 | 22.1 | +3.8 |

## 9. Qué NO hacer

- radar clásico con línea conectando puntos si hay mucha diferencia entre PBs (engaña visualmente).

**Mejor:** radial bar chart, circular lollipop chart, radial stacked profile.

## 10. Propuesta final de figura

**Figure X — UPV-EARTH Planetary Boundary Research Profile**

- **Panel A:** radial bar plot perfil total 1990–2024.
- **Panel B:** radial bar plot perfil reciente 2016–2024.
- **Panel C:** mini ranking lateral con los 3 PBs más presentes y los 3 más infrarrepresentados.

**Mensaje:** *La producción científica de la UPV relacionada con Planetary Boundaries muestra una firma temática desigual, con concentración en ciertos límites y menor presencia en otros, permitiendo identificar fortalezas y vacíos de investigación.*

## 11. Título de la figura

- **"Planetary Boundary signature of UPV scientific production"**
- o en español: **"Firma Planetary Boundaries de la producción científica de la UPV"**

El concepto de **firma** convierte el gráfico en una identidad científica de la universidad.
