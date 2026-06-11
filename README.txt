HTTP Proxy con Filtrado y Monitoreo
====================================
EIF208 - Redes, Universidad Nacional (UNA)
Junio 2026

Servidor proxy HTTP con filtrado de dominios, panel de monitoreo web,
cache de respuestas, y registro de logs. Proyecto de curso para la
carrera de Ingenieria en Sistemas, Universidad Nacional.

====================================
1. REQUISITOS
====================================

- Python 3.13+ (verificar con: python --version)
- Dependencias opcionales: Flask (para dashboard web incluido en flake.nix)
- Entorno Nix: direnv allow (o: nix develop)

====================================
2. INICIO RAPIDO
====================================

  direnv allow
  python src/proxy.py

El proxy inicia en http://localhost:8080
El dashboard de monitoreo inicia en http://localhost:8081

====================================
3. OPCIONES DE LINEA DE COMANDOS
====================================

  --host HOST              Proxy listen host (default: localhost)
  --port PORT              Proxy listen port (default: 8080)
  --dashboard-host HOST    Dashboard listen host (default: localhost)
  --dashboard-port PORT    Dashboard listen port (default: 8081)
  --blocklist PATH         Ruta al archivo de dominios bloqueados
                           (default: config/blocked_domains.txt)
  --log-file PATH          Ruta al archivo de log
                           (default: logs/proxy.log)
  --log-format FORMAT      Formato de log: jsonl o csv (default: jsonl)
  --cache-ttl SECONDS      TTL de cache en segundos (default: 60)
  --cache-max-size NUM     Maximo de entradas en cache (default: 100)

Ejemplos:

  python src/proxy.py --port 9090
  python src/proxy.py --port 9090 --dashboard-port 9092
  python src/proxy.py --port 8080 --blocklist config/mi-lista.txt
  python src/proxy.py --log-file logs/custom.log --log-format csv

====================================
4. CONFIGURACION DEL NAVEGADOR
====================================

Firefox:
  Preferencias -> Red -> Configuracion de conexion -> Proxy manual
  HTTP Proxy: localhost 8080
  Usar tambien para HTTPS: marcado

Chrome:
  Configuracion -> Sistema -> Proxy de red -> Manual
  O desde terminal:
    google-chrome --proxy-server="localhost:8080"

====================================
5. ESTRUCTURA DEL PROYECTO
====================================

  src/proxy.py           Servidor proxy (entry point con CLI args)
  src/config.py          Constantes de configuracion
  src/handler.py         Manejador de requests HTTP
  src/http_relay.py      Reenvio de requests HTTP
  src/connect_tunnel.py  Tunel CONNECT para HTTPS
  src/filter.py          Bloqueo de dominios (HTTP + SNI)
  src/logger.py          Logging en formato JSONL/CSV
  src/stats.py           Metricas en memoria (thread-safe)
  src/monitor.py         Dashboard web Flask
  src/cache.py           Cache HTTP en memoria con TTL + FIFO
  config/blocked_domains.txt  Lista de dominios bloqueados
  logs/proxy.log         Archivo de log
  .planning/             Artefactos de planificacion GSD

====================================
6. ESCENARIOS DE DEMO
====================================

6.1 Proxy HTTP basico

  curl -x http://localhost:8080 http://example.com

  Debe responder con el contenido HTML de example.com.

6.2 Proxy HTTPS (tunel CONNECT)

  curl -x http://localhost:8080 https://google.com

  Debe responder con el HTML de Google (el contenido exacto
  depende de si Google redirige a HTTPS directo).

6.3 Bloqueo de dominios (HTTP)

  curl -x http://localhost:8080 http://facebook.com

  Debe mostrar pagina 403 Forbidden con el mensaje de bloqueo.

6.4 Bloqueo de dominios (HTTPS via SNI)

  curl -v -x http://localhost:8080 https://twitter.com 2>&1 | head -20

  Debe fallar con conexion cerrada (el proxy bloquea antes de
  establecer el tunel CONNECT).

6.5 Modificar lista de bloqueo (hot-reload)

  echo "example.com" >> config/blocked_domains.txt
  curl -x http://localhost:8080 http://example.com

  Ahora debe mostrar 403. No es necesario reiniciar el proxy.
  La lista se recarga automaticamente cada 2 segundos.

6.6 Dashboard de monitoreo

  Abrir http://localhost:8081 en el navegador.

  Muestra: total de requests, bloqueados vs permitidos,
  conexiones activas, top 5 dominios, codigos de estado,
  hits/miss de cache.

  Endpoint JSON: http://localhost:8081/api/stats

  Endpoint CSV: http://localhost:8081/api/report
  Descarga un reporte CSV con metricas, dominios principales,
  clientes activos, y codigos de estado.

6.7 Cache HTTP

  Primera visita (se reenvia al servidor destino):
    time curl -x http://localhost:8080 http://example.com -o /dev/null -s

  Segunda visita (sirve desde cache, mas rapido):
    time curl -x http://localhost:8080 http://example.com -o /dev/null -s

  La segunda visita debe ser notablemente mas rapida (ms vs ms).

6.8 Logs

  cat logs/proxy.log | python -m json.tool

  Muestra entradas JSONL con timestamp, metodo, host,
  status, duracion, bloqueado, cache_hit.

  Formato CSV (si se usa --log-format csv):

  timestamp,method,host,path,status,duration,blocked,cache_hit

  La primera linea es el encabezado con los nombres de las
  columnas. Cada linea representa una solicitud. Usar:

    column -t -s',' logs/proxy.log

  para visualizar en terminal, o abrir directamente en hoja
  de calculo.

6.9 Flags personalizados

  Terminal 1:
    python src/proxy.py --port 9090 --dashboard-port 9092

  Terminal 2:
    curl -x http://localhost:9090 http://example.com
    curl http://localhost:9092/api/stats

  El proxy funciona en :9090 y el dashboard en :9092.

6.10 Hot-reload de lista de bloqueo

  Terminal 1: python src/proxy.py

  Terminal 2: tail -f logs/proxy.log

  Terminal 3:
    echo "blocked-site.com" >> config/blocked_domains.txt
    curl -x http://localhost:8080 http://blocked-site.com

  El bloqueo se activa sin reiniciar el proxy. El log
  muestra la entrada con "blocked": true.


