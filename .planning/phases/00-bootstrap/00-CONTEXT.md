# Phase 0: Bootstrap del entorno — Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Crear repositorio con estructura inicial: flake.nix para entorno Nix con Python 3, .envrc para direnv, .gitignore, directorios src/ config/ logs/ con archivos placeholder. Commit inicial. No incluye lógica de proxy ni código funcional.

</domain>

<decisions>
## Implementation Decisions

### Nix flake config
- Usar nixpkgs unstable como input
- devShell con python3 + python3Packages.requests + python3Packages.flask
- Herramientas adicionales: git, curl, wireshark (opcional)
- Shell hook: imprimir "HTTP Proxy Dev Environment ready"

### Environment management
- .envrc con `use flake` para activación automática con direnv
- No usar poetry/pipenv — Nix flake es el único gestor de entorno

### Directory structure
- src/ para código fuente Python
- config/ para archivos de configuración (blocked_domains.txt)
- logs/ para archivos de log con .gitkeep

### Gitignore
- logs/*.log, __pycache__/, *.pyc, .direnv/, result
- NO ignorar .envrc (debe trackearse en git)
- NO ignorar flake.lock (debe trackearse para reproducibilidad)

### the agent's Discretion
- Orden exacto de commits (1 o múltiples)
- Formato de README.txt
- Contenido exacto de los placeholders src/*.py

</decisions>

<canonical_refs>
## Canonical References

### Nix flake
- No external specs — requirements captured in ROADMAP.md and user context

</canonical_refs>

<specifics>
## Specific Ideas

- Proyecto debe funcionar en NixOS con direnv
- Shell hook descriptivo para confirmar entorno activo
- flake.lock debe trackearse (reproducibilidad)

</specifics>

<deferred>
## Deferred Ideas

- Configuración de linting/formateo — no necesaria para entorno base
- CI/CD — fuera de alcance

</deferred>

---

*Phase: 00-bootstrap*
*Context gathered: 2026-06-08*
