import datetime
import re

def register_template_filters(app):
    """Registra los filtros de Jinja2 en la aplicación Flask."""
    app.jinja_env.filters['datetime'] = datetime_filter
    app.jinja_env.filters['days_remaining'] = days_remaining_filter
    app.jinja_env.filters['format_amount'] = format_amount_filter
    app.jinja_env.filters['truncate_smart'] = truncate_smart_filter

def datetime_filter(date_string):
    try:
        date_obj = datetime.datetime.strptime(date_string, "%Y-%m-%d") if isinstance(date_string, str) else date_string
        return date_obj.strftime("%d/%m/%Y")
    except Exception:
        return date_string

def days_remaining_filter(deadline_string):
    try:
        deadline = datetime.datetime.strptime(deadline_string, "%Y-%m-%d") if isinstance(deadline_string, str) else deadline_string
        days = (deadline - datetime.datetime.now()).days
        return max(0, days)
    except Exception:
        return 0

def format_amount_filter(amount_string):
    try:
        if isinstance(amount_string, str):
            numbers = re.findall(r'[\d.,]+', amount_string)
            if numbers:
                number = numbers[0].replace(',', '')
                formatted = f"{float(number):,.2f}".replace(',', ' ') if '.' in number else f"{int(number):,}".replace(',', ' ')
                return amount_string.replace(numbers[0], formatted)
        return amount_string
    except Exception:
        return amount_string

def truncate_smart_filter(text, length=150):
    try:
        if not text: return text
        if len(text) <= length: return text
        truncated = text[:length]
        last_space = truncated.rfind(' ')
        return truncated[:last_space] + '...' if last_space > length * 0.8 else truncated + '...'
    except Exception:
        return text