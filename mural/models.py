"""
Compatibilidad de modelos para la app `mural`.

Esta app ya no define sus propias tablas; reutiliza los modelos definidos
en la app `operatividad`. Para evitar duplicación en la base de datos y
mantener compatibilidad con el código existente, exponemos nombres comunes
referenciando directamente los modelos de `operatividad`.
"""

from operatividad.models import (
    Area,
    Contenido,
    Archivo,
    AsignacionArea as Asignacion,
)

# Nota: `Asignacion` aquí es un alias a `AsignacionArea` de la app
# `operatividad`. No se crean tablas nuevas en esta app.

__all__ = ["Area", "Contenido", "Archivo", "Asignacion"]
