from flask import Flask
import datetime
import os
import logging
from werkzeug.exceptions import RequestEntityTooLarge

# Importar los Blueprints de las rutas
from routes.main import main_bp
from routes.api import api_bp

# Importar las utilidades de ayuda
from utils.web_helpers import register_template_filters

# Configurar el logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Inicializar la aplicación Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['DEBUG'] = os.environ.get('FLASK_ENV', '') == 'development'

# Registrar los Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Registrar los filtros de plantilla
register_template_filters(app)

# ------------------------
# Handlers de errores
# ------------------------
@app.errorhandler(404)
def not_found_error(error):
    return "Página no encontrada", 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Error interno: {error}")
    return "Error interno del servidor", 500

@app.errorhandler(503)
def service_unavailable(error):
    return "Servicio no disponible", 503

@app.errorhandler(RequestEntityTooLarge)
def too_large(e):
    return "Archivo demasiado grande", 413

@app.errorhandler(429)
def ratelimit_handler(e):
    return "Demasiadas solicitudes", 429


# ------------------------
# Contexto global para templates
# ------------------------
@app.context_processor
def inject_global_vars():
    return {'current_year': datetime.datetime.now().year, 'app_version': '2.0.1', 'last_updated': datetime.datetime.now().strftime('%Y-%m-%d')}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config['DEBUG'])