import json
import os

from dotenv import load_dotenv
from kafka import KafkaConsumer
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("Configura SUPABASE_URL y SUPABASE_KEY en el archivo .env.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

consumer = KafkaConsumer(
    'app-logs',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print(">>> Consumidor Kafka iniciado. Esperando eventos para Supabase...")

for message in consumer:
    log_data = message.value
    print(f"\n[EVENTO RECIBIDO] -> {log_data}")

    details_val = log_data.get("details")
    if isinstance(details_val, (dict, list)):
        details_val = json.dumps(details_val, ensure_ascii=False)

    payload = {
        "process_name": log_data.get("process_name"),
        "action": log_data.get("action"),
        "details": details_val
    }

    response = supabase.table("app_logs").insert(payload).execute()
    print(f"[GUARDADO EN SUPABASE] -> ID generado: {response.data}")
