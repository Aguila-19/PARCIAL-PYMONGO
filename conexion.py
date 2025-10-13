# ===========================================
# CRUD COMPLETO EN PyMongo
# Base de datos: Tienda
# Colección: Productos
# ===========================================

from pymongo import MongoClient
from pprint import pprint

# -----------------------------
# 1. Conexión a MongoDB local
# -----------------------------
try:
    cliente = MongoClient("mongodb://localhost:27017/")
    print("✅ Conexión exitosa a MongoDB")
except Exception as e:
    print("❌ Error al conectar:", e)
    exit()

# -----------------------------
# 2. Crear base de datos y colección
# -----------------------------
db = cliente["Tienda"]
productos = db["Productos"]
print("📦 Base de datos y colección creadas (o abiertas)")

# -----------------------------
# 3. Función para insertar datos (CREATE)
# -----------------------------
def crear_productos():
    datos = [
        {"sku": "PROD001", "nombre": "Laptop Lenovo", "categoria": "Computo", "precio": 750.00, "stock": 10, "marca": "Lenovo"},
        {"sku": "PROD002", "nombre": "Mouse inalámbrico", "categoria": "Accesorios", "precio": 12.99, "stock": 45, "marca": "Logitech"},
        {"sku": "PROD003", "nombre": "Teclado mecánico", "categoria": "Accesorios", "precio": 29.99, "stock": 30, "marca": "Redragon"},
        {"sku": "PROD004", "nombre": "Monitor 24 pulgadas", "categoria": "Pantallas", "precio": 120.50, "stock": 20, "marca": "HP"},
        {"sku": "PROD005", "nombre": "Memoria USB 64GB", "categoria": "Almacenamiento", "precio": 8.75, "stock": 60, "marca": "Kingston"},
    ]
    productos.insert_many(datos)
    print("✅ Productos insertados correctamente.")


# -----------------------------
# 4. Función para leer datos (READ)
# -----------------------------
def leer_productos():
    print("\n📄 Lista de productos:")
    for p in productos.find({}, {"_id": 0}):
        pprint(p)


# -----------------------------
# 5. Función para actualizar datos (UPDATE)
# -----------------------------
def actualizar_producto():
    criterio = {"sku": "PROD001"}
    nuevos_datos = {"$set": {"precio": 799.99, "stock": 8}}
    resultado = productos.update_one(criterio, nuevos_datos)
    if resultado.modified_count > 0:
        print("✅ Producto actualizado correctamente.")
    else:
        print("⚠️ No se encontró el producto para actualizar.")


# -----------------------------
# 6. Función para eliminar datos (DELETE)
# -----------------------------
def eliminar_producto():
    criterio = {"sku": "PROD005"}
    resultado = productos.delete_one(criterio)
    if resultado.deleted_count > 0:
        print("🗑️ Producto eliminado correctamente.")
    else:
        print("⚠️ No se encontró el producto para eliminar.")


# -----------------------------
# 7. Menú de opciones CRUD
# -----------------------------
def menu():
    while True:
        print("""
===============================
     MENÚ CRUD - PyMongo
===============================
1. Insertar productos
2. Mostrar productos
3. Actualizar producto
4. Eliminar producto
5. Salir
""")
        opcion = input("Elige una opción: ")

        if opcion == "1":
            crear_productos()
        elif opcion == "2":
            leer_productos()
        elif opcion == "3":
            actualizar_producto()
        elif opcion == "4":
            eliminar_producto()
        elif opcion == "5":
            print("👋 Cerrando conexión. ¡Hasta luego!")
            cliente.close()
            break
        else:
            print("❌ Opción no válida. Intenta de nuevo.")


# -----------------------------
# 8. Ejecutar menú principal
# -----------------------------
if __name__ == "__main__":
    menu()
