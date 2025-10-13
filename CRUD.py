# GUI CRUD + LOGIN (Tkinter + PyMongo + bcrypt) con "duplicado solo si es igual"
# BD: Tienda | Cols: Usuarios, Productos
# Campos del producto: codigo, nombre, categoria, precio, existencia, marca
# Único por huella (_fp) calculada con (codigo, nombre, categoria, precio, existencia, marca)

import os
import json
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError
import bcrypt

# ---------------- Conexión ----------------
def get_client():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")
    return client

client = None
db = None
col_users = None
col_prod = None

def conectar():
    """Conecta y asegura índices según la política de duplicados."""
    global client, db, col_users, col_prod
    client = get_client()
    db = client["Tienda"]
    col_users = db["Usuarios"]
    col_prod = db["Productos"]

    # Índices de usuarios
    col_users.create_index([("username", ASCENDING)], unique=True)

    # --- Política de unicidad para Productos ---
    # 1) Intentar borrar índice único antiguo en 'codigo' si existiera
    try:
        col_prod.drop_index("codigo_1")
    except Exception:
        pass

    # 2) Índice único por huella (_fp) => duplicado solo si todos los campos son idénticos
    col_prod.create_index([("_fp", ASCENDING)], unique=True)

# ---------------- Utilidades de hashing/huella ----------------
def producto_fingerprint(doc: dict) -> str:
    """Huella estable: si estos campos son idénticos, es duplicado."""
    keys = ["codigo", "nombre", "categoria", "precio", "existencia", "marca"]
    payload = {k: doc.get(k) for k in keys}
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

# ---------------- Utilidades de usuarios ----------------
def hash_password(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt())

def check_password(pw: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(pw.encode("utf-8"), hashed)

def ensure_admin():
    """Si no hay usuarios, pide crear el primero (admin)."""
    if col_users.count_documents({}) == 0:
        messagebox.showinfo("Usuarios", "No existen usuarios. Crea el primer usuario (admin).")
        open_register_window(initial_admin=True)

# ---------------- Ventana de Registro ----------------
def open_register_window(initial_admin=False):
    reg = tk.Toplevel()
    reg.title("Registrar usuario")
    reg.grab_set()

    ttk.Label(reg, text="Usuario *").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    e_user = ttk.Entry(reg, width=28); e_user.grid(row=0, column=1, padx=8, pady=6)

    ttk.Label(reg, text="Contraseña *").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    e_pass = ttk.Entry(reg, width=28, show="*"); e_pass.grid(row=1, column=1, padx=8, pady=6)

    ttk.Label(reg, text="Rol").grid(row=2, column=0, sticky="w", padx=8, pady=6)
    e_role = ttk.Combobox(reg, values=["admin", "vendedor", "visor"], state="readonly", width=25)
    e_role.set("admin" if initial_admin else "vendedor")
    e_role.grid(row=2, column=1, padx=8, pady=6)

    def registrar():
        user = e_user.get().strip()
        pw = e_pass.get().strip()
        role = e_role.get().strip() or "vendedor"
        if not user or not pw:
            messagebox.showwarning("Registro", "Usuario y contraseña son obligatorios.")
            return
        try:
            col_users.insert_one({"username": user, "password": hash_password(pw), "role": role})
            messagebox.showinfo("Registro", f"Usuario '{user}' creado.")
            reg.destroy()
        except DuplicateKeyError:
            messagebox.showerror("Registro", "Ese usuario ya existe.")
        except PyMongoError as e:
            messagebox.showerror("Registro", f"Error MongoDB:\n{e}")

    ttk.Button(reg, text="Registrar", command=registrar).grid(row=3, column=0, columnspan=2, pady=10)

# ---------------- Ventana de Login ----------------
def open_login_window(on_success):
    lw = tk.Toplevel()
    lw.title("Login - Tienda")
    lw.grab_set()

    ttk.Label(lw, text="Usuario").grid(row=0, column=0, sticky="w", padx=8, pady=6)
    e_user = ttk.Entry(lw, width=28); e_user.grid(row=0, column=1, padx=8, pady=6)

    ttk.Label(lw, text="Contraseña").grid(row=1, column=0, sticky="w", padx=8, pady=6)
    e_pass = ttk.Entry(lw, width=28, show="*"); e_pass.grid(row=1, column=1, padx=8, pady=6)

    def do_login():
        username = e_user.get().strip()
        password = e_pass.get().strip()
        if not username or not password:
            messagebox.showwarning("Login", "Completa usuario y contraseña.")
            return
        user = col_users.find_one({"username": username})
        if not user:
            messagebox.showerror("Login", "Usuario no existe.")
            return
        if not check_password(password, user["password"]):
            messagebox.showerror("Login", "Contraseña incorrecta.")
            return
        lw.destroy()
        on_success(user)

    ttk.Button(lw, text="Ingresar", command=do_login).grid(row=2, column=0, padx=8, pady=10)
    ttk.Button(lw, text="Registrar nuevo", command=lambda: open_register_window(False)).grid(row=2, column=1, padx=8, pady=10)

# ---------------- Utilidades CRUD ----------------
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
        tree.insert("", tk.END, values=(
            d.get("codigo", ""), d.get("nombre", ""), d.get("categoria", ""),
            d.get("precio", ""), d.get("existencia", ""), d.get("marca", "")
        ))

# ---------------- Acciones CRUD ----------------
def insertar():
    doc = doc_from_form(require_all=True)
    if not doc: return
    try:
        # huella antes de insertar (duplicado solo si todo igual)
        doc["_fp"] = producto_fingerprint(doc)
        col_prod.insert_one(doc)
        messagebox.showinfo("Insertar", "Producto insertado.")
        listar_todos()
    except DuplicateKeyError:
        messagebox.showerror("Insertar", "Producto duplicado (todos los campos iguales).")
    except PyMongoError as e:
        messagebox.showerror("Insertar", f"Error MongoDB:\n{e}")

def cargar_por_codigo():
    codigo = e_codigo.get().strip()
    if not codigo:
        messagebox.showwarning("Cargar", "Ingresa el código del producto.")
        return
    doc = col_prod.find_one({"codigo": codigo}, {"_id": 0})
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
        # Obtenemos un documento que coincida con ese código para recálculo
        actual = col_prod.find_one({"codigo": codigo}, {"_id": 0})
        if not actual:
            messagebox.showinfo("Actualizar", "No se encontró ese código.")
            return

        mezcla = {**actual, **{k: v for k, v in nuevos.items() if k != "codigo"}}

        # Si cambian campos que definen la huella, recalcúlala
        claves = {"codigo", "nombre", "categoria", "precio", "existencia", "marca"}
        if any(k in claves for k in nuevos.keys()):
            nuevos["_fp"] = producto_fingerprint(mezcla)

        res = col_prod.update_one({"codigo": codigo}, {"$set": {k: v for k, v in nuevos.items() if k != "codigo"}})
        if res.matched_count == 0:
            messagebox.showinfo("Actualizar", "No se encontró ese código.")
        elif res.modified_count == 0:
            messagebox.showinfo("Actualizar", "No hubo cambios.")
        else:
            messagebox.showinfo("Actualizar", "Producto actualizado.")
        listar_todos()
    except DuplicateKeyError:
        messagebox.showerror("Actualizar", "Producto duplicado (todos los campos iguales).")
    except PyMongoError as e:
        messagebox.showerror("Actualizar", f"Error MongoDB:\n{e}")

def eliminar():
    codigo = e_codigo.get().strip()
    if not codigo:
        messagebox.showwarning("Eliminar", "Coloca el código a eliminar.")
        return
    if messagebox.askyesno("Eliminar", f"¿Eliminar el código '{codigo}'?"):
        try:
            res = col_prod.delete_one({"codigo": codigo})
            messagebox.showinfo("Eliminar", f"Eliminados: {res.deleted_count}")
            listar_todos()
        except PyMongoError as e:
            messagebox.showerror("Eliminar", f"Error MongoDB:\n{e}")

def listar_todos():
    cursor = col_prod.find({}, {"_id": 0, "_fp": 0}).sort("nombre", ASCENDING)
    refresh_table(cursor)

def buscar():
    filtro = {}
    cat = e_categoria.get().strip()
    if cat: filtro["categoria"] = cat
    texto = e_nombre.get().strip()
    if texto: filtro["nombre"] = {"$regex": texto, "$options": "i"}
    pmin = to_number(e_precio_min.get(), integer=False)
    pmax = to_number(e_precio_max.get(), integer=False)
    if pmin is not None or pmax is not None:
        rango = {}
        if pmin is not None: rango["$gte"] = pmin
        if pmax is not None: rango["$lte"] = pmax
        filtro["precio"] = rango
    cursor = col_prod.find(filtro, {"_id": 0, "_fp": 0}).sort("nombre", ASCENDING)
    refresh_table(cursor)

def on_tree_double_click(event):
    item = tree.focus()
    if not item: return
    vals = tree.item(item, "values")
    doc = {
        "codigo": vals[0], "nombre": vals[1], "categoria": vals[2],
        "precio": to_number(vals[3] if vals[3] else None),
        "existencia": to_number(vals[4] if vals[4] else None, integer=True),
        "marca": vals[5]
    }
    fill_form(doc)

# ---------------- UI principal (se crea tras login) ----------------
root = tk.Tk()
root.title("Login requerido…")
root.withdraw()  # oculto hasta loguear

def launch_app(user_info):
    root.deiconify()
    root.title(f"Tienda - CRUD (Usuario: {user_info.get('username')} | Rol: {user_info.get('role','-')})")

    frm = ttk.Frame(root, padding=10); frm.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1); root.rowconfigure(0, weight=1)

    # Formulario
    ttk.Label(frm, text="Código de producto*").grid(row=0, column=0, sticky="w")
    global e_codigo, e_nombre, e_categoria, e_precio, e_existencia, e_marca
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

    # Rango de precio para búsquedas
    ttk.Label(frm, text="Precio mínimo").grid(row=3, column=0, sticky="w")
    global e_precio_min, e_precio_max
    e_precio_min = ttk.Entry(frm, width=24); e_precio_min.grid(row=3, column=1, padx=5, pady=3)
    ttk.Label(frm, text="Precio máximo").grid(row=3, column=2, sticky="w")
    e_precio_max = ttk.Entry(frm, width=24); e_precio_max.grid(row=3, column=3, padx=5, pady=3)

    # Botones
    btns = ttk.Frame(frm); btns.grid(row=4, column=0, columnspan=4, pady=(8, 10))
    ttk.Button(btns, text="Insertar", command=insertar).grid(row=0, column=0, padx=5)
    ttk.Button(btns, text="Cargar por código", command=cargar_por_codigo).grid(row=0, column=1, padx=5)
    ttk.Button(btns, text="Actualizar", command=actualizar).grid(row=0, column=2, padx=5)
    ttk.Button(btns, text="Eliminar", command=eliminar).grid(row=0, column=3, padx=5)
    ttk.Button(btns, text="Buscar/Filtrar", command=buscar).grid(row=0, column=4, padx=5)
    ttk.Button(btns, text="Listar todos", command=listar_todos).grid(row=0, column=5, padx=5)
    ttk.Button(btns, text="Limpiar formulario", command=clear_form).grid(row=0, column=6, padx=5)

    # Tabla
    cols = ("codigo", "nombre", "categoria", "precio", "existencia", "marca")
    global tree
    tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
    for c in cols:
        encabezado = "Código" if c == "codigo" else "En existencia" if c == "existencia" else c.capitalize()
        tree.heading(c, text=encabezado)
        tree.column(c, width=120, anchor="w")
    tree.grid(row=5, column=0, columnspan=4, sticky="nsew")
    frm.rowconfigure(5, weight=1); frm.columnconfigure(3, weight=1)

    ys = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
    tree.configure(yscroll=ys.set); ys.grid(row=5, column=4, sticky="ns")
    tree.bind("<Double-1>", on_tree_double_click)

    listar_todos()

# ---------------- Arranque ----------------
if __name__ == "__main__":
    try:
        conectar()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("MongoDB", f"No se pudo conectar:\n{e}")
        raise SystemExit

    # Ventana raíz oculta mientras gestionamos usuarios
    hidden = tk.Tk()
    hidden.withdraw()
    ensure_admin()
    open_login_window(launch_app)
    hidden.mainloop()
