import logging
from typing import List, Dict

class IdaeScraper:
    def __init__(self, session, config, spanish_regions, logger):
        self.session = session
        self.config = config
        self.spanish_regions = spanish_regions
        self.logger = logger
        
    def search(self, sector: str, company_type: str, region: str) -> List[Dict]:
        """Extrae información del IDAE (sin datos de ejemplo)."""
        return []