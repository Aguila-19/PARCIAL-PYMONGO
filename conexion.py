import os
import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

# ---------- Conexión a MongoDB ----------
def get_client():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")  # valida conexión
    return client

try:
    client = get_client()
    db = client["Tienda"]
    col = db["Productos"]
    # índice único por SKU
    col.create_index([("sku", ASCENDING)], unique=True)
except Exception as e:
    # Si falla aquí, cierra GUI luego de mostrar error
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Conexión MongoDB", f"No se pudo conectar:\n{e}")
    raise SystemExit

# ---------- Utilidades ----------
def to_number(value, integer=False):
    v = str(value).strip()
    if v == "":
        return None
    try:
        return int(v) if integer else float(v)
    except ValueError:
        return None

def clear_form():
    e_sku.delete(0, tk.END)
    e_nombre.delete(0, tk.END)
    e_categoria.delete(0, tk.END)
    e_precio.delete(0, tk.END)
    e_stock.delete(0, tk.END)
    e_marca.delete(0, tk.END)

def doc_from_form(require_all=False):
    sku = e_sku.get().strip()
    nombre = e_nombre.get().strip()
    categoria = e_categoria.get().strip()
    precio = to_number(e_precio.get(), integer=False)
    stock = to_number(e_stock.get(), integer=True)
    marca = e_marca.get().strip()

    if require_all and (not sku or not nombre):
        messagebox.showwarning("Validación", "SKU y Nombre son obligatorios.")
        return None

    doc = {}
    if sku: doc["sku"] = sku
    if nombre: doc["nombre"] = nombre
    if categoria: doc["categoria"] = categoria
    if precio is not None: doc["precio"] = precio
    if stock is not None: doc["stock"] = stock
    if marca: doc["marca"] = marca
    return doc

def fill_form(doc):
    clear_form()
    e_sku.insert(0, doc.get("sku", ""))
    e_nombre.insert(0, doc.get("nombre", ""))
    e_categoria.insert(0, doc.get("categoria", ""))
    if "precio" in doc: e_precio.insert(0, str(doc["precio"]))
    if "stock" in doc: e_stock.insert(0, str(doc["stock"]))
    e_marca.insert(0, doc.get("marca", ""))

def refresh_table(docs):
    for row in tree.get_children():
        tree.delete(row)
    for d in docs:
        tree.insert(
            "", tk.END,
            values=(
                d.get("sku", ""),
                d.get("nombre", ""),
                d.get("categoria", ""),
                d.get("precio", ""),
                d.get("stock", ""),
                d.get("marca", "")
            )
        )

# ---------- Acciones CRUD ----------
def insertar():
    doc = doc_from_form(require_all=True)
    if not doc: return
    try:
        col.insert_one(doc)
        messagebox.showinfo("Insertar", "Producto insertado.")
        listar_todos()
    except DuplicateKeyError:
        messagebox.showerror("Insertar", "SKU duplicado. Usa otro SKU.")
    except PyMongoError as e:
        messagebox.showerror("Insertar", f"Error MongoDB:\n{e}")

def cargar_por_sku():
    sku = e_sku.get().strip()
    if not sku:
        messagebox.showwarning("Cargar", "Ingresa el SKU.")
        return
    doc = col.find_one({"sku": sku}, {"_id": 0})
    if not doc:
        messagebox.showinfo("Cargar", "No se encontró ese SKU.")
        return
    fill_form(doc)

def actualizar():
    sku = e_sku.get().strip()
    if not sku:
        messagebox.showwarning("Actualizar", "Coloca el SKU a actualizar.")
        return
    nuevos = doc_from_form(require_all=False)
    if not nuevos or len(nuevos) == 1:  # sólo trae SKU
        messagebox.showwarning("Actualizar", "Ingresa al menos un campo a cambiar.")
        return
    try:
        res = col.update_one({"sku": sku}, {"$set": {k: v for k, v in nuevos.items() if k != "sku"}})
        if res.matched_count == 0:
            messagebox.showinfo("Actualizar", "No se encontró ese SKU.")
        elif res.modified_count == 0:
            messagebox.showinfo("Actualizar", "No hubo cambios (mismos valores).")
        else:
            messagebox.showinfo("Actualizar", "Producto actualizado.")
        listar_todos()
    except PyMongoError as e:
        messagebox.showerror("Actualizar", f"Error MongoDB:\n{e}")

def eliminar():
    sku = e_sku.get().strip()
    if not sku:
        messagebox.showwarning("Eliminar", "Coloca el SKU a eliminar.")
        return
    if messagebox.askyesno("Eliminar", f"¿Eliminar el SKU '{sku}'?"):
        try:
            res = col.delete_one({"sku": sku})
            messagebox.showinfo("Eliminar", f"Eliminados: {res.deleted_count}")
            listar_todos()
        except PyMongoError as e:
            messagebox.showerror("Eliminar", f"Error MongoDB:\n{e}")

def listar_todos():
    cursor = col.find({}, {"_id": 0}).sort("nombre", ASCENDING)
    refresh_table(cursor)

def buscar():
    # Filtros simples: categoría y texto en nombre, + rango de precio opcional
    filtro = {}
    cat = e_categoria.get().strip()
    if cat:
        filtro["categoria"] = cat
    texto = e_nombre.get().strip()
    if texto:
        filtro["nombre"] = {"$regex": texto, "$options": "i"}
    pmin = to_number(e_precio_min.get(), integer=False)
    pmax = to_number(e_precio_max.get(), integer=False)
    if pmin is not None or pmax is not None:
        rango = {}
        if pmin is not None: rango["$gte"] = pmin
        if pmax is not None: rango["$lte"] = pmax
        filtro["precio"] = rango

    cursor = col.find(filtro, {"_id": 0}).sort("nombre", ASCENDING)
    refresh_table(cursor)

def on_tree_double_click(event):
    item = tree.focus()
    if not item: return
    vals = tree.item(item, "values")
    doc = {
        "sku": vals[0], "nombre": vals[1], "categoria": vals[2],
        "precio": to_number(vals[3] if vals[3] != "" else None),
        "stock": to_number(vals[4] if vals[4] != "" else None, integer=True),
        "marca": vals[5]
    }
    fill_form(doc)

# ---------- Interfaz (Tkinter) ----------
root = tk.Tk()
root.title("Tienda - CRUD (MongoDB)")

frm = ttk.Frame(root, padding=10)
frm.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Formulario
ttk.Label(frm, text="SKU*").grid(row=0, column=0, sticky="w")
e_sku = ttk.Entry(frm, width=24); e_sku.grid(row=0, column=1, padx=5, pady=3)

ttk.Label(frm, text="Nombre*").grid(row=0, column=2, sticky="w")
e_nombre = ttk.Entry(frm, width=24); e_nombre.grid(row=0, column=3, padx=5, pady=3)

ttk.Label(frm, text="Categoría").grid(row=1, column=0, sticky="w")
e_categoria = ttk.Entry(frm, width=24); e_categoria.grid(row=1, column=1, padx=5, pady=3)

ttk.Label(frm, text="Precio").grid(row=1, column=2, sticky="w")
e_precio = ttk.Entry(frm, width=24); e_precio.grid(row=1, column=3, padx=5, pady=3)

ttk.Label(frm, text="Stock").grid(row=2, column=0, sticky="w")
e_stock = ttk.Entry(frm, width=24); e_stock.grid(row=2, column=1, padx=5, pady=3)

ttk.Label(frm, text="Marca").grid(row=2, column=2, sticky="w")
e_marca = ttk.Entry(frm, width=24); e_marca.grid(row=2, column=3, padx=5, pady=3)

# Rango de precio para búsquedas
ttk.Label(frm, text="P. mín").grid(row=3, column=0, sticky="w")
e_precio_min = ttk.Entry(frm, width=24); e_precio_min.grid(row=3, column=1, padx=5, pady=3)
ttk.Label(frm, text="P. máx").grid(row=3, column=2, sticky="w")
e_precio_max = ttk.Entry(frm, width=24); e_precio_max.grid(row=3, column=3, padx=5, pady=3)

# Botones
btns = ttk.Frame(frm)
btns.grid(row=4, column=0, columnspan=4, pady=(8, 10))
ttk.Button(btns, text="Insertar", command=insertar).grid(row=0, column=0, padx=5)
ttk.Button(btns, text="Cargar por SKU", command=cargar_por_sku).grid(row=0, column=1, padx=5)
ttk.Button(btns, text="Actualizar", command=actualizar).grid(row=0, column=2, padx=5)
ttk.Button(btns, text="Eliminar", command=eliminar).grid(row=0, column=3, padx=5)
ttk.Button(btns, text="Buscar/Filtrar", command=buscar).grid(row=0, column=4, padx=5)
ttk.Button(btns, text="Listar todos", command=listar_todos).grid(row=0, column=5, padx=5)
ttk.Button(btns, text="Limpiar formulario", command=clear_form).grid(row=0, column=6, padx=5)

# Tabla
cols = ("sku", "nombre", "categoria", "precio", "stock", "marca")
tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
for c in cols:
    tree.heading(c, text=c.capitalize())
    tree.column(c, width=120, anchor="w")
tree.grid(row=5, column=0, columnspan=4, sticky="nsew")
frm.rowconfigure(5, weight=1)
frm.columnconfigure(3, weight=1)

ys = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
tree.configure(yscroll=ys.set)
ys.grid(row=5, column=4, sticky="ns")

tree.bind("<Double-1>", on_tree_double_click)

# Carga inicial
listar_todos()

root.mainloop()
