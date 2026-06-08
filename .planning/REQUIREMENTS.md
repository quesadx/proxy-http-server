# Project Requirements

## REQ-00: Bootstrap del entorno
Environment listo para desarrollo — nix flake con Python 3, direnv, estructura de directorios, .gitignore.
- `direnv allow` activa el entorno Nix con Python 3 disponible
- `python --version` funciona dentro del shell
- Estructura de directorios creada (src/, config/, logs/)
- Commit inicial con todos los archivos de bootstrap

## REQ-01: Núcleo del Proxy HTTP
Proxy HTTP funcional — servidor TCP concurrente que parsea requests HTTP, reenvía, y soporta CONNECT para HTTPS.
- `http://example.com` carga a través del proxy en `localhost:8080`
- `https://google.com` funciona (túnel CONNECT transparente)
- Múltiples conexiones concurrentes manejadas correctamente
- Métodos GET y POST reenviados correctamente

## REQ-02: Módulo de Filtrado
Bloqueo de dominios en HTTP (por Host header) y HTTPS (por SNI) con hot-reload de lista.
- `http://facebook.com` muestra página de bloqueo 403
- `https://twitter.com` no carga (bloqueado por SNI)
- Bloqueo funciona sin reiniciar proxy al modificar blocklist
- Dominios no bloqueados pasan sin interferencia

## REQ-03: Logging y Panel de Monitoreo
Registro CSV/JSONL de cada solicitud y panel Flask con métricas en tiempo real en puerto 8081.
- Cada request queda registrado en `logs/proxy.log`
- Panel en `http://localhost:8081` muestra stats actualizadas
- Top 5 dominios, requests bloqueadas vs permitidas, clientes activos visibles
- Panel corre en hilo daemon sin bloquear proxy

## REQ-04: Caché HTTP
Caché en memoria (dict) con TTL configurable, eviction FIFO, integración con logger/dashboard.
- Segunda visita a HTTP cacheable llega más rápido
- Solo GET 200 son cacheados
- TTL expira y entrada se sirve fresca después
- Dashboard muestra cache hits/misses

## REQ-05: Integración, Hardening y README
Todo integrado, robusto, con CLI args, manejo de errores, y documentación para demo oral.
- `python src/proxy.py --port 8080 --dashboard-port 8081` funciona
- Destino que no responde no crashea el proxy
- Conexiones cerradas abruptamente manejadas sin error
- README.txt completo con instrucciones de demo
