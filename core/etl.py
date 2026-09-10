import logging
from pathlib import Path

import pandas as pd

from src.config import (
    BANK_FILE,
    COMISIONES_CONTRATO,
    ERP_FILE,
    GATEWAY_FILE,
    GATEWAY_NOMBRES,
    RET_IVA_PCT,
    RET_RENTA_PCT,
)

log =logging.getLogger(__name__)


# Funcion de limpieza del archivos csv

def load_bank_report(filepath: str | Path) -> pd.DataFrame :
    log.info("Cargando reporte del banco : %s",filepath)
    df =pd.read_csv(filepath)
    log.info("Numero total de registros cargados :%d",len(df))

    #Renombar Columnas

    df =df.rename(columns = {
        "transaction_id"   : "tx_id",
        "settlement_date"  : "fecha_liquidacion",
        "transaction_date" : "fecha_tx",
        "gross_amount"     : "monto_bruto",
        "commission_amount": "comision_banco",
        "vat_retention"    : "ret_iva_banco",
        "income_retention" : "ret_renta_banco",
        "net_amount"       : "monto_neto_banco",
        "status"           : "estado_banco",
        "chargeback_flag"  : "es_chargeback",

    })

    # Asignar tipos de datos correctos
    df["fecha_tx"] =pd.to_datetime( df["fecha_tx"])  # Columna fechas
    df["cardlast4"]= df["card_last4"].astype(str)    #Columna que contiene los  4 digitos de la tx

    # Normalizar textos

    df["gateway"] = df["gateway"].str.strip().str.lower().map(GATEWAY_NOMBRES).fillna(df["gateway"]).str.strip()
    df["estado_banco"] = df["estado_banco"].str.strip().str.upper()
    df["card_type"]    = df["card_type"].str.strip().str.upper()

    # --Calculo de retenciones esperadas segun el contrato

    df["comision_esperada"] = (
        df["gateway"].map(COMISIONES_CONTRATO)  # type: ignore[arg-type]
        * df["monto_bruto"].abs()
    ).round(2)

    df["ret_iva_esperada"]   = (df["monto_bruto"].abs() * RET_IVA_PCT).round(2)
    df["ret_renta_esperada"] = (df["monto_bruto"].abs() * RET_RENTA_PCT).round(2)
    df["neto_esperado_banco"] = (
        df["monto_bruto"].abs()
        - df["comision_esperada"]
        - df["ret_iva_esperada"]
        - df["ret_renta_esperada"]
    ).round(2)

    # ── Validación básica

    nulos = df["tx_id"].isna().sum()
    if nulos > 0:
        log.warning("  %d filas sin tx_id en bank_report", nulos)

    log.info("  Bank report limpio. Filas: %d | Chargebacks: %d",
             len(df), df["es_chargeback"].sum())


    return df


def load_gateway_report(filepath: str | Path) ->pd.DataFrame :
    log.info("Cargando reporte del pasarela : %s",filepath)
    df=pd.read_csv(filepath)
    log.info("Numero total de registros cargados :%d",len(df))

    #Renombar Columnas

    df = df.rename(columns={
        "transaction_id" : "tx_id",
        "transaction_date": "fecha_tx",
        "gateway_name"   : "gateway",
        "gross_amount"   : "monto_bruto_gw",
        "gateway_fee"    : "comision_gw",
        "net_to_bank"    : "neto_gw",
        "status"         : "estado_gw",
    })

    # Fechas
    df["fecha_tx"] = pd.to_datetime(df["fecha_tx"])

    #  Montos
    cols_monto = ["monto_bruto_gw", "comision_gw", "neto_gw"]
    df[cols_monto] = df[cols_monto].round(2)

    # Normalizar texto
    df["gateway"]    = df["gateway"].str.strip().str.lower().map(GATEWAY_NOMBRES).fillna(df["gateway"].str.strip())
    df["estado_gw"]  = df["estado_gw"].str.strip().str.upper()
    df["card_type"]  = df["card_type"].str.strip().str.upper()

    # Detectar duplicados
    df["tx_id_base"] = df["tx_id"].str.replace("-DUP", "", regex=False)
    df["es_duplicado"] = df.duplicated(subset=["tx_id_base"], keep=False).astype(int)
    n_dup = df["es_duplicado"].sum()

    if n_dup > 0 :
        log.warning("Gatweay contiene %d transacciones duplicadas",n_dup)

    return df


def load_erp_report (filepath: str | Path) ->pd.DataFrame:
    log.info("Cargando reporte del erp : %s",filepath)
    df=pd.read_csv(filepath)
    log.info("Numero total de registros cargados :%d",len(df))

    # Renombrar columnas
    df = df.rename(columns = {
        "transaction_id" : "tx_id",
        "invoice_date"   : "fecha_factura" ,
        "total_invoice"  : "monto_bruto_erp",
        "payment_method" : "gateway" ,
        "status"         : "estado_erp"

    })

    # Convertir tipo de datos
    df["fecha_factura"] = pd.to_datetime(df["fecha_factura"])
    df["client_ruc"] = df["client_ruc"].astype(str)

    #Normalizar Texto
    df["gateway"] =df["gateway"].str.strip().str.lower().map(GATEWAY_NOMBRES).fillna(df["gateway"].str.strip())
    df["card_type"] = df["card_type"].str.strip().str.upper()
    df["estado_erp"] = df["estado_erp"].str.strip().str.upper()


    ## Calculo de retenciones
    df["comision_esperada_erp"] = (
        df["gateway"].map (COMISIONES_CONTRATO)  # type: ignore[arg-type]
        * df["monto_bruto_erp"].abs()
    ).round(2)

    df["ret_iva_esperada_erp"] = (df["monto_bruto_erp"].abs()* RET_IVA_PCT).round(2)
    df["ret_renta_esperada_erp"] = (df["monto_bruto_erp"].abs() * RET_RENTA_PCT).round(2)
    df["neto_esperado_erp"] = (df["monto_bruto_erp"].abs() -
                               df["comision_esperada_erp"] -
                               df["ret_iva_esperada_erp"] -
                               df["ret_renta_esperada_erp"]
                               ).round(2)

    # Validacion de Nulos
    nulos = df["tx_id"].isnull().sum()
    if nulos > 0 :
        log.warning("Las filas con valores nulos son : %d", nulos)

    return df


def run_etl():
    log.info("INICIANDO ETL")

    bank    = load_bank_report(BANK_FILE)
    gateway = load_gateway_report(GATEWAY_FILE)
    erp     = load_erp_report(ERP_FILE)

    log.info("ETL COMPLETADO")

    return bank, gateway, erp


# Main

if __name__ == "__main__":
    bank, gateway, erp = run_etl()
    print(bank.head())
    print(gateway.head())
    print(erp.head())
