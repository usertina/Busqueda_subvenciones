import requests
import datetime
import time
import logging
from typing import List, Dict, Optional
import json
import re
from urllib.parse import urljoin, quote

# Importar los submódulos de fuentes de búsqueda
from scraper.api import boe, eu_funding
from scraper.web import cdti, idae

class RealGrantAPI:
    """Clase que gestiona la búsqueda de subvenciones usando APIs oficiales reales."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SubvencionesFinder/2.0 (https://subvencionesfinder.com)',
            'Accept': 'application/json, text/xml, text/html',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        })
        
        # APIs oficiales CORREGIDAS
        self.apis = {
            'boe': {'sumarios_url': 'https://www.boe.es/datosabiertos/api/sumario', 'timeout': 15},
            'eu_funding': {'base_url': 'https://ec.europa.eu', 'timeout': 20},
            'cdti_web': {'ayudas_url': 'https://www.cdti.es/index.asp?MP=4&MS=0&MN=1', 'timeout': 15},
            'idae_web': {'ayudas_url': 'https://www.idae.es/ayudas-y-financiacion', 'timeout': 15}
        }
        
        # Mapeo de comunidades autónomas
        self.spanish_regions = {
            'Andalucía': ['andalucia', 'sevilla', 'córdoba', 'granada', 'málaga', 'cádiz', 'huelva', 'jaén', 'almería'],
            'Cataluña': ['cataluña', 'catalunya', 'barcelona', 'girona', 'lleida', 'tarragona'],
            'Madrid': ['madrid', 'comunidad de madrid'],
            'Valencia': ['valencia', 'castellón', 'alicante', 'comunidad valenciana'],
            'Galicia': ['galicia', 'coruña', 'lugo', 'ourense', 'pontevedra'],
            'País Vasco': ['país vasco', 'euskadi', 'bilbao', 'vitoria', 'san sebastián'],
            'Aragón': ['aragón', 'zaragoza', 'huesca', 'teruel'],
            'Asturias': ['asturias', 'oviedo'],
            'Cantabria': ['cantabria', 'santander'],
            'Castilla-La Mancha': ['castilla la mancha', 'toledo', 'ciudad real', 'albacete', 'cuenca', 'guadalajara'],
            'Castilla y León': ['castilla y león', 'valladolid', 'salamanca', 'león', 'burgos', 'zamora', 'palencia', 'ávila', 'segovia', 'soria'],
            'Extremadura': ['extremadura', 'badajoz', 'cáceres'],
            'Islas Baleares': ['baleares', 'mallorca', 'menorca', 'ibiza', 'formentera'],
            'Canarias': ['canarias', 'las palmas', 'santa cruz de tenerife', 'tenerife', 'gran canaria'],
            'La Rioja': ['la rioja', 'logroño'],
            'Murcia': ['murcia', 'región de murcia', 'cartagena'],
            'Navarra': ['navarra', 'pamplona'],
            'Ceuta': ['ceuta'],
            'Melilla': ['melilla']
        }
        
        # Cache con TTL
        self.cache = {}
        self.cache_timeout = 1800  # 30 minutos
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def search_grants(self, sector: str, location: str, company_type: str, region: str = "Todas") -> List[Dict]:
        """Busca subvenciones reales usando múltiples APIs oficiales."""
        
        cache_key = f"{sector}_{location}_{company_type}_{region}"
        current_time = time.time()
        
        # Verificar cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if current_time - timestamp < self.cache_timeout:
                self.logger.info(f"Devolviendo {len(cached_data)} resultados desde cache")
                return cached_data
        
        all_grants = []
        
        try:
            # 1. Buscar en BOE
            self.logger.info("Consultando API del BOE...")
            boe_api = boe.BoeScraper(self.session, self.apis['boe'], self.spanish_regions, self.logger)
            all_grants.extend(boe_api.search(sector, location, company_type, region))
            
            # 2. Buscar en EU Funding & Tenders Portal
            self.logger.info("Consultando EU Funding & Tenders Portal...")
            eu_api = eu_funding.EUFundingScraper(self.session, self.apis['eu_funding'], self.logger)
            all_grants.extend(eu_api.search(sector, location, company_type))
            
            # 3. Scraping CDTI
            self.logger.info("Consultando web del CDTI...")
            cdti_web = cdti.CdtisScraper(self.session, self.apis['cdti_web'], self.spanish_regions, self.logger)
            all_grants.extend(cdti_web.search(sector, company_type, region))
            
            # 4. Scraping IDAE
            self.logger.info("Consultando web del IDAE...")
            idae_web = idae.IdaeScraper(self.session, self.apis['idae_web'], self.spanish_regions, self.logger)
            all_grants.extend(idae_web.search(sector, company_type, region))
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de APIs: {e}")
            all_grants = self._get_fallback_data()
        
        # Filtrar, deduplicar y ordenar por fecha de publicación (más recientes primero)
        filtered_grants = self._process_results(all_grants, sector, location, company_type, region)
        
        # Guardar en cache
        self.cache[cache_key] = (filtered_grants, current_time)
        
        self.logger.info(f"Devolviendo {len(filtered_grants)} subvenciones encontradas")
        return filtered_grants
    
    def _process_results(self, grants: List[Dict], sector: str, location: str, company_type: str, region: str) -> List[Dict]:
        """Procesa y ordena resultados por fecha de publicación (más recientes primero)."""
        
        # Deduplicar por un ID único para evitar perder resultados con títulos similares
        unique_grants = []
        seen_ids = set()
        
        for grant in grants:
            # Creamos un identificador único combinando la fuente y un ID interno
            source = grant.get('source', 'NO_SOURCE')
            identifier = grant.get('identifier', 'NO_ID')
            
            if identifier == 'NO_ID' or len(identifier) <= 3:
                # Si no hay ID válido, usamos el título normalizado
                title_normalized = re.sub(r'\W+', '', grant.get('title', 'NO_TITLE').lower())
                unique_id = f"{source}_{title_normalized}"
            else:
                unique_id = f"{source}_{identifier}"
            
            if unique_id not in seen_ids:
                seen_ids.add(unique_id)
                unique_grants.append(grant)
        
        # Ordenar por fecha de publicación (más recientes primero)
        def get_publication_date(grant):
            try:
                pub_date = grant.get('publication_date', '1900-01-01')
                return datetime.datetime.strptime(pub_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                return datetime.datetime(1900, 1, 1)
        
        unique_grants.sort(key=get_publication_date, reverse=True)
        
        # Limitar resultados
        return unique_grants[:25]
    
    def _get_fallback_data(self) -> List[Dict]:
        """Datos de respaldo si todas las APIs fallan."""
        self.logger.warning("No se encontraron datos en las APIs, devolviendo lista vacía.")
        return []
    
    def get_grant_details(self, grant_url: str) -> Optional[Dict]:
        """Obtiene detalles adicionales de una subvención."""
        try:
            response = self.session.get(grant_url, timeout=10)
            if response.status_code == 200:
                return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles: {e}")
        
        return None