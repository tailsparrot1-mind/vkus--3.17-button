"""First-party local marketplace for demand and supply listings.

The initial implementation is intentionally local-first: records are stored in
SQLite on the user's machine. No fake remote listings or unconfigured network
connectors are presented as live data.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime


KINDS = ("Ищу", "Предлагаю")
CATEGORIES = (
    "Товары", "Услуги", "Работа", "Подряд и задачи",
    "Аренда", "Покупка", "Продажа", "Другое",
)


class MarketplaceStore:
    """SQLite repository with safe parameterized search and CRUD operations."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent / "data" / "marketplace.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK(kind IN ('Ищу','Предлагаю')),
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    city TEXT NOT NULL,
                    price TEXT NOT NULL DEFAULT '',
                    contact TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Активно'
                        CHECK(status IN ('Активно','Завершено','Архив')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_status ON marketplace_listings(status, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_city ON marketplace_listings(city)")

    @staticmethod
    def _validate(payload):
        required = ("kind", "category", "title", "description", "city")
        for key in required:
            if not str(payload.get(key, "")).strip():
                raise ValueError("Заполните обязательные поля: тип, категория, заголовок, описание и город.")
        if payload["kind"] not in KINDS:
            raise ValueError("Неизвестный тип объявления.")
        if payload["category"] not in CATEGORIES:
            raise ValueError("Выберите категорию из списка.")
        if len(payload["title"].strip()) > 120:
            raise ValueError("Заголовок не должен превышать 120 символов.")
        if len(payload["description"].strip()) > 5000:
            raise ValueError("Описание не должно превышать 5000 символов.")
        if len(payload["city"].strip()) > 80:
            raise ValueError("Название города слишком длинное.")

    def create(self, payload):
        self._validate(payload)
        now = datetime.now().isoformat(timespec="seconds")
        values = (
            payload["kind"].strip(), payload["category"].strip(),
            payload["title"].strip(), payload["description"].strip(),
            payload["city"].strip(), payload.get("price", "").strip(),
            payload.get("contact", "").strip(), payload.get("author", "").strip(),
            now, now,
        )
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO marketplace_listings
                (kind,category,title,description,city,price,contact,author,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?, 'Активно',?,?)
            """, values)
            return cur.lastrowid

    def update(self, listing_id, payload):
        self._validate(payload)
        now = datetime.now().isoformat(timespec="seconds")
        values = (
            payload["kind"].strip(), payload["category"].strip(),
            payload["title"].strip(), payload["description"].strip(),
            payload["city"].strip(), payload.get("price", "").strip(),
            payload.get("contact", "").strip(), payload.get("author", "").strip(),
            now, int(listing_id),
        )
        with self._connect() as conn:
            cur = conn.execute("""
                UPDATE marketplace_listings SET kind=?,category=?,title=?,description=?,
                city=?,price=?,contact=?,author=?,updated_at=? WHERE id=?
            """, values)
            if not cur.rowcount:
                raise LookupError("Объявление не найдено.")

    def set_status(self, listing_id, status):
        if status not in ("Активно", "Завершено", "Архив"):
            raise ValueError("Недопустимый статус объявления.")
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE marketplace_listings SET status=?,updated_at=? WHERE id=?",
                (status, datetime.now().isoformat(timespec="seconds"), int(listing_id)),
            )
            if not cur.rowcount:
                raise LookupError("Объявление не найдено.")

    def delete(self, listing_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM marketplace_listings WHERE id=?", (int(listing_id),))

    def get(self, listing_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM marketplace_listings WHERE id=?", (int(listing_id),)
            ).fetchone()
            return dict(row) if row else None

    def list_listings(self, query="", kind="Все типы", category="Все категории",
                      city="", status="Активно"):
        sql = "SELECT * FROM marketplace_listings WHERE 1=1"
        args = []
        if status != "Все статусы":
            sql += " AND status=?"
            args.append(status)
        if kind != "Все типы":
            sql += " AND kind=?"
            args.append(kind)
        if category != "Все категории":
            sql += " AND category=?"
            args.append(category)
        if city.strip():
            sql += " AND city LIKE ?"
            args.append("%" + city.strip() + "%")
        if query.strip():
            sql += " AND (title LIKE ? OR description LIKE ? OR city LIKE ? OR category LIKE ?)"
            term = "%" + query.strip() + "%"
            args.extend((term, term, term, term))
        sql += " ORDER BY CASE status WHEN 'Активно' THEN 0 WHEN 'Завершено' THEN 1 ELSE 2 END, created_at DESC"
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(sql, args).fetchall()]


def open_marketplace_window(parent):
    """Open the working local demand/supply board."""
    store = MarketplaceStore()
    win = tk.Toplevel(parent)
    win.title("Vkus — Биржа объявлений")
    win.configure(bg="#050b1b")
    win.geometry("1120x720")
    win.minsize(900, 600)
    win.transient(parent)

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Market.Treeview", background="#0a1731", fieldbackground="#0a1731",
                    foreground="#eaf1ff", rowheight=34, borderwidth=0,
                    font=("DejaVu Sans", 9))
    style.configure("Market.Treeview.Heading", background="#17264a",
                    foreground="#c99aff", font=("DejaVu Sans", 9, "bold"))
    style.map("Market.Treeview", background=[("selected", "#4b258b")])

    shell = tk.Frame(win, bg="#07122a", highlightbackground="#7136c3", highlightthickness=1)
    shell.pack(fill="both", expand=True, padx=10, pady=10)
    header = tk.Frame(shell, bg="#07122a")
    header.pack(fill="x", padx=18, pady=(16, 8))
    tk.Label(header, text="БИРЖА СПРОСА И ПРЕДЛОЖЕНИЙ", bg="#07122a",
             fg="#d18aff", font=("DejaVu Sans", 17, "bold")).pack(side="left")
    tk.Label(header, text="Локальная доска объявлений · данные хранятся на этом компьютере",
             bg="#07122a", fg="#8da4d3", font=("DejaVu Sans", 8)).pack(side="right")

    filters = tk.Frame(shell, bg="#07122a")
    filters.pack(fill="x", padx=18, pady=(4, 10))
    query_var = tk.StringVar()
    kind_var = tk.StringVar(value="Все типы")
    category_var = tk.StringVar(value="Все категории")
    city_var = tk.StringVar()
    status_var = tk.StringVar(value="Активно")
    def field(parent_frame, caption, widget, width=None):
        cell = tk.Frame(parent_frame, bg="#07122a")
        cell.pack(side="left", padx=(0, 10))
        tk.Label(cell, text=caption, bg="#07122a", fg="#91a8d7",
                 font=("DejaVu Sans", 8)).pack(anchor="w")
        widget.pack(fill="x", pady=(3, 0))
        return cell
    search = tk.Entry(filters, textvariable=query_var, bg="#0a1731", fg="#f0f4ff",
                      insertbackground="white", relief="flat", width=27,
                      font=("DejaVu Sans", 9))
    field(filters, "Поиск по объявлениям", search)
    field(filters, "Тип", ttk.Combobox(filters, textvariable=kind_var,
          values=("Все типы",) + KINDS, state="readonly", width=12))
    field(filters, "Категория", ttk.Combobox(filters, textvariable=category_var,
          values=("Все категории",) + CATEGORIES, state="readonly", width=19))
    field(filters, "Статус", ttk.Combobox(filters, textvariable=status_var,
          values=("Активно", "Завершено", "Архив", "Все статусы"),
          state="readonly", width=12))
    field(filters, "Город", tk.Entry(filters, textvariable=city_var, bg="#0a1731",
          fg="#f0f4ff", insertbackground="white", relief="flat", width=15,
          font=("DejaVu Sans", 9)))

    body = tk.Frame(shell, bg="#07122a")
    body.pack(fill="both", expand=True, padx=18, pady=(0, 10))
    columns = ("kind", "title", "category", "city", "price", "created_at")
    table = ttk.Treeview(body, columns=columns, show="headings", style="Market.Treeview")
    headings = {"kind":"Тип", "title":"Объявление", "category":"Категория",
                "city":"Город", "price":"Цена / бюджет", "created_at":"Создано"}
    widths = {"kind":95, "title":330, "category":145, "city":130, "price":130, "created_at":145}
    for key in columns:
        table.heading(key, text=headings[key])
        table.column(key, width=widths[key], anchor="w")
    scroll = ttk.Scrollbar(body, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    table.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    details = tk.Label(shell, text="Выберите объявление, чтобы увидеть описание и контакты.",
                       bg="#0a1731", fg="#9fb4df", justify="left", anchor="w",
                       padx=12, pady=9, font=("DejaVu Sans", 9))
    details.pack(fill="x", padx=18, pady=(0, 8))
    actions = tk.Frame(shell, bg="#07122a")
    actions.pack(fill="x", padx=18, pady=(0, 16))
    count_label = tk.Label(actions, text="", bg="#07122a", fg="#8fa5d4",
                           font=("DejaVu Sans", 8))
    count_label.pack(side="left")

    current = {}
    def selected_id():
        selection = table.selection()
        return int(selection[0]) if selection else None

    def show_details(_event=None):
        listing_id = selected_id()
        item = store.get(listing_id) if listing_id else None
        if not item:
            details.configure(text="Выберите объявление, чтобы увидеть описание и контакты.")
            return
        text = (f"{item['kind']} · {item['category']} · {item['status']}\n"
                f"{item['title']}\n{item['description']}\n"
                f"Город: {item['city']}   Бюджет/цена: {item['price'] or 'не указана'}\n"
                f"Автор: {item['author'] or 'не указан'}   Контакт: {item['contact'] or 'не указан'}")
        details.configure(text=text)

    def refresh(*_):
        rows = store.list_listings(query_var.get(), kind_var.get(), category_var.get(),
                                   city_var.get(), status_var.get())
        table.delete(*table.get_children())
        for item in rows:
            table.insert("", "end", iid=str(item["id"]), values=(
                item["kind"], item["title"], item["category"], item["city"],
                item["price"] or "—", item["created_at"][:16].replace("T", " "),
            ))
        count_label.configure(text=f"Объявлений: {len(rows)}")
        show_details()

    def edit_dialog(existing=None):
        dialog = tk.Toplevel(win)
        dialog.title("Новое объявление" if existing is None else "Редактировать объявление")
        dialog.configure(bg="#091735")
        dialog.transient(win)
        dialog.grab_set()
        dialog.geometry("610x600")
        form = tk.Frame(dialog, bg="#091735")
        form.pack(fill="both", expand=True, padx=22, pady=18)
        values = {
            "kind": tk.StringVar(value=(existing or {}).get("kind", "Ищу")),
            "category": tk.StringVar(value=(existing or {}).get("category", CATEGORIES[0])),
            "title": tk.StringVar(value=(existing or {}).get("title", "")),
            "city": tk.StringVar(value=(existing or {}).get("city", "")),
            "price": tk.StringVar(value=(existing or {}).get("price", "")),
            "author": tk.StringVar(value=(existing or {}).get("author", "")),
            "contact": tk.StringVar(value=(existing or {}).get("contact", "")),
        }
        def row(caption, widget):
            tk.Label(form, text=caption, bg="#091735", fg="#a9badc",
                     font=("DejaVu Sans", 9, "bold")).pack(anchor="w", pady=(9, 2))
            widget.pack(fill="x", ipady=5)
        row("Тип объявления *", ttk.Combobox(form, textvariable=values["kind"],
            values=KINDS, state="readonly"))
        row("Категория *", ttk.Combobox(form, textvariable=values["category"],
            values=CATEGORIES, state="readonly"))
        row("Заголовок *", tk.Entry(form, textvariable=values["title"], bg="#102044",
            fg="white", insertbackground="white", relief="flat"))
        row("Город *", tk.Entry(form, textvariable=values["city"], bg="#102044",
            fg="white", insertbackground="white", relief="flat"))
        row("Цена / бюджет", tk.Entry(form, textvariable=values["price"], bg="#102044",
            fg="white", insertbackground="white", relief="flat"))
        row("Автор / организация", tk.Entry(form, textvariable=values["author"], bg="#102044",
            fg="white", insertbackground="white", relief="flat"))
        row("Контакт (телефон, ссылка или ник)", tk.Entry(form, textvariable=values["contact"],
            bg="#102044", fg="white", insertbackground="white", relief="flat"))
        tk.Label(form, text="Описание *", bg="#091735", fg="#a9badc",
                 font=("DejaVu Sans", 9, "bold")).pack(anchor="w", pady=(9, 2))
        description = tk.Text(form, height=5, bg="#102044", fg="white",
                              insertbackground="white", relief="flat", wrap="word")
        description.pack(fill="both", expand=True)
        description.insert("1.0", (existing or {}).get("description", ""))
        def save():
            payload = {key: var.get().strip() for key, var in values.items()}
            payload["description"] = description.get("1.0", "end-1c").strip()
            try:
                if existing:
                    store.update(existing["id"], payload)
                else:
                    store.create(payload)
            except (ValueError, LookupError) as exc:
                messagebox.showwarning("Проверьте объявление", str(exc), parent=dialog)
                return
            dialog.destroy()
            refresh()
        buttons = tk.Frame(form, bg="#091735")
        buttons.pack(fill="x", pady=(12, 0))
        tk.Button(buttons, text="СОХРАНИТЬ", command=save, bg="#6330b4", fg="white",
                  activebackground="#8549df", relief="flat", padx=18, pady=8).pack(side="right")
        tk.Button(buttons, text="ОТМЕНА", command=dialog.destroy, bg="#17264a", fg="#dbe6ff",
                  relief="flat", padx=16, pady=8).pack(side="right", padx=8)

    def add():
        edit_dialog()
    def edit():
        listing_id = selected_id()
        item = store.get(listing_id) if listing_id else None
        if item:
            edit_dialog(item)
        else:
            messagebox.showinfo("Биржа", "Сначала выберите объявление.", parent=win)
    def change_status(status):
        listing_id = selected_id()
        if not listing_id:
            messagebox.showinfo("Биржа", "Сначала выберите объявление.", parent=win)
            return
        store.set_status(listing_id, status)
        refresh()
    def remove():
        listing_id = selected_id()
        if not listing_id:
            messagebox.showinfo("Биржа", "Сначала выберите объявление.", parent=win)
            return
        if messagebox.askyesno("Удалить объявление", "Удалить выбранное объявление без возможности восстановления?", parent=win):
            store.delete(listing_id)
            refresh()

    def action(text, command, color="#182b55"):
        tk.Button(actions, text=text, command=command, bg=color, fg="white",
                  activebackground="#7540c8", activeforeground="white",
                  relief="flat", bd=0, padx=12, pady=7,
                  font=("DejaVu Sans", 8, "bold"), cursor="hand2").pack(side="right", padx=(6,0))
    action("Удалить", remove, "#64263f")
    action("В архив", lambda: change_status("Архив"))
    action("Завершено", lambda: change_status("Завершено"))
    action("Редактировать", edit)
    action("+ Добавить объявление", add, "#6330b4")

    table.bind("<<TreeviewSelect>>", show_details)
    for var in (query_var, kind_var, category_var, city_var, status_var):
        var.trace_add("write", refresh)
    refresh()
    win.bind("<Escape>", lambda _e: win.destroy())
    return win
