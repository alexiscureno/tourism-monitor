# Feature Specification: Tourism Monitor Cozumel — Cruise Monitor MVP

**Feature Branch**: `001-cruise-monitor-mvp`
**Created**: 2026-04-17
**Status**: Draft

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ver la actividad de cruceros de hoy (Priority: P1)

Un visitante llega al dashboard y ve de un vistazo cuántos cruceros están en Cozumel hoy, en qué terminales, cuántos pasajeros desembarcaron y el status de cada barco (arribado, programado, cancelado).

**Why this priority**: Es el "headline" del monitor. Si no funciona esto, el proyecto no tiene razón de ser.

**Independent Test**: Abrir el dashboard muestra correctamente los cruceros del día actual con su terminal, hora de llegada/salida, status y pasajeros. Entrega valor inmediato sin necesitar el análisis histórico.

**Acceptance Scenarios**:

1. **Given** el usuario abre el dashboard, **When** carga la vista principal, **Then** ve los cruceros programados y/o arribados para la fecha actual con terminal, ETA, ETD, status y pasajeros.
2. **Given** hay un crucero cancelado hoy, **When** el usuario ve la lista, **Then** el barco cancelado aparece claramente diferenciado con 0 pasajeros.
3. **Given** no hay cruceros hoy, **When** el usuario ve la vista, **Then** el dashboard indica explícitamente "sin cruceros hoy".

---

### User Story 2 — Explorar el histórico con filtros (Priority: P2)

Un analista o visitante quiere explorar la actividad histórica de cruceros en Cozumel filtrando por año, mes, naviera o terminal para identificar patrones.

**Why this priority**: Es la funcionalidad que demuestra el pipeline de data science y la riqueza del dataset histórico (2015–hoy).

**Independent Test**: El usuario puede seleccionar un año y mes específico y el dashboard actualiza todas las visualizaciones y métricas para reflejar ese período.

**Acceptance Scenarios**:

1. **Given** el usuario selecciona año 2019 y mes Diciembre, **When** aplica el filtro, **Then** todas las gráficas y métricas muestran solo datos de ese período.
2. **Given** el usuario filtra por naviera "Carnival", **When** aplica el filtro, **Then** solo aparecen barcos operados por Carnival Corporation.
3. **Given** el usuario filtra por terminal "SSA Mexico", **When** aplica el filtro, **Then** solo aparecen visitas a esa terminal.
4. **Given** el usuario combina filtros (año + naviera), **When** aplica ambos, **Then** el dashboard muestra la intersección de ambos criterios.

---

### User Story 3 — Ver tendencias estacionales y métricas clave (Priority: P2)

Un visitante quiere entender los patrones estacionales: cuáles son los meses de mayor afluencia, qué navieras dominan el puerto, y cómo ha evolucionado el número de pasajeros a lo largo de los años.

**Why this priority**: Es el núcleo del valor analítico. Demuestra habilidades de análisis de series de tiempo.

**Independent Test**: Sin filtros aplicados, el dashboard muestra gráficas de tendencia anual y estacionalidad mensual con el dataset completo.

**Acceptance Scenarios**:

1. **Given** el usuario accede a la sección de análisis histórico, **When** ve la vista sin filtros, **Then** aparece una gráfica de pasajeros totales por mes/año que revela la estacionalidad (alta temporada octubre–abril, baja mayo–septiembre).
2. **Given** el usuario ve el análisis por navieras, **When** observa la distribución, **Then** puede identificar qué navieras tienen mayor participación en el puerto.
3. **Given** hay eventos anómalos en el historial (pandemia 2020, huracanes), **When** el usuario ve la serie de tiempo completa, **Then** las anomalías son visualmente evidentes y están anotadas.

---

### User Story 4 — Ver el load factor de los barcos (Priority: P3)

Un visitante quiere saber qué tan llenos llegan los cruceros a Cozumel — el porcentaje de ocupación real vs. la capacidad en double occupancy del barco.

**Why this priority**: Añade profundidad analítica al dataset básico al cruzarlo con la capacidad de cada barco.

**Independent Test**: Para cualquier barco con datos en el histórico, el dashboard puede calcular y mostrar su load factor promedio (pasajeros reportados / capacidad double occupancy × 100).

**Acceptance Scenarios**:

1. **Given** el usuario ve el detalle de un barco específico, **When** el barco tiene capacidad registrada, **Then** se muestra el load factor calculado (ej. "87% de ocupación").
2. **Given** el usuario ve el análisis por naviera, **When** observa las métricas, **Then** puede comparar el load factor promedio entre navieras.
3. **Given** un barco no tiene capacidad registrada, **When** el sistema intenta calcular el load factor, **Then** muestra "capacidad no disponible" en lugar de un error.

---

### User Story 5 — Ver el pronóstico de actividad futura (Priority: P3)

Un visitante quiere ver una proyección de la actividad de cruceros para las próximas semanas/meses basada en el histórico y la programación conocida de APIQROO.

**Why this priority**: Demuestra capacidades de forecasting en el portfolio. Combina datos históricos con programación oficial.

**Independent Test**: La sección de forecasting muestra una proyección de pasajeros esperados para los próximos 30 días, independiente del análisis histórico.

**Acceptance Scenarios**:

1. **Given** el usuario accede a la sección de pronóstico, **When** ve la vista, **Then** aparece una gráfica con los cruceros ya programados en APIQROO para las próximas semanas.
2. **Given** el modelo tiene suficiente historial, **When** genera una proyección mensual, **Then** el pronóstico incluye intervalos de confianza y se compara con el mismo período del año anterior.

---

### User Story 6 — Ver el mapa de terminales activas hoy (Priority: P3)

Un visitante quiere ver un mapa visual de Cozumel con las 4 terminales marcadas, indicando cuáles tienen barcos hoy y cuáles están vacías.

**Why this priority**: Elemento visual de alto impacto para el portfolio.

**Independent Test**: El mapa muestra Cozumel con las 4 terminales diferenciadas por actividad del día actual.

**Acceptance Scenarios**:

1. **Given** hay barcos en 3 de 4 terminales hoy, **When** el usuario ve el mapa, **Then** las 3 terminales activas tienen un indicador visual diferente a la terminal vacía.
2. **Given** el usuario interactúa con una terminal activa en el mapa, **When** hace hover o clic, **Then** ve el nombre del barco, naviera y número de pasajeros del día.

---

### User Story 7 — Globo interactivo de rutas de origen (Priority: P3)

Un visitante ve un globo 3D oscuro y rotante que muestra arcos animados desde los puertos de origen de los cruceros hacia Cozumel, con el grosor de cada arco proporcional al número de visitas históricas desde ese puerto.

**Why this priority**: Elemento visual de alto impacto para el portfolio. Comunica de forma inmediata la conectividad global de Cozumel como destino de cruceros.

**Independent Test**: El globo muestra al menos los 8 puertos de origen principales con arcos correctamente proporcionales al volumen histórico de visitas. Funciona de forma independiente al resto del dashboard.

**Acceptance Scenarios**:

1. **Given** el usuario accede a la vista del globo, **When** carga la visualización, **Then** aparece un globo oscuro rotante con arcos animados desde los puertos de origen hacia Cozumel.
2. **Given** el usuario ve el globo, **When** observa los arcos, **Then** los arcos más gruesos/brillantes corresponden a los puertos con mayor volumen de cruceros (ej. Miami, Fort Lauderdale).
3. **Given** el usuario hace hover sobre un arco o punto de origen, **When** interactúa con el globo, **Then** ve el nombre del puerto, naviera principal que opera desde ahí y número total de visitas históricas.
4. **Given** el usuario aplica un filtro de naviera en el dashboard, **When** el filtro está activo, **Then** el globo actualiza los arcos mostrando solo las rutas de esa naviera.

---

### Edge Cases

- ¿Qué pasa si APIQROO no está disponible al intentar actualizar datos?
- ¿Cómo se maneja un barco que aparece duplicado en el mismo día?
- ¿Qué pasa con cruceros que tienen 0 pasajeros y status "Arribado" (dato pendiente de carga semanal de APIQROO)?
- ¿Cómo se comporta el forecasting durante temporada de huracanes con cancelaciones masivas?
- ¿Qué pasa si un nombre de barco en APIQROO no tiene coincidencia en la tabla maestra de capacidades?
- ¿Cómo se trata el período COVID (marzo 2020 – marzo 2021) en modelos de estacionalidad?

---

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline de datos:**

- **FR-001**: El sistema DEBE recolectar y almacenar el histórico completo de cruceros de APIQROO (octubre 2015 – presente) con los campos: fecha, terminal, bandera/país, nombre del barco, hora arribo (ETA), hora zarpe (ETD), status y pasajeros.
- **FR-002**: El sistema DEBE actualizar diariamente los datos de programación de APIQROO para reflejar cambios de status del día actual (programado → arribado / cancelado).
- **FR-003**: El sistema DEBE actualizar semanalmente (lunes o martes) los datos del histórico de APIQROO para incorporar los pasajeros reportados de la semana anterior.
- **FR-004**: El sistema DEBE mantener una tabla maestra de barcos con: nombre del barco, naviera operadora, capacidad double occupancy, capacidad máxima, año de construcción y tonelaje bruto (gross tonnage).
- **FR-005**: El sistema DEBE recolectar datos climáticos históricos y pronóstico para Cozumel (temperatura, precipitación, velocidad del viento) alineados a las fechas del historial de cruceros.
- **FR-006**: El sistema DEBE marcar como "pendiente de actualización" los registros con pasajeros = 0 y status = "Arribado" para excluirlos del cálculo de load factor hasta que se actualicen.

**Análisis:**

- **FR-007**: El sistema DEBE calcular el load factor por visita como: (pasajeros_reportados / capacidad_double_occupancy) × 100, solo cuando ambos valores estén disponibles.
- **FR-008**: El sistema DEBE identificar y etiquetar anomalías históricas conocidas: cierre COVID (marzo 2020 – marzo 2021) y períodos con cancelaciones masivas por fenómenos meteorológicos.
- **FR-009**: El sistema DEBE calcular métricas agregadas por período seleccionado: total de visitas, total de pasajeros, promedio de pasajeros por visita, tasa de cancelación, distribución por naviera y por terminal.
- **FR-010**: El sistema DEBE generar un pronóstico de pasajeros para los próximos 30 días combinando la programación conocida de APIQROO con patrones históricos estacionales.

**Dashboard:**

- **FR-011**: El dashboard DEBE ofrecer filtros interactivos por: año, mes, naviera, terminal y status. Todos los filtros se combinan y actualizan las visualizaciones automáticamente.
- **FR-012**: El dashboard DEBE mostrar como vista principal un resumen del día actual: barcos en puerto, total de pasajeros hoy, terminales activas.
- **FR-013**: El dashboard DEBE mostrar un mapa geográfico de las 4 terminales de Cozumel con indicadores visuales de actividad basados en los datos del día actual.
- **FR-014**: El dashboard DEBE mostrar series de tiempo de pasajeros mensuales/anuales con anotaciones en eventos anómalos.
- **FR-015**: El dashboard DEBE mostrar la distribución de mercado por naviera (participación en número de visitas y en total de pasajeros).
- **FR-016**: El dashboard DEBE ser accesible públicamente desde `monitor.axologic.com` con disponibilidad continua.
- **FR-017**: Los datos del dashboard DEBEN actualizarse automáticamente sin intervención manual del usuario.
- **FR-018**: El sistema DEBE mantener una tabla de puertos de origen con: nombre del puerto, ciudad, país y coordenadas geográficas, mapeada a los barcos que operan desde ese puerto.
- **FR-019**: El dashboard DEBE mostrar un globo 3D interactivo con arcos animados desde los puertos de origen hacia Cozumel, donde el grosor del arco es proporcional al volumen histórico de visitas desde ese puerto.

### Key Entities

- **Visita de crucero**: Registro único de un barco en una terminal en una fecha. Atributos: fecha, terminal, nombre del barco, bandera, hora arribo, hora zarpe, status, pasajeros reportados.
- **Barco (tabla maestra)**: Perfil estático de un barco de crucero. Atributos: nombre, naviera operadora, capacidad double occupancy, capacidad máxima, año de construcción, tonelaje bruto.
- **Terminal**: Punto de atraque en Cozumel. Valores fijos: Terminal SSA México, Terminal Puerta Maya, Terminal Punta Langosta, Fondeo Cozumel.
- **Naviera**: Empresa operadora de cruceros (ej. Carnival Corporation, Royal Caribbean Group, MSC Cruises, Norwegian Cruise Line Holdings, Princess Cruises).
- **Dato climático**: Registro diario de condiciones meteorológicas en Cozumel asociado a una fecha de visita.
- **Puerto de origen**: Puerto desde donde zarpa un crucero antes de llegar a Cozumel. Atributos: nombre, ciudad, país, coordenadas geográficas. Se mapea a los barcos que operan habitualmente desde ese puerto.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El historial de datos cubre sin interrupciones desde octubre 2015 hasta la semana anterior a la fecha actual.
- **SC-002**: Los datos de programación del día actual están disponibles en el dashboard antes de las 9:00 AM cada día.
- **SC-003**: Los datos de pasajeros de la semana anterior están disponibles los martes antes del mediodía.
- **SC-004**: El dashboard carga completamente en menos de 5 segundos en una conexión estándar.
- **SC-005**: El dashboard está disponible públicamente en `monitor.axologic.com` con uptime ≥ 95%.
- **SC-006**: El load factor puede calcularse para ≥ 90% de las visitas históricas (≥ 90% de los barcos únicos tienen capacidad en la tabla maestra).
- **SC-007**: El modelo de forecasting produce predicciones mensuales con error promedio (MAE) menor al 15% en períodos de validación histórica, excluyendo anomalías COVID/huracanes.
- **SC-008**: Todos los filtros interactivos del dashboard responden en menos de 2 segundos al cambiar la selección.
- **SC-009**: El proyecto está documentado y publicado en GitHub como repositorio público para uso en portfolio.

---

## Assumptions

- Los datos de APIQROO son la fuente oficial y autoritativa para el historial de cruceros en Cozumel.
- APIQROO publica los pasajeros con rezago de ~1 semana; los registros de la semana en curso muestran 0 hasta que se actualicen.
- La capacidad "double occupancy" es el denominador correcto para el load factor, siguiendo la convención estándar de la industria de cruceros.
- Los cruceros con status "Cancelado" se excluyen del cálculo de métricas de afluencia (pasajeros = 0 es correcto para cancelados).
- El período marzo 2020 – marzo 2021 se trata como anomalía COVID y se excluye o anota en los modelos de forecasting y estacionalidad.
- Los cruceristas en Cozumel son visitantes del día (no huéspedes de hotel), por lo que los datos de cruceros y ocupación hotelera son mercados independientes y no se correlacionan en este MVP.
- El mapa de terminales usa coordenadas geográficas fijas (las terminales son infraestructura permanente).
- La tabla maestra de barcos se construye una sola vez y se enriquece incrementalmente cuando aparecen nuevos barcos en el historial de APIQROO.
- El sistema corre en hardware propiedad del usuario con acceso a internet estable y exposición pública mediante túnel seguro.
- El scope es exclusivamente el Puerto de Cozumel. Otros puertos de Quintana Roo (Mahahual, Costa Maya) quedan fuera del MVP.
- Los datos de vuelos quedan fuera del MVP; se considerarán en una fase posterior al expandir a Quintana Roo completo.
