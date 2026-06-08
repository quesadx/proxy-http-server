HTTP Proxy con Filtrado y Monitoreo
EIF208 - Redes, Universidad Nacional (UNA)
Junio 2026

=== Entorno de Desarrollo ===

1. Activar entorno:
   direnv allow
   (o: nix develop)

2. Ejecutar proxy:
   python src/proxy.py

=== Configuracion del Navegador ===

Firefox: Preferences -> Network -> Manual proxy -> HTTP: localhost 8080

=== Estructura del Proyecto ===

src/          Codigo fuente Python
config/       Archivos de configuracion
logs/         Archivos de log generados
