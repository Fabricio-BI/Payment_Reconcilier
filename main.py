
from core.loader import cargar_a_sqlite
from core.reconciler import run_reconciler
from src.config import (
    DUPLICADOS_GATEWAY_FILE,
    PROCESSED_DIR,
    RECONCILIATION_OUTPUT_FILE,
)
from src.log_config import setup_logger

if __name__ == "__main__":
    log = setup_logger()

    tabla_maestra, duplicados = run_reconciler()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    tabla_maestra.to_csv(RECONCILIATION_OUTPUT_FILE, index=False)
    duplicados.to_csv(DUPLICADOS_GATEWAY_FILE ,index=False)
    cargar_a_sqlite()
