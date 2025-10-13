from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    client.admin.command("ping")  # Verifica conexión
    print("✅ Conectado a MongoDB local")
except ConnectionFailure as e:
    print("❌ No se pudo conectar:", e)

db = client["Tienda"]           # Crea/selecciona base de datos
productos = db["productos"]     # Crea/selecciona colección
