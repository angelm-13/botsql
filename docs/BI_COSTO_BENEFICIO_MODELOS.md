# BI texto-a-SQL: costo/beneficio de modelos de IA

Fecha de consulta de todas las fuentes: **2026-10-15**. Los precios cambian; revisar la fuente antes de presupuestar.

Convención de verificación usada en este documento:
- **[V]** verificado en la página oficial o en el repositorio durante esta consulta.
- **[T]** tomado de un agregador/terceros, sin confirmar en la página oficial.
- **[E]** estimación propia o regla empírica; no es un dato verificado.
- **[NV]** no se pudo verificar.

## 1. Punto de partida (lo que hay hoy)

- Modelo actual: Ollama local, `qwen2.5-coder:3b` (el default en `backend/app/bi/config.py` es `:7b`). El propio comentario del código dice que con `:7b` en CPU pura una pregunta tarda **60-100 s** (hasta 166 s dentro de Docker con carga) y por eso `timeout_llm=270` [medición del equipo, en el repo].
- Clúster k3s de 3 nodos con 3.8 GB RAM, sin GPU (CLAUDE.md). Un modelo 7B cuantizado a 4 bits ocupa del orden de 4.5 GB solo en pesos [E]; **no cabe** en un nodo de 3.8 GB junto con el resto de pods. Un 3B (~2 GB [E]) cabe, justo, y compite con la app.
- Carga de referencia pedida: ~4,000 tokens de entrada y ~500 de salida por consulta. 500 consultas/mes = 2.0 M tokens de entrada + 0.25 M de salida. 5,000 consultas/mes = 20 M + 2.5 M.
- Aviso: modelos con "razonamiento" pueden generar muchos más tokens de salida que 500; los costos de API de abajo son un piso para esos modelos. Con prompt caching (el DDL del esquema es un prefijo estable) la entrada puede costar ~10 % [V para Anthropic: cache hit = 0.1x], lo que no se aplicó en las tablas.

## 2. APIs administradas: precio por token y costo mensual

Costo mensual = (entrada x precio_in) + (salida x precio_out), sin caché ni batch.

### 2.1 Anthropic (Claude) [V]
Fuente: https://platform.claude.com/docs/en/about-claude/pricing (consultada 2026-10-15). Precios por millón de tokens (MTok).

| Modelo | Entrada / Salida | 500 consultas/mes | 5,000 consultas/mes |
|---|---|---|---|
| Haiku 5.5 (prompts hasta 100K) | $0.10 / $0.50 | ~$0.33 | ~$3.25 |
| Haiku 4.5 | $1 / $5 | ~$3.25 | ~$32.50 |
| Sonnet 5.5 | $2 / $10 | ~$6.50 | ~$65 |
| Opus 5.5 | $4 / $20 | ~$13 | ~$130 |
| Fable 5.1 | $10 / $50 | ~$32.50 | ~$325 |

La página oficial también lista descuentos de caché (lectura = 0.1x de la entrada). Un resultado de búsqueda de terceros mostraba precios distintos (Haiku $1/$5, Sonnet $3/$15, Opus $5/$25): corresponden a la generación anterior (4.x); la tabla oficial de arriba es la vigente.

### 2.2 Google Gemini [V]
Fuente: https://ai.google.dev/gemini-api/docs/pricing (2026-10-15), nivel de pago estándar.

| Modelo | Entrada / Salida | 500/mes | 5,000/mes |
|---|---|---|---|
| 2.5 Flash-Lite | $0.10 / $0.40 | ~$0.30 | ~$3 |
| 2.5 Flash | $0.30 / $2.50 | ~$1.23 | ~$12.25 |
| 3.6 Flash (promo hasta 31-dic-2026; después $1.50/$7.50) | $0.75 / $3.75 | ~$2.44 | ~$24.40 |
| 3.1 Pro Preview (<=200K) | $2 / $12 | ~$7 | ~$70 |

### 2.3 OpenAI [T]
No se pudo abrir la página oficial (HTTP 403). Cifras de agregadores (morphllm.com, cloudzero.com, g2.com), fechadas entre junio y septiembre de 2026; **tratar como no verificadas**.

| Modelo | Entrada / Salida | 500/mes | 5,000/mes |
|---|---|---|---|
| GPT-5.4 nano | $0.20 / $1.25 | ~$0.71 | ~$7.10 |
| GPT-5.4 mini | $0.75 / $4.50 | ~$2.63 | ~$26 |
| GPT-5.4 | $2.50 / $15 | ~$8.75 | ~$87.50 |
| GPT-5.5 | $5 / $30 | ~$17.50 | ~$175 |

Conclusión de costo: a este volumen el costo de API es **de centavos a decenas de dólares al mes** en los modelos pequeños/medios; incluso Opus/GPT-5.5 a 5,000 consultas cuesta menos que un solo servidor con GPU encendido 24x7.

## 3. Modelos abiertos autoalojados

Calidad: para ningún modelo abierto se pudo verificar un número BIRD/Spider propio en esta consulta (el reporte técnico de Qwen2.5-Coder, arXiv:2409.12186, dice evaluar Spider y BIRD en su sección 7.4, pero ni el abstract ni el blog oficial dan los números que se pudieron leer: **[NV]**). Lo único cuantitativo verificado de modelos abiertos es de Defog (SQLCoder), con su **propio** benchmark SQL-Eval sobre PostgreSQL, autoreportado: SQLCoder-70B 93.0 %, SQLCoder-7B-2 90.5 %, GPT-4 82.0 % en esquemas no vistos (n=200) (fuente: model card/README de defog en Hugging Face/GitHub, vía búsqueda 2026-10-15). Es autoreportado y de 2024: no sirve para comparar con modelos actuales.

Contexto verificado de referencia (no son estos modelos): el leaderboard de BIRD tiene arriba sistemas multi-paso en ~80-82 % de execution accuracy, y humanos ~92.96 % (reportes de prensa/terceros; oficial: https://bird-bench.github.io [no abierto directamente]). Eso indica que incluso lo mejor falla ~1 de cada 5 consultas en bases reales; un esquema de 150 tablas en inglés con preguntas en español es más difícil que el benchmark típico [E].

Memoria/VRAM (regla empírica Q4 ≈ 0.55-0.6 GB por mil millones de parámetros + KV cache para 4K+ de contexto) [E]; licencias de la columna "Licencia" son de memoria del autor, **[NV]** en esta sesión, confirmar antes de usar comercialmente.

| Modelo | Memoria Q4 aprox. [E] | CPU (sin GPU) | GPU (L4 24 GB o similar) | Calidad text-to-SQL esperada [E, no verificada] | Licencia [NV] |
|---|---|---|---|---|---|
| qwen2.5-coder 3B | ~2-2.5 GB | cabe en un nodo; lento (decenas de s) | segundos | baja: falla joins en esquemas de 150 tablas | Qwen Research (restrictiva) |
| qwen2.5-coder 7B | ~4.5-5 GB | **60-100 s medido por el equipo**; no cabe en 3.8 GB | 2-6 s | media | Apache 2.0 |
| qwen2.5-coder 14B | ~9-10 GB | >3 min, inviable | 5-10 s | media-alta | Apache 2.0 |
| qwen2.5-coder 32B | ~19-20 GB | inviable | cabe en L4 24 GB Q4 (justo); 10-20 s | alta entre abiertos | Apache 2.0 |
| SQLCoder 7B-2 / 70B (defog) | ~4.5 GB / ~40 GB | 7B como Qwen 7B | 70B requiere >=2 GPU grandes | buena en su benchmark propio, esquemas antiguos | CC BY-SA 4.0 (pesos; fine-tune obliga a compartir) |
| Llama 3.x (8B / 70B) | ~5 GB / ~40 GB | 8B lento | 8B ok | media (8B), alta (70B) | Llama Community |
| DeepSeek-Coder-V2-Lite (16B MoE) / DeepSeek-V3 (671B MoE) | ~10 GB / cientos de GB | inviable | V3 exige multi-GPU: fuera de alcance | V3 alta pero no autoalojable aquí | licencia propia DeepSeek |
| Mistral / Codestral (22B) | ~13 GB | inviable | ok en L4 | media-alta | Codestral: licencia no comercial/propia |
| Phi (3.5/4, 3.8-14B) | 2.5-9 GB | Phi mini cabe | rápido | media-baja en SQL, bueno por tamaño | MIT |
| Gemma 2/3 (2-27B) | 1.5-17 GB | pequeñas cabe | rápido | media | Términos de Gemma |

Costo de infraestructura autoalojada:

| Escenario | Costo mensual | Estado |
|---|---|---|
| VPS actual sin GPU (3x 3.8 GB) | $0 adicional | Solo 3B viable; 7B no cabe. Latencia >60 s. Calidad insuficiente para producción [E]. |
| AWS g6.xlarge (1x L4 24 GB, 4 vCPU, 16 GB) 24x7, on-demand $0.805/h | ~$588 | [V] https://instances.vantage.sh/aws/ec2/g6.xlarge |
| Mismo, spot $0.616/h | ~$450 (puede interrumpirse) | [V] |
| Mismo, reservado 1 año $0.524/h / 3 años $0.369/h | ~$383 / ~$269 | [V] |
| Mismo, solo horario laboral (~176 h/mes) on-demand | ~$142 | [E] sobre precio [V]; requiere arranque/parada y arranque en frío del modelo |
| Hetzner GPU dedicado | GEX45 €0.3429/h, GEX63 €1.6009/h (neto); GEX131 con cifras contradictorias (€889 a €1,197/mes) | [T], artículo del 13-oct-2026; los modelos de GPU cambiaron en otoño de 2026. [NV] especificaciones/VRAM y precio actual: confirmar en hetzner.com |

Un GPU dedicado 24x7 solo se amortiza frente a API si el volumen o la regla de privacidad lo exigen: a 5,000 consultas/mes, $588/mes de L4 equivale a ~9 veces el costo mensual de Sonnet 5.5 en API (~$65/mes) [E].

## 4. Privacidad, residencia y despliegue en k8s

| Opción | Privacidad / residencia | Despliegue en k8s | Riesgo operativo |
|---|---|---|---|
| Abiertos autoalojados (Ollama/vLLM) | Máxima: el esquema y las filas nunca salen de la infraestructura propia | Fácil con Ollama (un Deployment), pero requiere nodo con GPU (taint/nodeSelector, device plugin de NVIDIA) y volumen para pesos; el clúster actual no tiene GPU | Operar GPU, actualizar modelos, disponibilidad propia |
| APIs administradas (Claude, OpenAI, Gemini) | El **esquema (DDL) y los resultados que se re-envíen** salen a un tercero; hay que revisar términos de retención/entrenamiento y DPA del proveedor [NV: no revisados aquí]; residencia de datos no necesariamente en México | Trivial: solo un cliente HTTP y un Secret con la API key; sin GPU | Dependencia de proveedor, cambios de precio/modelo, latencia de red, cuotas |
| Nube de hiperescaladores con modelo alojado (Bedrock, Vertex, Azure) | Datos dentro del contrato/región de tu cuenta cloud; suele dar mejores garantías contractuales | Cliente HTTP + IAM | Costo y configuración de IAM |

Nota importante sobre qué se envía: el módulo manda al modelo el **DDL** (nombres de tablas/columnas) y la pregunta, no las filas, siempre que `con_muestras=False` (default) [V, config.py]. Los valores de datos solo salen si se activa `BI_SAMPLE_VALUES` o si se re-envían resultados al modelo para resumir. Eso reduce mucho la exposición de datos sensibles de facturación/nómina a una API externa, aunque el esquema por sí mismo ya es información del cliente.

## 5. Recomendación por escenario

| Escenario | Recomendación | Por qué | Costo orden de magnitud |
|---|---|---|---|
| **Piloto** (<=500 consultas/mes, datos de demo/dev) | API de modelo pequeño: Claude Haiku 5.5 o Gemini 2.5/3.x Flash; probar también Sonnet 5.5 como techo de calidad | Cero infraestructura, mucho mejor calidad que un 3B/7B, latencia de segundos en vez de 60-100 s, <$7/mes | <$10/mes |
| **Producción chica** (~5,000/mes, clientes reales sin datos regulados) | API de modelo medio (Sonnet 5.5 o Gemini 3.1 Pro/Flash) con prompt caching del esquema, tope de gasto, y `schema_linking` ya existente para recortar tokens | La API cuesta una fracción de una GPU dedicada; calidad superior | ~$10-70/mes |
| **Producción con datos sensibles** (nómina/facturación, clientes que exigen que el dato no salga) | Opción A: modelo abierto de 14B-32B (qwen2.5-coder 32B Q4) en una instancia con GPU de 24 GB (~$270-590/mes) en tu propio VPC/nodo dedicado. Opción B: API vía hiperescalador con contrato/DPA y región elegida, enviando solo DDL (sin muestras), con rol de BD de solo lectura | A: el dato no sale; B: costo bajo con garantías contractuales. La decisión depende de la política de cada cliente y de la revisión legal (LFPDPPP) | A: $270-590/mes; B: <$70/mes |

Regla práctica: abstraer el proveedor (ya existe `llm_provider.py` con `ProveedorLLM`; hoy solo `ProveedorOllama` está cableado en `app/__init__.py`) y ofrecer **por cliente** un interruptor entre "local" y "API", de modo que los clientes sensibles no dependan de enviar su esquema fuera.

## 6. Qué no se pudo verificar

- Números BIRD/Spider propios de Qwen2.5-Coder 3B/7B/14B/32B, Llama, DeepSeek, Mistral, Phi, Gemma: el reporte técnico (arXiv:2409.12186) menciona la evaluación pero los números no se pudieron extraer; no se citan.
- Precios oficiales de OpenAI (403); sus cifras son de agregadores.
- Precio y especificaciones vigentes de GPU de Hetzner; precios de L4/T4/A10G en otros proveedores distintos de AWS.
- Licencias exactas por modelo (columna marcada [NV]) y términos de retención de datos de cada proveedor de API.
- Latencias en GPU y con API son estimaciones (no medidas en este sistema); solo la de 7B en CPU está medida por el equipo.
- Requisitos de memoria son reglas empíricas, no medición.
