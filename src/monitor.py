"""Flask monitoring dashboard — real-time proxy metrics on port 8081."""

import threading

from flask import Flask, jsonify, Response

from src.stats import proxy_stats


def create_dashboard(stats=proxy_stats, host="localhost", port=8081):
    """Create and return a Flask app wired to shared stats."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        snapshot = stats.get_snapshot()
        top_domains_rows = "".join(
            f"<tr><td>{d}</td><td>{c}</td></tr>"
            for d, c in snapshot["top_domains"]
        )
        status_rows = "".join(
            f"<tr><td>{s}</td><td>{n}</td></tr>"
            for s, n in snapshot["status_codes"].items()
        )
        client_rows = "".join(
            f"<tr><td>{ip}</td><td>{count}</td></tr>"
            for ip, count in snapshot["clients"].items()
        )
        data_mb = round(snapshot["bytes_transferred"] / (1024 * 1024), 2)
        return f"""<!DOCTYPE html>
<html lang='es'>
<head><meta charset='utf-8'>
<meta http-equiv='refresh' content='5'>
<title>Proxy Monitor</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f6f9; color: #333; padding: 0; }}
  .navbar {{ background: #1a1a2e; color: #fff; padding: 1em 2em; display: flex; justify-content: space-between; align-items: center; }}
  .navbar h1 {{ font-size: 1.3em; font-weight: 600; }}
  .navbar span {{ font-size: 0.85em; opacity: 0.7; }}
  .container {{ max-width: 1000px; margin: 0 auto; padding: 1.5em; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1em; margin-bottom: 1.5em; }}
  .card {{ background: #fff; border-radius: 10px; padding: 1.2em; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .card h3 {{ font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 0.5em; }}
  .card .num {{ font-size: 1.8em; font-weight: 700; }}
  .card .num.allowed {{ color: #16a34a; }}
  .card .num.blocked {{ color: #dc2626; }}
  .card .sub {{ font-size: 0.85em; color: #888; margin-top: 0.2em; }}
  .section {{ background: #fff; border-radius: 10px; padding: 1.2em; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 1.5em; }}
  .section h3 {{ font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 0.8em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 0.5em 0.8em; font-size: 0.85em; color: #888; border-bottom: 2px solid #eee; font-weight: 600; }}
  td {{ padding: 0.5em 0.8em; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #fafafa; }}
  .footer {{ text-align: center; padding: 1.5em; font-size: 0.85em; color: #aaa; }}
  .footer a {{ color: #1a1a2e; text-decoration: none; }}
  .footer a:hover {{ text-decoration: underline; }}
</style></head>
<body>
<div class='navbar'>
<h1>Proxy Monitor</h1>
<span>EIF208 — Redes, UNA</span>
</div>
<div class='container'>
<div class='grid'>
<div class='card'><h3>Solicitudes</h3><div class='num'>{snapshot['total_requests']}</div></div>
<div class='card'><h3>Permitidas</h3><div class='num allowed'>{snapshot['allowed_requests']}</div><div class='sub'>{snapshot['allowed_pct']}% del total</div></div>
<div class='card'><h3>Bloqueadas</h3><div class='num blocked'>{snapshot['blocked_requests']}</div><div class='sub'>{snapshot['blocked_pct']}% del total</div></div>
<div class='card'><h3>Volumen</h3><div class='num'>{data_mb} <span style='font-size:0.5em;'>MB</span></div></div>
<div class='card'><h3>Activas</h3><div class='num'>{snapshot['active_connections']}</div><div class='sub'>conexiones</div></div>
<div class='card'><h3>Cache hits</h3><div class='num'>{snapshot['cache_hits']}</div><div class='sub'>miss: {snapshot['cache_misses']} · rate: {snapshot['hit_rate']}%</div></div>
</div>
<div class='section'>
<h3>Clientes activos</h3>
<table><tr><th>IP</th><th>Solicitudes</th></tr>
{client_rows if client_rows else '<tr><td colspan="2" style="text-align:center;color:#aaa;">Sin datos</td></tr>'}
</table>
</div>
<div class='section'>
<h3>Top 5 dominios</h3>
<table><tr><th>Dominio</th><th>Solicitudes</th></tr>
{top_domains_rows if top_domains_rows else '<tr><td colspan="2" style="text-align:center;color:#aaa;">Sin datos</td></tr>'}
</table>
</div>
<div class='section'>
<h3>Códigos de estado</h3>
<table><tr><th>Código</th><th>Conteo</th></tr>
{status_rows if status_rows else '<tr><td colspan="2" style="text-align:center;color:#aaa;">Sin datos</td></tr>'}
</table>
</div>
<div class='footer'>
Proxy Monitor — <a href='/api/stats'>API JSON</a> | <a href='/api/report'>Exportar CSV</a>
</div>
</div>
</body></html>"""

    @app.route("/api/stats")
    def api_stats():
        return jsonify(stats.get_snapshot())

    @app.route("/api/report")
    def api_report():
        import datetime

        snapshot = stats.get_snapshot()
        total_cache = snapshot["cache_hits"] + snapshot["cache_misses"]
        miss_rate = round(snapshot["cache_misses"] / total_cache * 100, 1) if total_cache > 0 else 0.0
        data_mb = round(snapshot["bytes_transferred"] / (1024 * 1024), 2)

        status_desc = {
            200: "OK", 301: "Moved Permanently", 302: "Found",
            304: "Not Modified", 400: "Bad Request", 401: "Unauthorized",
            403: "Forbidden (Bloqueado)", 404: "Not Found", 500: "Server Error",
            502: "Bad Gateway", 503: "Service Unavailable",
        }

        today = datetime.date.today().isoformat()
        lines = [
            f"=== REPORTE ESTADÍSTICO DEL PROXY (EIF208) ===",
            f"Reporte generado,{today}",
            "",
            f"--- MÉTRICAS GLOBALES DE TRÁFICO ---",
            f"Métrica,Valor,Porcentaje",
            f"Total de Peticiones,{snapshot['total_requests']},100%",
            f"Peticiones Permitidas,{snapshot['allowed_requests']},{snapshot['allowed_pct']}%",
            f"Peticiones Bloqueadas,{snapshot['blocked_requests']},{snapshot['blocked_pct']}%",
            f"Volumen de Datos Transferidos,{data_mb} MB,—",
            f"Conexiones Activas en el Corte,{snapshot['active_connections']},—",
            f"Clientes Únicos Activos,{snapshot['active_clients']},—",
            "",
            f"--- RENDIMIENTO DE LA MEMORIA CACHÉ ---",
            f"Estado,Cantidad,Porcentaje de Éxito",
            f"Cache Hits (Éxitos),{snapshot['cache_hits']},{snapshot['hit_rate']}%",
            f"Cache Misses (Fallos),{snapshot['cache_misses']},{miss_rate}%",
            "",
            f"--- CÓDIGOS DE ESTADO HTTP DETECTADOS ---",
            f"Código HTTP,Descripción,Conteo de Peticiones",
        ]
        for code, count in snapshot["status_codes"].items():
            desc = status_desc.get(code, "Desconocido")
            lines.append(f"{code},{desc},{count}")

        lines += [
            "",
            f"--- TOP 5 DOMINIOS MÁS SOLICITADOS ---",
            f"Posición,Dominio de Red,Total Peticiones",
        ]
        for i, (dom, count) in enumerate(snapshot["top_domains"], start=1):
            lines.append(f"{i},{dom},{count}")

        lines += [
            "",
            f"--- DIRECCIONES IP DE ORIGEN (CLIENTES) ---",
            f"Dirección IP,Peticiones Totales",
        ]
        for ip, count in snapshot["clients"].items():
            lines.append(f"{ip},{count}")

        csv = "\n".join(lines) + "\n"
        return Response(csv, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=proxy-report.csv"})

    return app


def start_dashboard(stats=proxy_stats, host="localhost", port=8081):
    """Start Flask in a daemon thread."""
    app = create_dashboard(stats, host, port)
    thread = threading.Thread(
        target=app.run,
        kwargs={"host": host, "port": port, "debug": False, "use_reloader": False},
        daemon=True,
    )
    thread.start()
    return thread
