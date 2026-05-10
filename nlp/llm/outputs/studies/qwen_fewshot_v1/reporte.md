# Reporte de Evaluación: Qwen 2.5 (14B) Few-Shot vs Validación Humana

## Resumen Ejecutivo
- **Documentos analizados**: 150
- **Exact Match (Perfecto)**: 49.3%
- **Top-1 Accuracy**: 57.3%
- **Hit@K (Acierto Flexible)**: 50.5%
- **True Negative**: 82.4%
- **Jaccard Similarity Promedio**: 0.407
- **Hamming Loss Promedio**: 0.067
- **Rigorousness**: 82.4%
- **Positivity Bias**: 17.6%

## Reporte de Clasificación Detallado
```
              precision    recall  f1-score   support

        None       0.51      0.82      0.63        51
         PB1       0.55      0.50      0.52        24
         PB2       0.70      0.88      0.78         8
         PB3       0.67      0.25      0.36         8
         PB4       0.60      0.30      0.40        10
         PB5       1.00      0.25      0.40         4
         PB6       0.50      0.50      0.50         4
         PB7       0.00      0.00      0.00        13
         PB8       1.00      0.14      0.25         7
         PB9       0.80      0.76      0.78        21

    accuracy                           0.57       150
   macro avg       0.63      0.44      0.46       150
weighted avg       0.57      0.57      0.53       150

```

## Análisis de Errores
- Total errores: 64
### Top 5 Confusiones:
- PB1 → None: 10 veces
- PB7 → None: 8 veces
- PB8 → None: 6 veces
- PB4 → None: 5 veces
- PB3 → None: 4 veces

## Estadísticas Descriptivas
- Promedio PBs asignados por humano: 0.87
- Promedio PBs asignados por Qwen Few-Shot: 0.60
- Máximo PBs humano: 2
- Máximo PBs Qwen Few-Shot: 3
- Documentos sin PB humano: 51
- Documentos sin PB Qwen Few-Shot: 83

## Interpretación Exhaustiva de Métricas
Este apartado explica en detalle qué mide cada métrica y qué implica su valor actual en el contexto de una evaluación multi-etiqueta jerárquica.

### 1. Exact Match (Perfecto)
- Mide el caso más estricto: la etiqueta primaria debe ser correcta y las etiquetas secundarias deben coincidir exactamente.
- Valor actual: 49.3%. Esto sugiere que más de la mitad de los documentos tienen una correspondencia completa entre humano y Qwen Few-Shot.
- Interpretación: es una métrica dura; una buena puntuación aquí indica coherencia tanto en el driver principal como en la jerarquía secundaria.

### 2. Top-1 Accuracy (Precisión Principal)
- Evalúa si Qwen Few-Shot identifica correctamente el PB primario humano, independientemente de los secundarios.
- Valor actual: 57.3%.
- Interpretación: una tasa de {(top1/len(df_eval))*100:.1f}% indica que Qwen Few-Shot acierta el tema principal en casi dos tercios de los casos, pero todavía hay margen de mejora.

### 3. Hit@K (Acierto Flexible)
- Comprueba si el PB primario humano aparece en la lista completa de PBs predichos por Qwen Few-Shot.
- Valor actual: 50.5%.
- Interpretación: es una métrica relevante para modelos multi-etiqueta porque permite reconocer el concepto aunque no sea la primera etiqueta. Un valor más bajo que el Top-1 indica que cuando falla el primario, tampoco suele recuperar el PB dentro de los secundarios.

### 4. True Negative (Rechazo Correcto)
- Calcula los casos en los que el humano y el modelo coinciden en 'None'.
- Valor actual: 82.4%.
- Interpretación: un {true_negative_pct:.1f}% es un buen indicador de que Qwen Few-Shot no sufre un ruido excesivo de positivismo en los ejemplos sin PB.

### 5. Jaccard Similarity
- Mide el solapamiento entre las listas de PBs humano y modelo en cada documento.
- Valor actual: 0.407.
- Interpretación: {avg_jaccard:.3f} indica un solapamiento moderado. Hay un número relevante de casos en los que las listas comparten al menos una etiqueta, pero no coinciden completamente.

### 6. Hamming Loss
- Mide la fracción de etiquetas PB mal clasificadas en el conjunto de 9 posibles.
- Valor actual: 0.067.
- Interpretación: {avg_hamming:.3f} es una cifra baja, lo que sugiere que el modelo no comete errores masivos en la mayoría de las etiquetas. Sin embargo, la métrica no distingue entre falsos positivos y falsos negativos.

### 7. Rigorousness (Tasa de Filtrado)
- Mide qué porcentaje de documentos sin PB humano fueron correctamente rechazados por Qwen Few-Shot.
- Valor actual: 82.4%.
- Interpretación: una tasa alta como {rigorousness:.1f}% indica que el modelo es bastante conservador frente a documentos sin PB, lo cual es positivo para evitar ruido.

### 8. Positivity Bias (Alucinación Verde)
- Indica qué porcentaje de documentos 'None' humanos recibió al menos un PB predicho por Qwen Few-Shot.
- Valor actual: 17.6%.
- Interpretación: el {positivity_bias:.1f}% revela un sesgo de positivismo presente, pero no excesivo. El objetivo de la evaluación debe ser reducir esta cifra sin sacrificar demasiada precisión primaria.

## Análisis Detallado de Gráficas
Este bloque resume el propósito y la interpretación de cada visualización, de modo que el tribunal pueda extraer conclusiones claras.

### 1. Matriz de Confusión Normalizada
- Muestra la distribución de aciertos y fallos de la etiqueta primaria en proporciones por clase.
- Si la diagonal es clara, el modelo distingue bien cada PB.
- Si aparecen valores altos fuera de la diagonal, especialmente hacia 'None', significa que el modelo tiende a sub-detectar esa PB.

### 2. Distribución de Overassignment (Violin Plot)
- Compara la distribución del número de PBs asignados por humano y por Qwen Few-Shot.
- Un violín más estrecho en Qwen Few-Shot sugiere que el modelo es más conservador.
- Los cuartiles ayudan a ver si hay documentos extremos con muchas etiquetas.

### 3. Accuracy por Planetary Boundary
- Refuerza dónde el modelo rinde mejor y peor en la etiqueta primaria.
- Las líneas de referencia permiten comparar cada PB con el accuracy global y con un baseline sencillo.
- Un PB con recall muy bajo es una línea roja de alerta para iterar el prompt o ajustar ejemplos de entrenamiento.

### 4. Sesgo de Positividad
- Muestra los PBs que el modelo inventa cuando el humano dice 'None'.
- Estos casos son críticos para entender el falso efecto 'el LLM siempre quiere asignar algo'.

### 5. Distribución de Predicciones de Qwen Few-Shot
- Permite ver qué PBs predice con más frecuencia.
- Un sesgo fuerte hacia ciertos PBs puede indicar un desequilibrio semántico o una respuesta habitual del prompt.

### 6. Comparación de Longitud de Listas Secundarias
- Un boxplot que compara cuántos secundarios asigna el humano frente al modelo.
- Si Qwen Few-Shot asigna menos secundarios y aún mantiene buen Top-1, su comportamiento es conservador pero más preciso.

### 7. Matrices One-vs-Rest por PB
- Cada mini-matriz 2x2 resume TP, FP, FN y TN para esa PB en particular.
- Útil para detectar rápidamente qué PBs se confunden más con el resto.

### 8. Co-occurrence Heatmap
- Visualiza qué PBs tiende a agrupar el modelo dentro de la misma predicción.
- Si aparecen co-ocurrencias fuertes entre PBs no esperadas, puede haber solapamiento semántico o mala separación de temas.

### 9. Sankey Diagram
- Representa el flujo de errores desde las etiquetas humanas a las predicciones.
- Las conexiones más gruesas muestran las rutas de confusión más frecuentes, lo que es especialmente útil para demostrar visualmente dónde se fuga el modelo.

### 10. Violin Plot de Confianza
- Si la columna de confianza está disponible, muestra cómo se distribuye la confianza del modelo en aciertos y fallos.
- Si se simula, sirve como placeholder instructivo: un verdadero análisis de calibración requiere confianza real.

## Razonamiento Inferido del LLM
A partir de estas métricas y visualizaciones, proponemos un diagnóstico de la estrategia interna del modelo:
- El modelo parece ser relativamente conservador: la baja Hamming Loss y la alta Rigorousness indican que evita asignar demasiadas PBs, pero el Positivity Bias del 17.6% muestra que aún produce falsos positivos en algunos documentos 'None'.
- El hecho de que el True Negative sea alto (82.4%) y el Top-1 no supere el 70% sugiere un equilibrio entre precaución y falta de confianza. El modelo sabe cuándo no asignar nada, pero a veces pierde el PB primario correcto.
- La Jaccard media de 0.407 indica que cuando el modelo no acierta exactamente, todavía captura parte del conjunto de PBs correcto. Esto es consistente con un razonamiento que identifica el dominio general del texto pero falla en ordenar o jerarquizar algunos PBs secundarios.
- Los errores hacia 'None' en las primeras confusiones (PB1 → None, PB7 → None, PB9 → None) revelan que el modelo en ocasiones subestima la presencia de un PB relevante. Eso puede deberse a un prompt que penaliza demasiado la sobre-asignación o a una interpretación demasiado literal de 'sin PB'.

## Hallazgos Clave y Recomendaciones
1. El prompt debe reforzar más claramente la distinción entre PBs primarios y secundarios para mejorar el Top-1 sin reducir la precisión general.
2. Hay margen para afinar la respuesta 'None': el modelo ya es bastante bueno rechazando casos sin PB, pero debe reducir el {positivity_bias:.1f}% de alucinación verde.
3. Revisar los PBs con peor recall (especialmente PB7 y PB1) en ejemplos concretos puede ayudar a ajustar ejemplos de few-shot o prompts de contexto.
4. Si es posible, incorporar una salida explícita de confianza real permitirá hacer un análisis de calibración más sólido en futuras iteraciones.

## Gráficos Generados
1. [Matriz de Confusión Normalizada](1_matriz_confusion_qwen_fewshot.png)
2. [Análisis de Overassignment (Violin Plot)](2_overassignment_qwen_fewshot.png)
3. [Tasa de Acierto por Planetary Boundary](3_accuracy_por_pb_qwen_fewshot.png)
4. [Sesgo de Positividad](4_sesgo_positividad_qwen_fewshot.png)
5. [Distribución de Predicciones de Qwen Few-Shot](5_distribucion_predicciones_qwen_fewshot.png)
6. [Comparación de Listas Secundarias](6_comparacion_listas_secundarias.png)
7. [Matrices One-vs-Rest por PB](7_ovr_matrices.png)
8. [Co-occurrence Heatmap](8_cooccurrence_heatmap.png)
9. [Sankey Diagram: Flujo de Errores](9_sankey_diagram.png)
10. [Violin Plot de Confianza](10_confianza_violin.png)

---
*Generado automáticamente el 2026-05-05 20:15:45*
