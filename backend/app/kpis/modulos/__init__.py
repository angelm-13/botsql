"""KPIs por modulo de negocio.

Cada archivo de esta carpeta trae las consultas de UN modulo y una funcion
`definiciones()` que devuelve sus `KpiDefinition`. `app/kpis/registry.py` las
agrega al final de `KPI_REGISTRY`; los KPIs de siempre se quedan donde estan.

Por que `definiciones()` y no una tupla a nivel de modulo: `KpiDefinition` vive en
`registry.py`, y `registry.py` es quien importa estos archivos. Importarla dentro
de la funcion evita el ciclo sin mover la clase.
"""
