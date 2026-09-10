import logging

import pandas as pd
import sqlalchemy as sa

from src.config import DB_PATH, DUPLICADOS_GATEWAY_FILE, RECONCILIATION_OUTPUT_FILE

log = logging.getLogger(__name__)


def _upsert_por_tx_id(df: pd.DataFrame, tabla: str, engine: sa.Engine, conn: sa.Connection):
    """
    Reemplaza en la tabla de SQLite las filas cuyo tx_id ya existe en `df`,
    y luego inserta `df` completo. Esto logra el efecto de un UPSERT:
    actualiza lo que cambió, agrega lo nuevo, sin duplicar ni perder histórico
    de otros períodos.
    """
    tablas_existentes = sa.inspect(engine).get_table_names()

    if tabla in tablas_existentes:
        tx_ids = df["tx_id"].tolist()

        stmt = sa.text(
            f"DELETE FROM {tabla} WHERE tx_id IN :tx_ids"
        ).bindparams(sa.bindparam("tx_ids", expanding=True))

        conn.execute(stmt, {"tx_ids": tx_ids})

    df.to_sql(tabla, conn, if_exists="append", index=False)


def cargar_a_sqlite(tabla_maestra_path=RECONCILIATION_OUTPUT_FILE,
                     duplicados_path=DUPLICADOS_GATEWAY_FILE):
    log.info("Conectando a SQLite: %s", DB_PATH)

    engine = sa.create_engine(f"sqlite:///{DB_PATH}")

    # Leer los archivos procesados
    df_main = pd.read_csv(tabla_maestra_path)
    df_dups = pd.read_csv(duplicados_path)

    # Columna informativa: cuándo se cargó este registro por última vez
    fecha_carga = pd.Timestamp.today().strftime("%Y-%m-%d")
    df_main["fecha_carga"] = fecha_carga
    df_dups["fecha_carga"] = fecha_carga

    with engine.connect() as conn:
        _upsert_por_tx_id(df_main, "reconciliation_results", engine, conn)
        _upsert_por_tx_id(df_dups, "duplicados_gateway", engine, conn)
        conn.commit()

    log.info("Carga completada: %s", fecha_carga)
    log.info("reconciliation_results: %d filas", len(df_main))
    log.info("duplicados_gateway: %d filas", len(df_dups))
    log.info("Base de datos actualizada correctamente")


if __name__ == "__main__":
    cargar_a_sqlite()
