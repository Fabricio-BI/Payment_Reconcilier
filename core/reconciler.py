import logging

import numpy as np
import pandas as pd

from core.etl import run_etl
from src.config import TOLERANCIA_CENTAVOS

log = logging.getLogger(__name__)

# Límite para absorber discrepancias menores de redondeo en pasarelas


def cruzar_banco_erp(bank: pd.DataFrame, erp: pd.DataFrame) -> pd.DataFrame:
    log.info("Cruzando banco ↔ ERP...")

    bank_slim = bank[[
        "tx_id", "fecha_tx", "fecha_liquidacion", "gateway",
        "card_type", "monto_bruto", "comision_banco",
        "ret_iva_banco", "ret_renta_banco", "monto_neto_banco",
        "comision_esperada", "neto_esperado_banco",
        "estado_banco", "es_chargeback", "original_transaction_id"
    ]].copy()

    erp_slim = erp[[
        "tx_id", "invoice_number", "fecha_factura", "client_name",
        "monto_bruto_erp", "subtotal", "iva_amount",
        "comision_esperada_erp", "ret_iva_esperada_erp",
        "ret_renta_esperada_erp", "neto_esperado_erp",
        "estado_erp", "erp_module"
    ]].copy()

    df = bank_slim.merge(erp_slim, on="tx_id", how="outer", suffixes=("_bank","_erp"))

    df["en_banco"] = df["monto_bruto"].notna().astype(int)
    df["en_erp"]   = df["monto_bruto_erp"].notna().astype(int)

    # ── FIX: recuperar client_name y monto_bruto_erp para chargebacks ────────
    # Las filas de reversión (chargeback) no generaron factura propia — son
    # una reversión de la venta original. original_transaction_id guarda el
    # tx_id de esa venta, así que buscamos sus datos directamente en erp.
    erp_lookup = erp[["tx_id", "client_name", "monto_bruto_erp"]].rename(  # type: ignore[arg-type]
        columns={
            "tx_id": "original_transaction_id",
            "client_name": "client_name_original",
            "monto_bruto_erp": "monto_bruto_erp_original",
        }
    )

    df = df.merge(erp_lookup, on="original_transaction_id", how="left")

    df["client_name"] = df["client_name"].fillna(df["client_name_original"])
    df["monto_bruto_erp"] = df["monto_bruto_erp"].fillna(df["monto_bruto_erp_original"])

    df = df.drop(columns=["client_name_original", "monto_bruto_erp_original"])


    # Comparación de flujos netos para evaluar descuadres iniciales
    df["diff_banco_erp"] = (
        df["monto_neto_banco"].fillna(0) - df["neto_esperado_erp"].fillna(0)
    ).round(2)

    log.info("  Cruce banco↔ERP: %d filas", len(df))
    return df


def agregar_gateway(df: pd.DataFrame, gateway: pd.DataFrame) -> pd.DataFrame:
    log.info("Agregando pasarela al cruce")

    # Se aíslan registros únicos de pasarela; duplicados van por canal operativo separado
    gw_unique= gateway.loc[
        gateway["es_duplicado"] == 0 ,
        ["tx_id", "monto_bruto_gw", "comision_gw","neto_gw", "estado_gw", "batch_id"]
    ].copy()

    df = df.merge(gw_unique, on="tx_id", how="left")
    df["en_gateway"] = df["monto_bruto_gw"].notna().astype(int)

    # Auditoría de comisiones cobradas vs tarifa contractual esperada
    df["diff_comision"] = (
        df["comision_banco"].fillna(0) - df["comision_esperada"].fillna(0)
    ).round(2)

    log.info("  Cruce completo: %d filas", len(df))
    return df


def clasificar_transacciones(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Clasificando transacciones")

    # Máscaras booleanas para la asignación de estados de concilacion
    mask_conciliada = (
        (df["en_banco"] == 1) &
        (df["en_erp"]   == 1) &
        (df["en_gateway"]== 1) &
        (df["diff_banco_erp"].abs() <= TOLERANCIA_CENTAVOS) &
        (df["es_chargeback"].fillna(0) == 0)
    )

    # Diferencias : Comision cobrada de mas

    mask_com_mas = (
        (df["en_banco"] == 1) &
        (df["en_erp"]   == 1) &
        (df["diff_banco_erp"].abs() > TOLERANCIA_CENTAVOS) &
        (df["diff_comision"] > TOLERANCIA_CENTAVOS)
    )


    # Diferencia : diferencia de centavos
    mask_centavos = (
        (df["en_banco"] == 1) &
        (df["en_erp"]   == 1) &
        (df["diff_banco_erp"].abs() > 0) &
        (df["diff_banco_erp"].abs() <= TOLERANCIA_CENTAVOS) &
        (~mask_conciliada)
    )

    # Pediente : (en banco , no en ERP)
    mask_chargeback = (df["es_chargeback"].fillna(0) == 1)

    # Pendiente : solo en banco
    mask_solo_banco = (
        (df["en_banco"] == 1) &
        (df["en_erp"]   == 0) &
        (df["es_chargeback"].fillna(0) == 0)
    )

    #Pendiente : solo ERP
    mask_solo_erp = (
        (df["en_banco"] == 0) &
        (df["en_erp"]   == 1)
    )

    # Pendiente : en banco y ERP , pero sin confirmar en pasarela
    mask_sin_gw = (
        (df["en_banco"]  == 1) &
        (df["en_erp"]    == 1) &
        (df["en_gateway"]== 0) &
        (~mask_conciliada)
    )

    # Asignación de estados y tipo de inconsistencia
    df["estado_conciliacion"] = "PENDIENTE"
    df["tipo_diferencia"]     = None

    df.loc[mask_conciliada,  "estado_conciliacion"] = "CONCILIADA"
    df.loc[mask_com_mas,     "estado_conciliacion"] = "CON_DIFERENCIA"
    df.loc[mask_com_mas,     "tipo_diferencia"]     = "COMISION_COBRADA_DE_MAS"
    df.loc[mask_centavos,    "estado_conciliacion"] = "CON_DIFERENCIA"
    df.loc[mask_centavos,    "tipo_diferencia"]     = "DIFERENCIA_CENTAVOS"
    df.loc[mask_chargeback,  "estado_conciliacion"] = "PENDIENTE"
    df.loc[mask_chargeback,  "tipo_diferencia"]     = "CHARGEBACK_NO_REGISTRADO_ERP"
    df.loc[mask_solo_banco,  "tipo_diferencia"]     = "SOLO_EN_BANCO"
    df.loc[mask_solo_erp,    "tipo_diferencia"]     = "SOLO_EN_ERP"
    df.loc[mask_sin_gw,      "tipo_diferencia"]     = "PENDIENTE_SIN_GATEWAY"

    # Cuantificación del impacto económico de partidas abiertas o con novedades
    df["monto_en_riesgo"] = np.where(
        df["estado_conciliacion"] != "CONCILIADA",
        df["monto_bruto"].fillna(df["monto_bruto_erp"]).fillna(0).abs(),
        0.0
    ).round(2)

    # Cálculo del aging de partidas pendientes
    hoy = pd.Timestamp.today().normalize()
    fecha_ref = df["fecha_tx"].fillna(df["fecha_factura"])
    df["dias_antiguedad"] = (hoy - fecha_ref).dt.days

    log.info("  Clasificación completa")
    return df


def detectar_duplicados_gateway(gateway: pd.DataFrame) -> pd.DataFrame:
    dups = gateway.loc[gateway["es_duplicado"] == 1].copy()
    dups["tipo_diferencia"] = "DUPLICADO_GATEWAY"
    log.info("  Duplicados en pasarela detectados: %d filas", len(dups))
    return dups


def generar_tabla_maestra(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "tx_id", "invoice_number", "fecha_tx", "fecha_liquidacion", "fecha_factura",
        "gateway", "card_type", "monto_bruto_erp", "neto_esperado_erp",
        "monto_neto_banco", "diff_banco_erp", "comision_banco", "comision_esperada",
        "diff_comision", "ret_iva_banco", "ret_renta_banco", "client_name", "erp_module",
        "en_banco", "en_erp", "en_gateway", "estado_conciliacion", "tipo_diferencia",
        "monto_en_riesgo", "dias_antiguedad", "es_chargeback"
    ]
    cols_disponibles = [c for c in cols if c in df.columns]
    return df.loc[:,cols_disponibles].copy()


def imprimir_resumen(df: pd.DataFrame, duplicados: pd.DataFrame):
    total       = len(df)
    conciliadas = (df["estado_conciliacion"] == "CONCILIADA").sum()
    con_diff    = (df["estado_conciliacion"] == "CON_DIFERENCIA").sum()
    pendientes  = (df["estado_conciliacion"] == "PENDIENTE").sum()
    tasa        = conciliadas / total * 100 if total > 0 else 0

    monto_riesgo = df["monto_en_riesgo"].sum()
    monto_diff   = df.loc[df["estado_conciliacion"] == "CON_DIFERENCIA", "diff_banco_erp"].abs().sum()

    print()
    print("RESUMEN EJECUTIVO DE CONCILIACIÓN")
    print(f"Total transacciones analizadas : {total}")
    print(f"CONCILIADAS                 : {conciliadas} ({tasa:.1f}%)")
    print(f"CON DIFERENCIA              : {con_diff}")
    print(f"PENDIENTES                  : {pendientes}")
    print(f"DUPLICADOS EN PASARELA      : {len(duplicados)}")
    print(f"\nMonto total en riesgo          : $ {monto_riesgo:,.2f}")
    print(f"Diferencias de monto           : $ {monto_diff:,.2f}")

    print("\nDetalle por tipo de diferencia:")
    detalle = df["tipo_diferencia"].value_counts(dropna=False)
    for tipo, cnt in detalle.items():
        if pd.notna(tipo):       # type: ignore[arg-type]
            monto = df.loc[df["tipo_diferencia"] == tipo, "monto_en_riesgo"].sum()
            print(f"  {tipo}: {cnt} casos ($ {monto:,.2f})")

    print()
    print("\nDetalle por pasarela:")
    for gw in df["gateway"].dropna().unique():
        mask = df["gateway"] == gw
        conc = (df.loc[mask, "estado_conciliacion"] == "CONCILIADA").sum()
        tot  = mask.sum()
        print(f"  {gw}: {conc}/{tot} conciliadas ({conc/tot*100:.1f}%)" if tot > 0 else "")



def run_reconciler():
    bank, gateway, erp = run_etl()

    df = cruzar_banco_erp(bank, erp)
    df = agregar_gateway(df, gateway)
    df = clasificar_transacciones(df)

    duplicados = detectar_duplicados_gateway(gateway)
    tabla_maestra = generar_tabla_maestra(df)

    imprimir_resumen(tabla_maestra, duplicados)
    return tabla_maestra, duplicados
