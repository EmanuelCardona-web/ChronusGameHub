import json
from typing import Optional, Union

from kafka import KafkaProducer

try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    producer = None
    print(f"Error al conectar con Kafka: {e}")

def send_audit_log(
    process_name: str,
    action: str,
    details: Union[str, dict],
) -> Optional[object]:
    if producer is None:
        return None

    message = {
        "process_name": process_name,
        "action": action,
        "details": details
    }
    return producer.send('app-logs', value=message)


if __name__ == "__main__":
    if producer is None:
        raise SystemExit("No se pudo conectar con Kafka en localhost:9092.")

    test_user = {
        "username": "usuario_prueba_kafka",
        "email": "usuario.prueba@example.com"
    }
    future = send_audit_log(
        "usuarios",
        "crear_usuario",
        test_user,
    )
    try:
        if future is None:
            raise SystemExit("No se pudo publicar el evento de prueba.")
        future.get(timeout=10)
        print("Evento de prueba de creación de usuario enviado a 'app-logs'.")
    finally:
        producer.close()