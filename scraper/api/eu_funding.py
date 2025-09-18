import logging
from typing import List, Dict

class EUFundingScraper:
    def __init__(self, session, config, logger):
        self.session = session
        self.config = config
        self.logger = logger
        
    def search(self, sector: str, location: str, company_type: str) -> List[Dict]:
        """Busca en EU Funding & Tenders Portal (sin datos de ejemplo)."""
        return []