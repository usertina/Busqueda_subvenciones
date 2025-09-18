import datetime
import logging
import io
import json
import os
from flask import Blueprint, request, jsonify, send_file
from services.grants import process_grants_data
from scraper.api_client import RealGrantAPI  # <-- Línea corregida

# Detectar disponibilidad de pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

api_bp = Blueprint('api', __name__)
grant_api = RealGrantAPI()

@api_bp.route("/search", methods=["GET"])
def api_search():
    """API endpoint para búsquedas directas."""
    start_time = datetime.datetime.now()
    try:
        sector = request.args.get("sector", "Todos")
        location = request.args.get("location", "Todas") 
        company_type = request.args.get("company_type", "Todos")
        region = request.args.get("region", "Todas")
        
        raw_grants = grant_api.search_grants(sector, location, company_type, region)
        grants, _ = process_grants_data(raw_grants, start_time)
        
        return jsonify({
            "success": True,
            "results": len(grants),
            "grants": grants,
            "search_criteria": {
                "sector": sector, "location": location, "region": region, "company_type": company_type
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error en API search: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.datetime.now().isoformat()}), 500

@api_bp.route("/export/<format>", methods=["POST"])
def export_results(format):
    """Endpoint para exportar resultados."""
    try:
        sector = request.form.get("sector", "Todos")
        location = request.form.get("location", "Todas")
        company_type = request.form.get("company_type", "Todos")
        region = request.form.get("region", "Todas")
        
        raw_grants = grant_api.search_grants(sector, location, company_type, region)
        grants, _ = process_grants_data(raw_grants)
        
        df_data = [{
            'Título': g.get('title'), 'Descripción': g.get('description'), 'Sector': g.get('sector'),
            'Ubicación': g.get('location'), 'Región': g.get('region'), 'Tipo Empresa': g.get('company_type'),
            'Importe': g.get('amount'), 'Fecha Límite': g.get('deadline'), 'Fecha Publicación': g.get('publication_date'),
            'Días Restantes': g.get('days_remaining'), 'Fuente': g.get('source'), 'Enlace': g.get('link')
        } for g in grants]
        
        if format.lower() == 'json':
            output = io.StringIO()
            json.dump({"grants": df_data}, output, indent=2, ensure_ascii=False)
            output.seek(0)
            return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='application/json', as_attachment=True, download_name=f'subvenciones.json')
            
        elif format.lower() == 'csv' and PANDAS_AVAILABLE:
            df = pd.DataFrame(df_data)
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'subvenciones.csv')
            
        elif format.lower() == 'excel' and PANDAS_AVAILABLE:
            df = pd.DataFrame(df_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Subvenciones', index=False)
            output.seek(0)
            return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'subvenciones.xlsx')
        
        else:
            return jsonify({"error": "Formato no soportado o pandas no disponible"}), 400
            
    except Exception as e:
        logging.error(f"Error en exportación: {e}")
        return jsonify({"error": str(e)}), 500