from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT /"data"/"raw"
PROCESSED_DIR = ROOT/"data"/"processed"

BANK_FILE = RAW_DIR/"bank_report.csv"
ERP_FILE= RAW_DIR/"erp_invoices.csv"
GATEWAY_FILE = RAW_DIR/"gateway_report.csv"

RECONCILIATION_OUTPUT_FILE = PROCESSED_DIR / "reconciliation_output.csv"
DUPLICADOS_GATEWAY_FILE = PROCESSED_DIR / "duplicados_gateway.csv"
DB_PATH = PROCESSED_DIR / "conciliador.db"

LOG_DIR = ROOT/"log"
LOG_FILE = LOG_DIR/"process.log"




## CONSTANTES DEL NEGOCIO

RET_IVA_PCT: float =0.045
RET_RENTA_PCT: float =0.010

TOLERANCIA_CENTAVOS: float = 0.05

# Comisiones cobradas por cada pasarela segun contrato

COMISIONES_CONTRATO: dict[str, float]={
    "Datafast":0.035,
    "Medianet":0.032,
    "PayPhone":0.038
}

# Mapeo de Nombres de pasarela para normalizar

GATEWAY_NOMBRES: dict[str, str] = {
    "datafast":"Datafast",
    "medianet":"Medianet",
    "payphone":"PayPhone"
}
