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
    # índice único por código
    col.create_index([("codigo", ASCENDING)], unique=True)
except Exception as e:
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
    e_codigo.delete(0, tk.END)
    e_nombre.delete(0, tk.END)
    e_categoria.delete(0, tk.END)
    e_precio.delete(0, tk.END)
    e_existencia.delete(0, tk.END)
    e_marca.delete(0, tk.END)

def doc_from_form(require_all=False):
    codigo = e_codigo.get().strip()
    nombre = e_nombre.get().strip()
    categoria = e_categoria.get().strip()
    precio = to_number(e_precio.get(), integer=False)
    existencia = to_number(e_existencia.get(), integer=True)
    marca = e_marca.get().strip()

    if require_all and (not codigo or not nombre):
        messagebox.showwarning("Validación", "Código y Nombre son obligatorios.")
        return None

    doc = {}
    if codigo: doc["codigo"] = codigo
    if nombre: doc["nombre"] = nombre
    if categoria: doc["categoria"] = categoria
    if precio is not None: doc["precio"] = precio
    if existencia is not None: doc["existencia"] = existencia
    if marca: doc["marca"] = marca
    return doc

def fill_form(doc):
    clear_form()
    e_codigo.insert(0, doc.get("codigo", ""))
    e_nombre.insert(0, doc.get("nombre", ""))
    e_categoria.insert(0, doc.get("categoria", ""))
    if "precio" in doc: e_precio.insert(0, str(doc["precio"]))
    if "existencia" in doc: e_existencia.insert(0, str(doc["existencia"]))
    e_marca.insert(0, doc.get("marca", ""))

def refresh_table(docs):
    for row in tree.get_children():
        tree.delete(row)
    for d in docs:
        tree.insert(
            "", tk.END,
            values=(
                d.get("codigo", ""),
                d.get("nombre", ""),
                d.get("categoria", ""),
                d.get("precio", ""),
                d.get("existencia", ""),
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
        messagebox.showerror("Insertar", "Código duplicado. Usa otro código.")
    except PyMongoError as e:
        messagebox.showerror("Insertar", f"Error MongoDB:\n{e}")

def cargar_por_codigo():
    codigo = e_codigo.get().strip()
    if not codigo:
        messagebox.showwarning("Cargar", "Ingresa el código del producto.")
        return
    doc = col.find_one({"codigo": codigo}, {"_id": 0})
    if not doc:
        messagebox.showinfo("Cargar", "No se encontró ese código.")
        return
    fill_form(doc)

def actualizar():
    codigo = e_codigo.get().strip()
    if not codigo:
        messagebox.showwarning("Actualizar", "Coloca el código a actualizar.")
        return
    nuevos = doc_from_form(require_all=False)
    if not nuevos or len(nuevos) == 1:
        messagebox.showwarning("Actualizar", "Ingresa al menos un campo a cambiar.")
        return
    try:
        res = col.update_one({"codigo": codigo}, {"$set": {k: v for k, v in nuevos.items() if k != "codigo"}})
        if res.matched_count == 0:
            messagebox.showinfo("Actualizar", "No se encontró ese código.")
        elif res.modified_count == 0:
            messagebox.showinfo("Actualizar", "No hubo cambios.")
        else:
            messagebox.showinfo("Actualizar", "Producto actualizado.")
        listar_todos()
    except PyMongoError as e:
        messagebox.showerror("Actualizar", f"Error MongoDB:\n{e}")

def eliminar():
    codigo = e_codigo.get().strip()
    if not codigo:
        messagebox.showwarning("Eliminar", "Coloca el código a eliminar.")
        return
    if messagebox.askyesno("Eliminar", f"¿Eliminar el código '{codigo}'?"):
        try:
            res = col.delete_one({"codigo": codigo})
            messagebox.showinfo("Eliminar", f"Eliminados: {res.deleted_count}")
            listar_todos()
        except PyMongoError as e:
            messagebox.showerror("Eliminar", f"Error MongoDB:\n{e}")

def listar_todos():
    cursor = col.find({}, {"_id": 0}).sort("nombre", ASCENDING)
    refresh_table(cursor)

def buscar():
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
        "codigo": vals[0], "nombre": vals[1], "categoria": vals[2],
        "precio": to_number(vals[3] if vals[3] != "" else None),
        "existencia": to_number(vals[4] if vals[4] != "" else None, integer=True),
        "marca": vals[5]
    }
    fill_form(doc)

# ---------- Interfaz ----------
root = tk.Tk()
root.title("Tienda - CRUD (MongoDB)")

frm = ttk.Frame(root, padding=10)
frm.grid(row=0, column=0, sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Formulario
ttk.Label(frm, text="Código de producto*").grid(row=0, column=0, sticky="w")
e_codigo = ttk.Entry(frm, width=24); e_codigo.grid(row=0, column=1, padx=5, pady=3)

ttk.Label(frm, text="Nombre*").grid(row=0, column=2, sticky="w")
e_nombre = ttk.Entry(frm, width=24); e_nombre.grid(row=0, column=3, padx=5, pady=3)

ttk.Label(frm, text="Categoría").grid(row=1, column=0, sticky="w")
e_categoria = ttk.Entry(frm, width=24); e_categoria.grid(row=1, column=1, padx=5, pady=3)

ttk.Label(frm, text="Precio").grid(row=1, column=2, sticky="w")
e_precio = ttk.Entry(frm, width=24); e_precio.grid(row=1, column=3, padx=5, pady=3)

ttk.Label(frm, text="En existencia").grid(row=2, column=0, sticky="w")
e_existencia = ttk.Entry(frm, width=24); e_existencia.grid(row=2, column=1, padx=5, pady=3)

ttk.Label(frm, text="Marca").grid(row=2, column=2, sticky="w")
e_marca = ttk.Entry(frm, width=24); e_marca.grid(row=2, column=3, padx=5, pady=3)

# Rango de precio
ttk.Label(frm, text="Precio mínimo").grid(row=3, column=0, sticky="w")
e_precio_min = ttk.Entry(frm, width=24); e_precio_min.grid(row=3, column=1, padx=5, pady=3)
ttk.Label(frm, text="Precio máximo").grid(row=3, column=2, sticky="w")
e_precio_max = ttk.Entry(frm, width=24); e_precio_max.grid(row=3, column=3, padx=5, pady=3)

# Botones
btns = ttk.Frame(frm)
btns.grid(row=4, column=0, columnspan=4, pady=(8, 10))
ttk.Button(btns, text="Insertar", command=insertar).grid(row=0, column=0, padx=5)
ttk.Button(btns, text="Cargar por código", command=cargar_por_codigo).grid(row=0, column=1, padx=5)
ttk.Button(btns, text="Actualizar", command=actualizar).grid(row=0, column=2, padx=5)
ttk.Button(btns, text="Eliminar", command=eliminar).grid(row=0, column=3, padx=5)
ttk.Button(btns, text="Buscar/Filtrar", command=buscar).grid(row=0, column=4, padx=5)
ttk.Button(btns, text="Listar todos", command=listar_todos).grid(row=0, column=5, padx=5)
ttk.Button(btns, text="Limpiar formulario", command=clear_form).grid(row=0, column=6, padx=5)

# Tabla
cols = ("codigo", "nombre", "categoria", "precio", "existencia", "marca")
tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
for c in cols:
    encabezado = "Código" if c == "codigo" else "En existencia" if c == "existencia" else c.capitalize()
    tree.heading(c, text=encabezado)
    tree.column(c, width=120, anchor="w")
tree.grid(row=5, column=0, columnspan=4, sticky="nsew")
frm.rowconfigure(5, weight=1)
frm.columnconfigure(3, weight=1)

ys = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
tree.configure(yscroll=ys.set)
ys.grid(row=5, column=4, sticky="ns")

tree.bind("<Double-1>", on_tree_double_click)

listar_todos()

root.mainloop()
