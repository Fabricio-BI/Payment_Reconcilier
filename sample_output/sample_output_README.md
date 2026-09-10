# Resultado de ejemplo

Contenido de esta carpeta:

- `reconciliation_output.csv` — clasificación completa de transacciones (conciliadas, con diferencia, pendientes)
- `duplicados_gateway.csv` — transacciones duplicadas detectadas en el reporte de la pasarela
- `conciliador.db` — base de datos SQLite con el resultado de la carga, abrible con DBeaver, SQLite CLI o cualquier cliente compatible

Corresponde a una ejecución del pipeline sobre los datos sintéticos incluidos en `data/raw/`.

**Esta es una muestra estática — no se actualiza automáticamente junto con el código.** Para generar un resultado actualizado con la versión actual del pipeline, corre desde la raíz del proyecto:

```bash
python main.py
```

El resultado de esa corrida se guarda en `data/processed/` (excluida del repositorio vía `.gitignore`).
