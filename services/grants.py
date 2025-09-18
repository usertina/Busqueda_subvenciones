import datetime
from typing import List, Dict, Tuple

def process_grants_data(grants: List[Dict], start_time: datetime.datetime = None) -> Tuple[List[Dict], Dict]:
    """
    Procesa la lista de subvenciones para añadir información adicional como días restantes e indicadores de urgencia.
    Calcula y devuelve estadísticas de búsqueda.
    """
    processed_grants = []
    
    for grant in grants:
        # Añadir días restantes y urgencia
        try:
            deadline = datetime.datetime.strptime(grant.get('deadline', ''), "%Y-%m-%d")
            days_remaining = (deadline - datetime.datetime.now()).days
            grant['days_remaining'] = max(0, days_remaining)
        except (ValueError, TypeError):
            grant['days_remaining'] = 0

        if grant['days_remaining'] <= 7:
            grant['urgency'] = 'critical'
        elif grant['days_remaining'] <= 30:
            grant['urgency'] = 'high'
        elif grant['days_remaining'] <= 60:
            grant['urgency'] = 'medium'
        else:
            grant['urgency'] = 'low'
        
        processed_grants.append(grant)

    # Calcular estadísticas
    end_time = datetime.datetime.now()
    search_time = round((end_time - start_time).total_seconds(), 2) if start_time else 0
    results_count = len(processed_grants)

    stats = {
        'total_results': results_count,
        'active_grants': len([g for g in processed_grants if g.get('days_remaining', 0) > 0]),
        'urgent_grants': len([g for g in processed_grants if g.get('urgency') in ['critical', 'high']]),
        'search_time': search_time
    }
    
    return processed_grants, stats