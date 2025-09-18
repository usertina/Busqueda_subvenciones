# Aplicación de Búsqueda de Subvenciones para Empresas

Esta es una aplicación web que permite buscar subvenciones y ayudas para empresas filtrando por sector, ubicación y tipo de empresa.

## Características

- Búsqueda de subvenciones por sector, ubicación y tipo de empresa
- Resultados obtenidos mediante scraping de fuentes oficiales
- Interfaz responsive y fácil de usar
- API JSON para desarrolladores

## Despliegue en Render

1. Crear una cuenta en [Render](https://render.com)
2. Conectar tu repositorio de GitHub con el proyecto
3. Render detectará automáticamente la configuración y desplegará la aplicación

### Variables de Entorno

No se requieren variables de entorno para el funcionamiento básico, pero puedes configurar:

- `PORT`: Puerto donde se ejecutará la aplicación (por defecto 5000)

## Uso de la API

Puedes acceder a los resultados en formato JSON mediante:
Parámetros:
- `sector`: Sector de la empresa (opcional)
- `location`: Ubicación geográfica (opcional)
- `company_type`: Tipo de empresa (opcional)

## Futuras Mejoras

- Implementar scraping en tiempo real de más fuentes oficiales
- Añadir sistema de notificaciones para nuevas subvenciones
- Implementar descarga de documentos oficiales
- Añadir más filtros de búsqueda avanzada

## Tecnologías Utilizadas

- Backend: Python, Flask
- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5
- Scraping: BeautifulSoup4, Requests
- Despliegue: Render, Gunicorn

