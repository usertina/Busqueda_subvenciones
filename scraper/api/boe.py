import datetime
import time
import logging
import json
from typing import List, Dict, Optional
import re

class BoeScraper:
    def __init__(self, session, config, spanish_regions, logger):
        self.session = session
        self.config = config
        self.spanish_regions = spanish_regions
        self.logger = logger
        
    def search(self, sector: str, location: str, company_type: str, region: str) -> List[Dict]:
        """Busca en la API oficial del BOE."""
        grants = []
        try:
            end_date = datetime.datetime.now()
            for i in range(15):
                search_date = (end_date - datetime.timedelta(days=i)).strftime('%Y%m%d')
                try:
                    sumario_url = f"{self.config['sumarios_url']}/{search_date}"
                    response = self.session.get(sumario_url, timeout=self.config['timeout'])
                    
                    if response.status_code == 200:
                        data = self._safe_json_parse(response.text)
                        if data and 'sumario' in data:
                            sumario = data['sumario']
                            if 'secciones' in sumario:
                                for seccion in sumario['secciones']:
                                    if 'secciones' in seccion:
                                        for subseccion in seccion['secciones']:
                                            grants.extend(self._process_boe_subsection(
                                                subseccion, sector, location, company_type, region, search_date
                                            ))
                    time.sleep(0.3)
                except Exception as e:
                    self.logger.warning(f"Error procesando fecha {search_date}: {e}")
                    continue
        except Exception as e:
            self.logger.warning(f"Error general en BOE API: {e}")
        return grants[:10]

    def _process_boe_subsection(self, subseccion: Dict, sector: str, location: str, company_type: str, region: str, fecha: str) -> List[Dict]:
        """Procesa subsecciones del sumario BOE."""
        grants = []
        try:
            if 'items' in subseccion:
                for item in subseccion['items']:
                    title = item.get('titulo', '')
                    relevance_keywords = ['subvención', 'ayuda', 'convocatoria', 'financiación', 'programa', 'incentivo', 'apoyo', 'fomento']
                    
                    if any(keyword in title.lower() for keyword in relevance_keywords):
                        if self._is_relevant_for_sector(title, sector) and self._is_relevant_for_location(title, location, region):
                            grant = {
                                'title': title[:150],
                                'description': f"Convocatoria oficial publicada en BOE.",
                                'sector': sector,
                                'location': self._extract_location_from_title(title, location),
                                'region': self._extract_region_from_title(title, region),
                                'company_type': company_type,
                                'amount': self._extract_amount_from_text(title),
                                'deadline': self._generate_future_deadline(45),
                                'publication_date': self._format_boe_date(fecha),
                                'source': 'BOE - Boletín Oficial del Estado',
                                'link': item.get('url', f"https://www.boe.es/boe/dias/{fecha}/"),
                                'relevance_score': self._calculate_relevance_score(title, sector)
                            }
                            grants.append(grant)
        except Exception as e:
            self.logger.warning(f"Error procesando subsección BOE: {e}")
        return grants

    def _is_relevant_for_location(self, title: str, location: str, region: str = "Todas") -> bool:
        title_lower = title.lower()
        if location == "Todas":
            return True
        elif location == "España":
            eu_keywords = ['unión europea', 'ue ', 'europa ', 'european']
            if any(keyword in title_lower for keyword in eu_keywords):
                return False
            if region != "Todas" and region in self.spanish_regions:
                region_keywords = self.spanish_regions[region]
                return any(keyword in title_lower for keyword in region_keywords)
            return True
        elif location == "UE":
            eu_keywords = ['unión europea', 'ue ', 'europa', 'european', 'horizon']
            return any(keyword in title_lower for keyword in eu_keywords)
        elif location in self.spanish_regions:
            region_keywords = self.spanish_regions[location]
            return any(keyword in title_lower for keyword in region_keywords)
        return True

    def _is_relevant_for_sector(self, title: str, sector: str) -> bool:
        if sector == "Todos":
            return True
        
        title_lower = title.lower()

        sector_keywords = {'Tecnología': ['tecnología', 'tecnológico', 'digital', 'innovación', 'i+d+i', 'startup', 'tic'],
            'Energía': ['energía', 'energético', 'renovable', 'eficiencia energética', 'autoconsumo'],
            'Industria': ['industria', 'industrial', 'manufactura', 'producción'],
            'Agricultura': ['agricultura', 'agrícola', 'rural', 'ganadero', 'agrario'],
            'Comercio': ['comercio', 'comercial', 'exportación', 'internacionalización'],
            'Servicios': ['servicios', 'terciario', 'turismo', 'hostelería'],
            'Construcción': ['construcción', 'vivienda', 'edificación', 'obra'],
            'Salud': ['salud', 'sanitario', 'médico', 'farmacéutico'],
            'Turismo': ['turismo', 'turístico', 'hostelería', 'restauración'],
            'Educación': ['educación', 'educativo', 'formación', 'universidad'],
            'Transporte': ['transporte', 'logística', 'movilidad', 'infraestructura']
        }
        keywords = sector_keywords.get(sector, [sector.lower()])
        return any(keyword in title_lower for keyword in keywords)
    
    def _extract_location_from_title(self, title: str, default_location: str) -> str:
        title_lower = title.lower()
        for region, keywords in self.spanish_regions.items():
            if any(keyword in title_lower for keyword in keywords):
                return region
        if any(keyword in title_lower for keyword in ['europa', 'european', 'ue ', 'unión europea']):
            return 'Unión Europea'
        return default_location

    def _extract_region_from_title(self, title: str, default_region: str) -> str:
        title_lower = title.lower()
        for region, keywords in self.spanish_regions.items():
            if any(keyword in title_lower for keyword in keywords):
                return region
        return default_region

    def _calculate_relevance_score(self, title: str, sector: str) -> int:
        score = 5
        title_lower = title.lower()
        high_relevance_words = ['subvención', 'ayuda', 'convocatoria']
        if any(word in title_lower for word in high_relevance_words):
            score += 2
        low_relevance_words = ['modificación', 'corrección', 'prórroga']
        if any(word in title_lower for word in low_relevance_words):
            score -= 2
        return max(1, min(10, score))

    def _format_boe_date(self, fecha_str: str) -> str:
        try:
            date_obj = datetime.datetime.strptime(fecha_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except:
            return datetime.datetime.now().strftime('%Y-%m-%d')

    def _extract_amount_from_text(self, text: str) -> str:
        amount_patterns = [r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?)', r'(?:hasta|máximo|importe)\s*:?\s*(\d{1,3}(?:[.,]\d{3})*)']
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match: return f"Hasta {match.group(1)}€"
        return "Consultar convocatoria"

    def _generate_future_deadline(self, days: int) -> str:
        future_date = datetime.datetime.now() + datetime.timedelta(days=days)
        return future_date.strftime("%Y-%m-%d")

    def _safe_json_parse(self, text: str) -> Optional[Dict]:
        try: return json.loads(text)
        except: return None