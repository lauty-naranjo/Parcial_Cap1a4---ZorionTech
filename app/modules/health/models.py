"""Modelos de tabla del módulo health.

El módulo `health` no define tablas: solo expone los endpoints de salud
(`/health/live` y `/health/ready`). Las nueve tablas del dominio viven en
`app/modules/*/models.py` (editoriales, géneros, autores, libros, clientes y
ventas). Este archivo se conserva vacío a propósito para mantener la misma
estructura de paquete que el resto de los módulos.
"""
