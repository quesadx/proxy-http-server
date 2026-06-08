# Roadmap: HTTP Proxy con Filtrado y Monitoreo

## Overview

Construir desde cero un servidor proxy HTTP funcional con filtrado de dominios (HTTP y HTTPS vía SNI), sistema de logs, panel web de monitoreo en tiempo real, y caché de respuestas como funcionalidad adicional. Proyecto para EIF208 - Redes, Universidad Nacional (UNA). Lenguaje: Python 3, entorno NixOS con direnv + nix flake.

**Fecha límite:** 9 u 11 de junio de 2026

## Phases

- [x] **Phase 0: Bootstrap del entorno** - Crear repositorio, flake.nix, .envrc, .gitignore, estructura de directorios
- [ ] **Phase 1: Núcleo del Proxy HTTP** - Proxy funcional que intercepta, reenvía y maneja concurrencia (35%)
- [ ] **Phase 2: Módulo de Filtrado** - Bloqueo de dominios en HTTP y HTTPS vía SNI (25%)
- [ ] **Phase 3: Logging y Panel de Monitoreo** - Registro auditable y panel web con métricas en tiempo real (20%)
- [ ] **Phase 4: Caché HTTP** - Caché en memoria de respuestas HTTP para reducir latencia (10%)
- [ ] **Phase 5: Integración, Hardening y README** - Integración final, robustez y documentación para demo (10%)

## Phase Details

### Phase 0: Bootstrap del entorno
**Goal**: Environment listo para desarrollo — nix flake con Python 3, direnv, estructura de directorios, .gitignore
**Depends on**: Nothing (initial setup)
**Requirements**: [REQ-00]
**Success Criteria** (what must be TRUE):
  1. `direnv allow` activa el entorno Nix con Python 3 disponible
  2. `python --version` funciona dentro del shell
  3. Estructura de directorios creada (src/, config/, logs/)
  4. Commit inicial con todos los archivos de bootstrap
**Plans**: 1 plan

Plans:
- [x] 00-01: Bootstrap nix flake dev environment

### Phase 1: Núcleo del Proxy HTTP
**Goal**: Proxy HTTP funcional — servidor TCP concurrente que parsea requests HTTP, reenvía, y soporta CONNECT para HTTPS
**Depends on**: Phase 0
**Requirements**: [REQ-01]
**Success Criteria** (what must be TRUE):
  1. `http://example.com` carga a través del proxy en `localhost:8080`
  2. `https://google.com` funciona (túnel CONNECT transparente)
  3. Múltiples conexiones concurrentes manejadas correctamente
  4. Métodos GET y POST reenviados correctamente
**Plans**: 3 plans

Plans:
- [x] 01-01: TCP server with concurrent connection handling
- [x] 01-02: HTTP request parsing and forwarding
- [x] 01-03: HTTPS CONNECT tunnel support

### Phase 2: Módulo de Filtrado
**Goal**: Bloqueo de dominios en HTTP (por Host header) y HTTPS (por SNI) con hot-reload de lista
**Depends on**: Phase 1
**Requirements**: [REQ-02]
**Success Criteria** (what must be TRUE):
  1. `http://facebook.com` muestra página de bloqueo 403
  2. `https://twitter.com` no carga (bloqueado por SNI)
  3. Bloqueo funciona sin reiniciar proxy al modificar blocklist
  4. Dominios no bloqueados pasan sin interferencia
**Plans**: 3 plans

Plans:
- [ ] 02-01: Domain blocklist loader with hot-reload
- [ ] 02-02: HTTP domain and keyword filtering
- [ ] 02-03: HTTPS SNI extraction and filtering

### Phase 3: Logging y Panel de Monitoreo
**Goal**: Log CSV/JSONL de cada solicitud y panel Flask con métricas en tiempo real en puerto 8081
**Depends on**: Phase 1, Phase 2
**Requirements**: [REQ-03]
**Success Criteria** (what must be TRUE):
  1. Cada request queda registrado en `logs/proxy.log`
  2. Panel en `http://localhost:8081` muestra stats actualizadas
  3. Top 5 dominios, requests bloqueadas vs permitidas, clientes activos visibles
  4. Panel corre en hilo daemon sin bloquear proxy
**Plans**: 3 plans

Plans:
- [ ] 03-01: Thread-safe request logger to file
- [ ] 03-02: Flask monitoring dashboard on port 8081
- [ ] 03-03: Real-time metrics from in-memory stats

### Phase 4: Caché HTTP
**Goal**: Caché en memoria (dict) con TTL configurable, eviction FIFO, integración con logger/dashboard
**Depends on**: Phase 3
**Requirements**: [REQ-04]
**Success Criteria** (what must be TRUE):
  1. Segunda visita a HTTP cacheable llega más rápido
  2. Solo GET 200 son cacheados
  3. TTL expira y entrada se sirve fresca después
  4. Dashboard muestra cache hits/misses
**Plans**: 2 plans

Plans:
- [ ] 04-01: In-memory HTTP response cache with TTL
- [ ] 04-02: Cache hit/miss tracking in logger and dashboard

### Phase 5: Integración, Hardening y README
**Goal**: Todo integrado, robusto, con CLI args, manejo de errores, y documentación para demo oral
**Depends on**: Phase 4
**Requirements**: [REQ-05]
**Success Criteria** (what must be TRUE):
  1. `python src/proxy.py --port 8080 --dashboard-port 8081` funciona
  2. Destino que no responde no crashea el proxy
  3. Conexiones cerradas abruptamente manejadas sin error
  4. README.txt completo con instrucciones de demo
**Plans**: 4 plans

Plans:
- [ ] 05-01: CLI arguments for port configuration
- [ ] 05-02: Connection error handling and timeouts
- [ ] 05-03: README.txt with demo instructions
- [ ] 05-04: Final integration and cleanup

## Progress

**Execution Order:** 0 → 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Bootstrap del entorno | 1/1 | Complete | 2026-06-08 |
| 1. Núcleo del Proxy HTTP | 3/3 | Complete | 2026-06-08 |
| 2. Módulo de Filtrado | 0/3 | Not started | - |
| 3. Logging y Panel de Monitoreo | 0/3 | Not started | - |
| 4. Caché HTTP | 0/2 | Not started | - |
| 5. Integración, Hardening y README | 0/4 | Not started | - |
