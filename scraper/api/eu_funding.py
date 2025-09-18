import logging
from typing import List, Dict
import datetime
import json
import re

class EUFundingScraper:
    def __init__(self, session, config, logger):
        self.session = session
        self.config = config
        self.logger = logger
        self.api_search_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        self.api_key = "SEDIA"
        
    def search(self, sector: str, location: str, company_type: str) -> List[Dict]:
        """Busca subvenciones en EU Funding & Tenders Portal usando la API pública."""
        grants = []
        
        if location not in ['UE', 'Todas', 'Internacional']:
            return grants
            
        self.logger.info("Realizando búsqueda en la API de la UE...")

        # Mapeo de sectores y tipos a palabras clave
        sector_keywords = {
            'Tecnología': 'Digital, IT, Innovation',
            'Energía': 'Energy, Climate, Green Deal',
            'Industria': 'Industry, Manufacturing, SME',
            'Agricultura': 'Agriculture, Bioeconomy',
            'Salud': 'Health, Research, Medical',
            'Todos': ''
        }
        
        company_type_keywords = {
            'PYME': 'SME',
            'Startup': 'Startup, Innovation',
            'Autónomo': 'SME',
            'Microempresa': 'SME',
            'Grande empresa': 'Industry, Research',
            'ONG': 'NGO, Non-profit',
            'Universidad': 'University, Higher Education',
            'Centro de investigación': 'Research Center, R&I',
            'Todos': ''
        }
        
        search_terms = f"{sector_keywords.get(sector, '')} {company_type_keywords.get(company_type, '')}".strip()
        
        # Construcción del payload de la solicitud POST
        search_payload = {
            "query": {
                "bool": {
                    "must": [
                        { "terms": { "type": ["1","2","8"] } },
                        { "terms": { "status": ["31094501", "31094502"] } }
                    ]
                }
            },
            "languages": ["es"],
            "sort": {
                "field": "startDate",
                "order": "DESC"
            },
            "pageNumber": "1",
            "pageSize": "20"
        }
        
        if search_terms:
            params = {"apiKey": self.api_key, "text": search_terms}
        else:
            params = {"apiKey": self.api_key, "text": "*"}

        try:
            api_url = f"{self.api_search_url}"
            
            response = self.session.post(
                api_url,
                json=search_payload,
                params=params,
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                data = response.json()
                # Se ha corregido la lógica para obtener los resultados.
                # Ahora se espera una lista en la clave 'results' y se itera sobre sus elementos.
                results = data.get('results', [])
                self.logger.info(f"Se encontraron {len(results)} resultados de la API de la UE.")
                
                for item in results:
                    public_data = item.get('publicData', {}) # Acceder al diccionario anidado de forma segura
                    grant = {
                        'title': public_data.get('title', {}).get('es', 'Sin título'),
                        'description': public_data.get('objective', {}).get('es', 'Sin descripción'),
                        'sector': sector,
                        'location': 'Unión Europea',
                        'region': 'Todas',
                        'company_type': company_type,
                        'amount': public_data.get('totalBudget', 'Consultar convocatoria'),
                        'deadline': public_data.get('deadlineDate', 'Sin fecha límite'),
                        'publication_date': public_data.get('publicationDate', 'Sin fecha de publicación'),
                        'source': 'Comisión Europea - Funding & Tenders Portal',
                        'link': public_data.get('link', self.config['base_url']),
                        'relevance_score': 4
                    }
                    grants.append(grant)
            else:
                self.logger.error(f"Error al consultar la API de la UE. Código de estado: {response.status_code} - Respuesta: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Error en la búsqueda de la API de la UE: {e}")
        
        return grants

    def _generate_future_deadline(self, days: int) -> str:
        """Genera una fecha límite futura."""
        future_date = datetime.datetime.now() + datetime.timedelta(days=days)
        return future_date.strftime("%Y-%m-%d")