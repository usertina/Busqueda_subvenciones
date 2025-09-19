import logging
import re
import datetime
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

class IdaeScraper:
    """Scraper real para el Instituto para la Diversificación y Ahorro de la Energía (IDAE)."""
    
    def __init__(self, session, config, spanish_regions, logger):
        self.session = session
        self.config = config
        self.spanish_regions = spanish_regions
        self.logger = logger
        self.base_url = "https://www.idae.es"
        
        # Verificar disponibilidad de BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            self.BeautifulSoup = BeautifulSoup
            self.bs4_available = True
        except ImportError:
            self.logger.error("BeautifulSoup4 no disponible para IDAE scraper")
            self.bs4_available = False
            return
        
        # URLs reales del IDAE para scraping
        self.urls = {
            'ayudas_financiacion': 'https://www.idae.es/ayudas-y-financiacion',
            'ayudas_empresas': 'https://www.idae.es/ayudas-y-financiacion/empresas',
            'convocatorias': 'https://www.idae.es/ayudas-y-financiacion/convocatorias',
            'programas_particulares': 'https://www.idae.es/ayudas-y-financiacion/particulares-y-comunidades',
            'fondos_europeos': 'https://www.idae.es/ayudas-y-financiacion/fondos-europeos'
        }
        
        # Headers específicos para IDAE
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Cache-Control': 'no-cache'
        })
    
    def search(self, sector: str, company_type: str, region: str) -> List[Dict]:
        """Realiza scraping real del sitio web del IDAE."""
        
        if not self.bs4_available:
            self.logger.warning("IDAE scraper deshabilitado - BeautifulSoup4 no disponible")
            return []
        
        all_grants = []
        
        try:
            self.logger.info("Iniciando scraping real del IDAE...")
            
            # Scrapear cada sección
            for section_name, url in self.urls.items():
                try:
                    self.logger.info(f"Scrapeando sección IDAE: {section_name}")
                    section_grants = self._scrape_section(url, section_name, sector, company_type, region)
                    if section_grants:
                        all_grants.extend(section_grants)
                        self.logger.info(f"Encontradas {len(section_grants)} ayudas en {section_name}")
                    
                    time.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    self.logger.warning(f"Error scrapeando IDAE {section_name}: {e}")
                    continue
            
            # Procesar y filtrar resultados
            filtered_grants = self._process_results(all_grants, sector, company_type, region)
            
            self.logger.info(f"IDAE scraping completado: {len(filtered_grants)} ayudas válidas encontradas")
            return filtered_grants
            
        except Exception as e:
            self.logger.error(f"Error general en scraper IDAE: {e}")
            return []
    
    def _scrape_section(self, url: str, section_name: str, sector: str, company_type: str, region: str) -> List[Dict]:
        """Scrapea una sección específica del IDAE."""
        grants = []
        
        try:
            # Realizar petición HTTP
            response = self.session.get(url, timeout=self.config.get('timeout', 20))
            
            if response.status_code != 200:
                self.logger.warning(f"Error HTTP {response.status_code} para {url}")
                return grants
            
            soup = self.BeautifulSoup(response.content, 'html.parser')
            
            # Buscar enlaces a programas y ayudas
            program_links = self._find_program_links(soup)
            
            self.logger.info(f"Encontrados {len(program_links)} enlaces en IDAE {section_name}")
            
            # Procesar cada enlace encontrado
            for i, link_data in enumerate(program_links[:12]):  # Limitar a 12 por sección
                try:
                    grant_data = self._extract_grant_from_link(link_data, section_name)
                    
                    if grant_data and self._is_relevant_grant(grant_data, sector, company_type, region):
                        grants.append(grant_data)
                    
                    # Rate limiting entre enlaces
                    if i < len(program_links) - 1:
                        time.sleep(1.5)
                        
                except Exception as e:
                    self.logger.warning(f"Error procesando enlace IDAE {link_data.get('title', 'N/A')}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error scrapeando sección IDAE {url}: {e}")
        
        return grants
    
    def _find_program_links(self, soup) -> List[Dict]:
        """Encuentra enlaces a programas y ayudas del IDAE."""
        links = []
        
        # Selectores CSS específicos para el sitio del IDAE
        selectors = [
            'a[href*="ayuda"]',
            'a[href*="programa"]',
            'a[href*="plan"]',
            'a[href*="convocatoria"]',
            'a[href*="financiacion"]',
            'article a',
            '.programa-item a',
            '.ayuda-item a',
            '.contenido-principal a',
            'div[class*="listado"] a',
            '.card a',
            '.destacado a'
        ]
        
        seen_urls = set()
        
        for selector in selectors:
            found_links = soup.select(selector)
            
            for link in found_links:
                href = link.get('href', '').strip()
                title = link.get_text(strip=True)
                
                if not href or not title or len(title) < 15:
                    continue
                
                # Construir URL completa
                if href.startswith('/'):
                    full_url = urljoin(self.base_url, href)
                elif not href.startswith('http'):
                    full_url = urljoin(self.base_url, href)
                else:
                    full_url = href
                
                # Filtrar URLs relevantes para IDAE
                if not self._is_relevant_idae_url(full_url, title):
                    continue
                
                # Evitar duplicados
                if full_url in seen_urls:
                    continue
                
                seen_urls.add(full_url)
                
                links.append({
                    'url': full_url,
                    'title': title[:250],
                    'text': title
                })
        
        return links
    
    def _is_relevant_idae_url(self, url: str, title: str) -> bool:
        """Verifica si una URL es relevante para programas/ayudas del IDAE."""
        title_lower = title.lower()
        url_lower = url.lower()
        
        # Incluir URLs relevantes para energía
        relevant_keywords = [
            'ayuda', 'programa', 'plan', 'convocatoria', 'subvención', 'financiación',
            'eficiencia energética', 'renovables', 'autoconsumo', 'rehabilitación',
            'moves', 'pree', 'biomasa', 'hidrógeno', 'solar', 'eólica',
            'movilidad', 'vehículo eléctrico', 'sostenible'
        ]
        
        if any(keyword in title_lower for keyword in relevant_keywords):
            # Excluir URLs no relevantes
            exclude_keywords = [
                'contacto', 'aviso legal', 'cookies', 'política', 'mapa web',
                'newsletter', 'rss', 'imprimir', 'buscar', 'buscador'
            ]
            
            if not any(keyword in title_lower for keyword in exclude_keywords):
                # Verificar que sea del dominio IDAE
                if 'idae.es' in url_lower:
                    return True
        
        return False
    
    def _extract_grant_from_link(self, link_data: Dict, section_name: str) -> Optional[Dict]:
        """Extrae información de una ayuda desde su página específica."""
        try:
            url = link_data['url']
            title = link_data['title']
            
            # Intentar obtener más detalles de la página específica
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    soup = self.BeautifulSoup(response.content, 'html.parser')
                    description = self._extract_description_from_idae_page(soup, title)
                    amount = self._extract_amount_from_idae_page(soup)
                    deadline = self._extract_deadline_from_idae_page(soup)
                    target_region = self._extract_target_region_from_page(soup)
                else:
                    description = None
                    amount = "Consultar convocatoria"
                    deadline = self._estimate_deadline()
                    target_region = 'Todas'
            except:
                description = None
                amount = "Consultar convocatoria"
                deadline = self._estimate_deadline()
                target_region = 'Todas'
            
            # Generar datos de la ayuda
            grant = {
                'title': title,
                'description': description or f"Programa del IDAE relacionado con eficiencia energética y sostenibilidad. Consulta la documentación oficial.",
                'sector': self._determine_energy_sector_from_content(title + ' ' + (description or '')),
                'location': 'España',
                'region': target_region,
                'company_type': self._determine_idae_company_type(title + ' ' + (description or '')),
                'amount': amount,
                'deadline': deadline,
                'publication_date': self._estimate_publication_date(),
                'source': 'IDAE - Instituto para la Diversificación y Ahorro de la Energía',
                'link': url,
                'relevance_score': self._calculate_idae_relevance_score(title, description or ''),
                'identifier': self._generate_identifier(title, 'IDAE'),
                'energy_focus': self._extract_energy_focus_from_content(title + ' ' + (description or ''))
            }
            
            return grant
            
        except Exception as e:
            self.logger.warning(f"Error extrayendo datos IDAE de {link_data.get('url', 'N/A')}: {e}")
            return None
    
    def _extract_description_from_idae_page(self, soup, title: str) -> str:
        """Extrae descripción de la página del programa IDAE."""
        # Selectores específicos para páginas del IDAE
        description_selectors = [
            'div.contenido-principal p',
            'div.descripcion p',
            'div.resumen p',
            'article p',
            'div[class*="texto"] p',
            '.programa-detalle p',
            'div.field-item p',
            'div.content p',
            'main p'
        ]
        
        for selector in description_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 100 and text.lower() not in title.lower():
                    # Limpiar y normalizar texto
                    text = re.sub(r'\s+', ' ', text)
                    # Excluir textos genéricos
                    if not any(generic in text.lower() for generic in 
                             ['cookies', 'aviso legal', 'política de privacidad']):
                        return text[:700]
        
        return None
    
    def _extract_amount_from_idae_page(self, soup) -> str:
        """Extrae información sobre importes de la página IDAE."""
        text_content = soup.get_text().lower()
        
        # Patrones específicos para importes del IDAE
        amount_patterns = [
            r'hasta\s+el\s+(\d{1,2})\s*%.*(?:inversión|coste)',
            r'(\d{1,2})\s*%.*(?:inversión|coste|subvencionable)',
            r'hasta\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?)',
            r'importe.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?)',
            r'dotación.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|millones?)',
            r'presupuesto.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|millones?)',
            r'ayuda.*?(\d{1,3}(?:[.,]\d{3})*)\s*€',
            r'(\d{1,3}(?:[.,]\d{3})*)\s*€[\/\s]*(?:mwh|kwh)',
            r'subvención.*?(\d{1,2})\s*%'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                amount = match.group(1)
                
                # Determinar tipo de ayuda
                if '%' in pattern or 'por ciento' in text_content:
                    return f"Hasta {amount}% de la inversión"
                elif 'millones' in text_content or 'millón' in text_content:
                    return f"Hasta {amount}M€"
                elif 'mwh' in pattern.lower() or 'kwh' in pattern.lower():
                    unit = 'MWh' if 'mwh' in text_content else 'kWh'
                    return f"{amount}€/{unit}"
                else:
                    return f"Hasta {amount}€"
        
        # Buscar menciones específicas de eficiencia energética
        if any(keyword in text_content for keyword in 
               ['eficiencia energética', 'certificado energético', 'clase energética']):
            return "Según mejora energética"
        
        # Buscar menciones de financiación
        if any(keyword in text_content for keyword in 
               ['financiación', 'subvención', 'ayuda', 'incentivo', 'bonificación']):
            return "Ver convocatoria"
        
        return "Consultar convocatoria"
    
    def _extract_deadline_from_idae_page(self, soup) -> str:
        """Extrae fecha límite de la página IDAE."""
        text_content = soup.get_text()
        
        # Patrones para fechas específicas
        date_patterns = [
            r'hasta\s+el\s+(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})',
            r'plazo.*?(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})',
            r'fecha[:\s]*límite.*?(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})',
            r'solicitudes.*?(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})',
            r'(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4}).*(?:fecha|plazo|límite)',
            r'convocatoria.*?(\d{4})'  # Para convocatorias anuales
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 3:  # día, mes, año
                        day, month, year = match
                        date_obj = datetime.datetime(int(year), int(month), int(day))
                    elif len(match) == 1:  # solo año
                        year = match[0]
                        date_obj = datetime.datetime(int(year), 12, 31)
                    
                    if date_obj > datetime.datetime.now():
                        return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # Buscar plazos relativos o permanentes
        if any(keyword in text_content.lower() for keyword in ['permanente', 'todo el año']):
            return self._estimate_deadline(365)
        
        return self._estimate_deadline()
    
    def _extract_target_region_from_page(self, soup) -> str:
        """Extrae región objetivo de la página."""
        text_content = soup.get_text().lower()
        
        # Buscar menciones específicas de comunidades autónomas
        for region, keywords in self.spanish_regions.items():
            if any(keyword in text_content for keyword in keywords):
                return region
        
        return 'Todas'
    
    def _determine_energy_sector_from_content(self, content: str) -> str:
        """Determina el sector energético basado en el contenido."""
        content_lower = content.lower()
        
        sector_keywords = {
            'Energía': ['eficiencia energética', 'renovables', 'autoconsumo', 'energía'],
            'Transporte': ['movilidad', 'vehículo eléctrico', 'moves', 'transporte'],
            'Construcción': ['rehabilitación', 'edificio', 'vivienda', 'construcción'],
            'Industria': ['industria', 'industrial', 'cogeneración', 'proceso'],
            'Agricultura': ['biomasa', 'biogás', 'agricultura', 'rural']
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return sector
        
        return 'Energía'  # Por defecto para IDAE
    
    def _determine_idae_company_type(self, content: str) -> str:
        """Determina tipo de beneficiario para programas IDAE."""
        content_lower = content.lower()
        
        type_keywords = {
            'PYME': ['pyme', 'pequeña empresa', 'mediana empresa'],
            'Grande empresa': ['gran empresa', 'empresa industrial'],
            'Particular': ['particular', 'ciudadano', 'vivienda unifamiliar'],
            'Comunidad de propietarios': ['comunidad de propietarios', 'comunidades'],
            'Ayuntamiento': ['ayuntamiento', 'corporación local', 'entidad local'],
            'Autónomo': ['autónomo', 'trabajador por cuenta propia']
        }
        
        for company_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return company_type
        
        return 'Todos'
    
    def _extract_energy_focus_from_content(self, content: str) -> str:
        """Extrae el foco energético específico."""
        content_lower = content.lower()
        
        focus_keywords = {
            'Eficiencia Energética': ['eficiencia energética', 'ahorro energético'],
            'Energías Renovables': ['renovables', 'solar', 'eólica', 'fotovoltaica'],
            'Movilidad Sostenible': ['vehículo eléctrico', 'movilidad', 'moves'],
            'Rehabilitación': ['rehabilitación energética', 'mejora energética'],
            'Autoconsumo': ['autoconsumo', 'autoabastecimiento'],
            'Hidrógeno': ['hidrógeno', 'hidrógeno renovable']
        }
        
        for focus, keywords in focus_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return focus
        
        return 'General'
    
    def _calculate_idae_relevance_score(self, title: str, description: str) -> int:
        """Calcula puntuación de relevancia específica para IDAE."""
        score = 7  # Base alta para IDAE (especializado)
        
        combined_text = (title + ' ' + description).lower()
        
        # Aumentar por palabras clave de alta relevancia
        high_relevance = [
            'eficiencia energética', 'autoconsumo', 'renovables', 'movilidad sostenible',
            'rehabilitación energética', 'hidrógeno renovable'
        ]
        for keyword in high_relevance:
            if keyword in combined_text:
                score += 2
        
        # Aumentar por palabras de relevancia media
        medium_relevance = ['energía', 'sostenible', 'programa', 'plan']
        for keyword in medium_relevance:
            if keyword in combined_text:
                score += 1
        
        # Disminuir por contenido menos relevante
        low_relevance = ['modificación', 'corrección', 'prórroga']
        for keyword in low_relevance:
            if keyword in combined_text:
                score -= 2
        
        return max(1, min(10, score))
    
    def _is_relevant_grant(self, grant: Dict, sector: str, company_type: str, region: str) -> bool:
        """Verifica si la ayuda IDAE es relevante."""
        if not grant or not grant.get('title'):
            return False
        
        # Verificar fechas válidas
        try:
            deadline = datetime.datetime.strptime(grant['deadline'], '%Y-%m-%d')
            if deadline < datetime.datetime.now() - datetime.timedelta(days=30):
                return False
        except:
            pass
        
        # Verificar relevancia de sector (más flexible para IDAE - enfoque energético)
        if sector not in ['Todos', 'Energía', 'Construcción', 'Transporte', 'Industria']:
            content = (grant.get('title', '') + ' ' + grant.get('description', '')).lower()
            energy_keywords = ['energía', 'eficiencia', 'renovable', 'sostenible', 'autoconsumo']
            if not any(keyword in content for keyword in energy_keywords):
                return False
        
        # Verificar tipo de empresa
        if company_type != 'Todos':
            grant_company_type = grant.get('company_type', 'Todos')
            if grant_company_type != 'Todos' and grant_company_type != company_type:
                return False
        
        # Verificar región
        if region != 'Todas':
            grant_region = grant.get('region', 'Todas')
            if grant_region != 'Todas' and grant_region != region:
                return False
        
        # Verificar relevancia mínima
        if grant.get('relevance_score', 0) < 5:
            return False
        
        return True
    
    def _process_results(self, grants: List[Dict], sector: str, company_type: str, region: str) -> List[Dict]:
        """Procesa y filtra los resultados del IDAE."""
        if not grants:
            return []
        
        # Eliminar duplicados por título similar
        unique_grants = {}
        for grant in grants:
            # Crear clave única considerando título y foco energético
            title_key = re.sub(r'[^\w\s]', '', grant.get('title', '')).lower()[:40]
            energy_focus = grant.get('energy_focus', 'general').lower()
            unique_key = f"{title_key}_{energy_focus}"
            
            if unique_key not in unique_grants:
                unique_grants[unique_key] = grant
            elif grant.get('relevance_score', 0) > unique_grants[unique_key].get('relevance_score', 0):
                unique_grants[unique_key] = grant
        
        # Filtrar por relevancia mínima
        relevant_grants = [g for g in unique_grants.values() if g.get('relevance_score', 0) >= 5]
        
        # Ordenar por relevancia y fecha
        sorted_grants = sorted(
            relevant_grants,
            key=lambda x: (x.get('relevance_score', 0), x.get('publication_date', '1900-01-01')),
            reverse=True
        )
        
        return sorted_grants[:8]  # Limitar a 8 resultados
    
    def _estimate_deadline(self, days: int = 120) -> str:
        """Genera fecha límite estimada."""
        future_date = datetime.datetime.now() + datetime.timedelta(days=days)
        return future_date.strftime('%Y-%m-%d')
    
    def _estimate_publication_date(self) -> str:
        """Estima fecha de publicación."""
        return datetime.datetime.now().strftime('%Y-%m-%d')
    
    def _generate_identifier(self, title: str, source: str) -> str:
        """Genera identificador único."""
        normalized = re.sub(r'[^\w]', '', title.lower())
        return f"{source}_{normalized[:30]}_{hash(title) % 10000}"