import logging
import re
import datetime
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

class CdtiScraper:
    """Scraper real para el Centro para el Desarrollo Tecnológico Industrial (CDTI)."""
    
    def __init__(self, session, config, spanish_regions, logger):
        self.session = session
        self.config = config
        self.spanish_regions = spanish_regions
        self.logger = logger
        self.base_url = "https://www.cdti.es"
        
        # Verificar disponibilidad de BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            self.BeautifulSoup = BeautifulSoup
            self.bs4_available = True
        except ImportError:
            self.logger.error("BeautifulSoup4 no disponible para CDTI scraper")
            self.bs4_available = False
            return
        
        # URLs reales del CDTI para scraping
        self.urls = {
            'ayudas_empresas': 'https://www.cdti.es/index.asp?MP=4&MS=0&MN=1',
            'programas_cooperacion': 'https://www.cdti.es/index.asp?MP=4&MS=0&MN=4',
            'convocatorias': 'https://www.cdti.es/index.asp?MP=100&MS=606&MN=2'
        }
        
        # Headers específicos para CDTI
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache'
        })
    
    def search(self, sector: str, company_type: str, region: str) -> List[Dict]:
        """Realiza scraping real del sitio web del CDTI."""
        
        if not self.bs4_available:
            self.logger.warning("CDTI scraper deshabilitado - BeautifulSoup4 no disponible")
            return []
        
        all_grants = []
        
        try:
            self.logger.info("Iniciando scraping real del CDTI...")
            
            # Scrapear cada sección
            for section_name, url in self.urls.items():
                try:
                    self.logger.info(f"Scrapeando sección: {section_name}")
                    section_grants = self._scrape_section(url, section_name, sector, company_type, region)
                    if section_grants:
                        all_grants.extend(section_grants)
                        self.logger.info(f"Encontradas {len(section_grants)} ayudas en {section_name}")
                    
                    time.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    self.logger.warning(f"Error scrapeando {section_name}: {e}")
                    continue
            
            # Procesar y filtrar resultados
            filtered_grants = self._process_results(all_grants, sector, company_type, region)
            
            self.logger.info(f"CDTI scraping completado: {len(filtered_grants)} ayudas válidas encontradas")
            return filtered_grants
            
        except Exception as e:
            self.logger.error(f"Error general en scraper CDTI: {e}")
            return []
    
    def _scrape_section(self, url: str, section_name: str, sector: str, company_type: str, region: str) -> List[Dict]:
        """Scrapea una sección específica del CDTI."""
        grants = []
        
        try:
            # Realizar petición HTTP
            response = self.session.get(url, timeout=self.config.get('timeout', 20))
            
            if response.status_code != 200:
                self.logger.warning(f"Error HTTP {response.status_code} para {url}")
                return grants
            
            # Detectar encoding
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
            
            soup = self.BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
            
            # Buscar enlaces a programas y convocatorias
            program_links = self._find_program_links(soup)
            
            self.logger.info(f"Encontrados {len(program_links)} enlaces en {section_name}")
            
            # Procesar cada enlace encontrado
            for i, link_data in enumerate(program_links[:15]):  # Limitar a 15 por sección
                try:
                    grant_data = self._extract_grant_from_link(link_data, section_name)
                    
                    if grant_data and self._is_relevant_grant(grant_data, sector, company_type, region):
                        grants.append(grant_data)
                    
                    # Rate limiting entre enlaces
                    if i < len(program_links) - 1:
                        time.sleep(1)
                        
                except Exception as e:
                    self.logger.warning(f"Error procesando enlace {link_data.get('title', 'N/A')}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error scrapeando sección {url}: {e}")
        
        return grants
    
    def _find_program_links(self, soup) -> List[Dict]:
        """Encuentra enlaces a programas y convocatorias."""
        links = []
        
        # Selectores CSS para diferentes tipos de enlaces en CDTI
        selectors = [
            'a[href*="MP=4"]',  # Enlaces de ayudas
            'a[href*="programa"]',
            'a[href*="convocatoria"]',
            'a[href*="ayuda"]',
            'td a',  # Enlaces en tablas
            '.contenido a',
            'div[class*="texto"] a',
            'p a'
        ]
        
        seen_urls = set()
        
        for selector in selectors:
            found_links = soup.select(selector)
            
            for link in found_links:
                href = link.get('href', '').strip()
                title = link.get_text(strip=True)
                
                if not href or not title or len(title) < 10:
                    continue
                
                # Construir URL completa
                if href.startswith('/') or href.startswith('index.asp'):
                    full_url = urljoin(self.base_url, href)
                elif not href.startswith('http'):
                    full_url = urljoin(self.base_url, href)
                else:
                    full_url = href
                
                # Filtrar URLs relevantes
                if not self._is_relevant_url(full_url, title):
                    continue
                
                # Evitar duplicados
                if full_url in seen_urls:
                    continue
                
                seen_urls.add(full_url)
                
                links.append({
                    'url': full_url,
                    'title': title[:200],
                    'text': title
                })
        
        return links
    
    def _is_relevant_url(self, url: str, title: str) -> bool:
        """Verifica si una URL es relevante para programas/ayudas."""
        title_lower = title.lower()
        
        # Incluir URLs relevantes
        relevant_keywords = [
            'programa', 'ayuda', 'convocatoria', 'subvención', 'financiación',
            'i+d', 'innovación', 'tecnológico', 'neotec', 'eureka', 'innterconecta',
            'pid', 'cooperación', 'internacional'
        ]
        
        if any(keyword in title_lower for keyword in relevant_keywords):
            # Excluir URLs no relevantes
            exclude_keywords = [
                'contacto', 'aviso legal', 'cookies', 'mapa', 'búsqueda',
                'newsletter', 'rss', 'imprimir', 'pdf', 'descargar'
            ]
            
            if not any(keyword in title_lower for keyword in exclude_keywords):
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
                    if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                        response.encoding = 'utf-8'
                    
                    soup = self.BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                    description = self._extract_description_from_page(soup, title)
                    amount = self._extract_amount_from_page(soup)
                else:
                    description = None
                    amount = "Consultar convocatoria"
            except:
                description = None
                amount = "Consultar convocatoria"
            
            # Generar datos de la ayuda
            grant = {
                'title': title,
                'description': description or f"Programa del CDTI. Consulta la documentación oficial para más detalles.",
                'sector': self._determine_sector_from_content(title + ' ' + (description or '')),
                'location': 'España',
                'region': 'Todas',
                'company_type': self._determine_company_type_from_content(title + ' ' + (description or '')),
                'amount': amount,
                'deadline': self._extract_or_estimate_deadline(),
                'publication_date': self._estimate_publication_date(),
                'source': 'CDTI - Centro para el Desarrollo Tecnológico Industrial',
                'link': url,
                'relevance_score': self._calculate_relevance_score(title, description or ''),
                'identifier': self._generate_identifier(title, 'CDTI')
            }
            
            return grant
            
        except Exception as e:
            self.logger.warning(f"Error extrayendo datos de {link_data.get('url', 'N/A')}: {e}")
            return None
    
    def _extract_description_from_page(self, soup, title: str) -> str:
        """Extrae descripción de la página del programa."""
        # Buscar descripción en diferentes elementos
        description_selectors = [
            'div.contenido p',
            'td p',
            'div[class*="texto"] p',
            '.descripcion',
            '.resumen',
            'p'
        ]
        
        for selector in description_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 100 and text.lower() not in title.lower():
                    # Limpiar texto
                    text = re.sub(r'\s+', ' ', text)
                    return text[:600]
        
        return None
    
    def _extract_amount_from_page(self, soup) -> str:
        """Extrae información sobre importes de la página."""
        text_content = soup.get_text().lower()
        
        # Patrones para importes del CDTI
        amount_patterns = [
            r'hasta\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|millones?)',
            r'importe.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?)',
            r'dotación.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|millones?)',
            r'presupuesto.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?|millones?)',
            r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:€|euros?)\s*(?:máximo|hasta)',
            r'subvención.*?(\d{1,2})\s*%'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text_content)
            if match:
                amount = match.group(1)
                if '%' in pattern:
                    return f"Hasta {amount}% del proyecto"
                elif 'millones' in text_content or 'millón' in text_content:
                    return f"Hasta {amount}M€"
                else:
                    return f"Hasta {amount}€"
        
        # Buscar menciones de financiación
        if any(keyword in text_content for keyword in 
               ['financiación', 'subvención', 'ayuda', 'préstamo', 'incentivo']):
            return "Ver convocatoria"
        
        return "Consultar convocatoria"
    
    def _determine_sector_from_content(self, content: str) -> str:
        """Determina el sector basado en el contenido."""
        content_lower = content.lower()
        
        sector_keywords = {
            'Tecnología': ['tecnología', 'tic', 'digital', 'software', 'ia', 'innovación tecnológica', 'neotec'],
            'Industria': ['industria', 'industrial', 'manufactura', 'producción', 'innterconecta'],
            'Energía': ['energía', 'energético', 'renovables', 'sostenible'],
            'Salud': ['salud', 'biotecnología', 'farmacéutico', 'biomédico'],
            'Transporte': ['transporte', 'movilidad', 'logística', 'automoción'],
            'Aeroespacial': ['aeroespacial', 'aeronáutico', 'espacial', 'defensa']
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return sector
        
        return 'Tecnología'  # Por defecto para CDTI
    
    def _determine_company_type_from_content(self, content: str) -> str:
        """Determina el tipo de empresa objetivo."""
        content_lower = content.lower()
        
        if 'pyme' in content_lower or 'pequeña' in content_lower or 'mediana' in content_lower:
            return 'PYME'
        elif 'startup' in content_lower or 'nueva empresa' in content_lower:
            return 'Startup'
        elif 'gran empresa' in content_lower or 'grande' in content_lower:
            return 'Grande empresa'
        elif 'universidad' in content_lower or 'centro de investigación' in content_lower:
            return 'Centro de investigación'
        
        return 'Todos'
    
    def _calculate_relevance_score(self, title: str, description: str) -> int:
        """Calcula puntuación de relevancia."""
        score = 6  # Base para CDTI
        
        combined_text = (title + ' ' + description).lower()
        
        # Aumentar por palabras clave relevantes
        high_relevance = ['i+d+i', 'innovación', 'tecnológico', 'neotec', 'eureka', 'innterconecta']
        for keyword in high_relevance:
            if keyword in combined_text:
                score += 2
        
        medium_relevance = ['programa', 'ayuda', 'subvención', 'financiación']
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
        """Verifica si la ayuda es relevante."""
        if not grant or not grant.get('title'):
            return False
        
        # Filtrar por sector si no es "Todos"
        if sector != 'Todos':
            grant_sector = grant.get('sector', '')
            content = (grant.get('title', '') + ' ' + grant.get('description', '')).lower()
            
            # Verificar coincidencia directa o por palabras clave
            if grant_sector != sector:
                sector_keywords = {
                    'Tecnología': ['tecnología', 'tic', 'digital', 'innovación'],
                    'Industria': ['industria', 'industrial', 'manufactura'],
                    'Energía': ['energía', 'renovables', 'sostenible'],
                    'Salud': ['salud', 'biotecnología', 'farmacéutico']
                }.get(sector, [sector.lower()])
                
                if not any(keyword in content for keyword in sector_keywords):
                    return False
        
        # Verificar relevancia mínima
        if grant.get('relevance_score', 0) < 4:
            return False
        
        return True
    
    def _process_results(self, grants: List[Dict], sector: str, company_type: str, region: str) -> List[Dict]:
        """Procesa y filtra los resultados."""
        if not grants:
            return []
        
        # Eliminar duplicados por título similar
        unique_grants = {}
        for grant in grants:
            title_key = re.sub(r'[^\w\s]', '', grant.get('title', '')).lower()[:50]
            if title_key not in unique_grants:
                unique_grants[title_key] = grant
        
        # Ordenar por relevancia
        sorted_grants = sorted(
            unique_grants.values(),
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        
        return sorted_grants[:8]  # Limitar resultados
    
    def _extract_or_estimate_deadline(self) -> str:
        """Extrae o estima fecha límite."""
        # Estimar fecha límite futura (60-120 días)
        days = 90
        future_date = datetime.datetime.now() + datetime.timedelta(days=days)
        return future_date.strftime('%Y-%m-%d')
    
    def _estimate_publication_date(self) -> str:
        """Estima fecha de publicación."""
        return datetime.datetime.now().strftime('%Y-%m-%d')
    
    def _generate_identifier(self, title: str, source: str) -> str:
        """Genera identificador único."""
        normalized = re.sub(r'[^\w]', '', title.lower())
        return f"{source}_{normalized[:30]}_{hash(title) % 10000}"