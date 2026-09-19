# -*- coding: utf-8 -*-
"""
Horria Lab
-----------
برنامج تسجيل توريدات المصنع وتحديد القبول/الرفض - متصل بجوجل شيت
Developed By Eng. Ahmed Adel

طريقة التشغيل والإعداد بالتفصيل في README.md
"""

import os
import json
from datetime import datetime, date

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from sheets_manager import SheetsManager
import pdf_reports
from master_data import SUPPLIERS_BY_TYPE, PRODUCTS_BY_SUPPLIER

APP_TITLE = "Horria Lab"
DEVELOPER = "Developed By Eng. Ahmed Adel"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

INCOMING_TYPES = ["خامات رئيسية", "خامات تعبئة وتغليف", "CF"]
STATUSES = ["مقبول", "مرفوض"]
UNITS = ["كرتونة", "كيس", "طن", "كيلوجرام", "لتر", "برميل", "علبة", "شيكارة", "وحدة"]


# ---------------------------------------------------------------------------
# Combobox قابل للفلترة بالكتابة (autocomplete)
# ---------------------------------------------------------------------------
class FilterCombobox(ttk.Combobox):
    def __init__(self, master, all_values_getter=None, **kwargs):
        super().__init__(master, **kwargs)
        self.all_values_getter = all_values_getter or (lambda: [])
        self._full_list = []
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Button-1>", lambda e: self.refresh_values())

    def refresh_values(self):
        self._full_list = self.all_values_getter()
        self["values"] = self._full_list

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        typed = self.get().strip()
        if not self._full_list:
            self._full_list = self.all_values_getter()
        if typed == "":
            filtered = self._full_list
        else:
            filtered = [v for v in self._full_list if typed in v]
        self["values"] = filtered
        # اظهار القائمة المنسدلة تلقائيًا
        if filtered:
            self.event_generate("<Down>") if not self["values"] else None


class HorriaLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} — {DEVELOPER}")
        self.geometry("1000x700")
        self.configure(bg="#F4F6F5")

        self.sm = SheetsManager()
        self.connected = False
        self.records_cache = []

        self._build_style()
        self._build_layout()
        self._try_auto_connect()

    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", background="#F4F6F5", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1B4332", background="#F4F6F5")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#666666", background="#F4F6F5")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    def _build_layout(self):
        header = tk.Frame(self, bg="#1B4332", height=70)
        header.pack(fill="x", side="top")
        tk.Label(header, text=APP_TITLE, font=("Segoe UI", 20, "bold"), fg="white", bg="#1B4332").pack(pady=(10, 0))
        tk.Label(header, text=DEVELOPER, font=("Segoe UI", 9), fg="#CFE8DB", bg="#1B4332").pack()

        self.status_label = tk.Label(self, text="غير متصل بجوجل شيت", fg="#C62828", bg="#F4F6F5", font=("Segoe UI", 9))
        self.status_label.pack(anchor="e", padx=10, pady=(4, 0))

        settings_btn = ttk.Button(self, text="⚙ إعدادات الاتصال بجوجل شيت", command=self.open_settings)
        settings_btn.pack(anchor="e", padx=10, pady=4)

        form = ttk.LabelFrame(self, text="تسجيل توريد جديد")
        form.pack(fill="x", padx=15, pady=10)

        # نوع الوارد
        ttk.Label(form, text="نوع الوارد:").grid(row=0, column=3, sticky="e", padx=8, pady=6)
        self.type_cb = ttk.Combobox(form, values=INCOMING_TYPES, state="readonly", width=25)
        self.type_cb.grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.type_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_supplier_list())

        # التاريخ
        ttk.Label(form, text="التاريخ (YYYY-MM-DD):").grid(row=0, column=1, sticky="e", padx=8, pady=6)
        self.date_entry = ttk.Entry(form, width=15)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        # المورد
        ttk.Label(form, text="اسم المورد (اكتب أول حرفين للفلترة):").grid(row=1, column=3, sticky="e", padx=8, pady=6)
        self.supplier_cb = FilterCombobox(form, all_values_getter=self._get_suppliers, width=25)
        self.supplier_cb.grid(row=1, column=2, sticky="w", padx=8, pady=6)
        self.supplier_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_product_list())

        # المنتج
        ttk.Label(form, text="اسم المنتج (اكتب أول حرفين للفلترة):").grid(row=1, column=1, sticky="e", padx=8, pady=6)
        self.product_cb = FilterCombobox(form, all_values_getter=self._get_products, width=25)
        self.product_cb.grid(row=1, column=0, sticky="w", padx=8, pady=6)

        # الحالة
        ttk.Label(form, text="الحالة:").grid(row=2, column=3, sticky="e", padx=8, pady=6)
        status_frame = tk.Frame(form, bg="#F4F6F5")
        status_frame.grid(row=2, column=2, sticky="w", padx=8, pady=6)
        self.status_var = tk.StringVar(value="مقبول")
        ttk.Radiobutton(status_frame, text="مقبول", variable=self.status_var, value="مقبول").pack(side="right", padx=4)
        ttk.Radiobutton(status_frame, text="مرفوض", variable=self.status_var, value="مرفوض").pack(side="right", padx=4)

        # الكمية والوحدة
        ttk.Label(form, text="الكمية:").grid(row=2, column=1, sticky="e", padx=8, pady=6)
        self.quantity_entry = ttk.Entry(form, width=12)
        self.quantity_entry.grid(row=2, column=0, sticky="w", padx=(8, 90), pady=6)
        self.unit_cb = ttk.Combobox(form, values=UNITS, state="readonly", width=10)
        self.unit_cb.set(UNITS[0])
        self.unit_cb.grid(row=2, column=0, sticky="e", padx=8, pady=6)

        # ملاحظات
        ttk.Label(form, text="ملاحظات:").grid(row=3, column=1, sticky="e", padx=8, pady=6)
        self.notes_entry = ttk.Entry(form, width=25)
        self.notes_entry.grid(row=3, column=0, sticky="w", padx=8, pady=6)

        save_btn = ttk.Button(form, text="💾 حفظ التوريد", style="Accent.TButton", command=self.save_record)
        save_btn.grid(row=4, column=0, columnspan=4, pady=10)

        # جدول عرض
        table_frame = ttk.LabelFrame(self, text="سجلات اليوم")
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("التاريخ", "نوع الوارد", "اسم المورد", "اسم المنتج", "الكمية", "الوحدة", "الحالة", "ملاحظات")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", width=140)
        self.tree.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        refresh_btn = ttk.Button(self, text="🔄 تحديث السجلات", command=self.refresh_table)
        refresh_btn.pack(pady=4)

        # أزرار التقارير
        reports_frame = ttk.LabelFrame(self, text="التقارير")
        reports_frame.pack(fill="x", padx=15, pady=10)

        ttk.Button(reports_frame, text="📄 تقرير اليوم PDF", command=self.generate_daily_report).pack(side="right", padx=10, pady=10)
        ttk.Button(reports_frame, text="📊 تقرير شهري (رفض) PDF", command=self.generate_monthly_report).pack(side="right", padx=10, pady=10)
        ttk.Button(reports_frame, text="🔍 بحث عن مورد (تقرير PDF)", command=self.generate_supplier_report).pack(side="right", padx=10, pady=10)

    # ------------------------------------------------------------------
    def _get_suppliers(self):
        incoming_type = self.type_cb.get() or None
        master_list = set(SUPPLIERS_BY_TYPE.get(incoming_type, [])) if incoming_type else set()
        sheet_list = set(self.sm.get_unique_suppliers(incoming_type=incoming_type)) if self.connected else set()
        return sorted(master_list | sheet_list)

    def _get_products(self):
        supplier = self.supplier_cb.get() or None
        incoming_type = self.type_cb.get() or None
        master_list = set(PRODUCTS_BY_SUPPLIER.get(supplier, [])) if supplier else set()
        sheet_list = set(
            self.sm.get_unique_products(supplier=supplier, incoming_type=incoming_type)
        ) if self.connected else set()
        return sorted(master_list | sheet_list)

    def _refresh_supplier_list(self):
        self.supplier_cb.refresh_values()

    def _refresh_product_list(self):
        self.product_cb.refresh_values()

    # ------------------------------------------------------------------
    def _try_auto_connect(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._connect(cfg.get("credentials_path", ""), cfg.get("sheet_id", ""), cfg.get("worksheet_name", "بيانات"))
            except Exception:
                pass

    def _connect(self, creds_path, sheet_id, worksheet_name):
        if not creds_path or not sheet_id:
            return
        try:
            self.sm.connect(creds_path, sheet_id, worksheet_name)
            self.connected = True
            self.status_label.config(text="متصل بجوجل شيت ✅", fg="#2E7D32")
            self.refresh_table()
        except Exception as e:
            self.connected = False
            self.status_label.config(text="فشل الاتصال بجوجل شيت", fg="#C62828")
            messagebox.showerror("خطأ في الاتصال", f"تعذر الاتصال بجوجل شيت:\n{e}")

    def open_settings(self):
        win = tk.Toplevel(self)
        win.title("إعدادات الاتصال بجوجل شيت")
        win.geometry("520x260")
        win.configure(bg="#F4F6F5")

        cfg = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

        ttk.Label(win, text="ملف اعتماد Google (JSON):").pack(anchor="e", padx=10, pady=(15, 2))
        creds_frame = tk.Frame(win, bg="#F4F6F5")
        creds_frame.pack(fill="x", padx=10)
        creds_var = tk.StringVar(value=cfg.get("credentials_path", ""))
        creds_entry = ttk.Entry(creds_frame, textvariable=creds_var, width=50)
        creds_entry.pack(side="right", padx=4)

        def browse_creds():
            path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            if path:
                creds_var.set(path)

        ttk.Button(creds_frame, text="استعراض", command=browse_creds).pack(side="right")

        ttk.Label(win, text="معرّف الشيت (Sheet ID):").pack(anchor="e", padx=10, pady=(15, 2))
        sheet_id_var = tk.StringVar(value=cfg.get("sheet_id", ""))
        ttk.Entry(win, textvariable=sheet_id_var, width=55).pack(anchor="e", padx=10)

        ttk.Label(win, text="اسم الشيت الفرعي (Worksheet):").pack(anchor="e", padx=10, pady=(15, 2))
        ws_var = tk.StringVar(value=cfg.get("worksheet_name", "بيانات"))
        ttk.Entry(win, textvariable=ws_var, width=30).pack(anchor="e", padx=10)

        def save_and_connect():
            new_cfg = {
                "credentials_path": creds_var.get().strip(),
                "sheet_id": sheet_id_var.get().strip(),
                "worksheet_name": ws_var.get().strip() or "بيانات",
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_cfg, f, ensure_ascii=False, indent=2)
            self._connect(new_cfg["credentials_path"], new_cfg["sheet_id"], new_cfg["worksheet_name"])
            win.destroy()

        ttk.Button(win, text="حفظ واتصال", style="Accent.TButton", command=save_and_connect).pack(pady=20)

    # ------------------------------------------------------------------
    def save_record(self):
        if not self.connected:
            messagebox.showwarning("غير متصل", "من فضلك قم بإعداد الاتصال بجوجل شيت أولاً.")
            return

        date_str = self.date_entry.get().strip()
        incoming_type = self.type_cb.get().strip()
        supplier = self.supplier_cb.get().strip()
        product = self.product_cb.get().strip()
        status = self.status_var.get()
        notes = self.notes_entry.get().strip()
        quantity = self.quantity_entry.get().strip()
        unit = self.unit_cb.get().strip()

        if not (date_str and incoming_type and supplier and product):
            messagebox.showwarning("بيانات ناقصة", "من فضلك املأ: التاريخ، نوع الوارد، المورد، المنتج.")
            return

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("تاريخ غير صحيح", "صيغة التاريخ يجب أن تكون YYYY-MM-DD")
            return

        try:
            self.sm.append_record(date_str, incoming_type, supplier, product, status, notes, quantity, unit)
            messagebox.showinfo("تم", "تم حفظ التوريد بنجاح ✅")
            self.product_cb.set("")
            self.notes_entry.delete(0, "end")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر حفظ السجل:\n{e}")

    # ------------------------------------------------------------------
    def refresh_table(self):
        if not self.connected:
            return
        try:
            self.records_cache = self.sm.get_all_records()
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر تحميل السجلات:\n{e}")
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        today_str = date.today().isoformat()
        for r in self.records_cache:
            if str(r.get("التاريخ", "")).strip() == today_str:
                self.tree.insert("", "end", values=(
                    r.get("التاريخ", ""), r.get("نوع الوارد", ""), r.get("اسم المورد", ""),
                    r.get("اسم المنتج", ""), r.get("الكمية", ""), r.get("الوحدة", ""),
                    r.get("الحالة", ""), r.get("ملاحظات", ""),
                ))

    # ------------------------------------------------------------------
    def _ask_save_path(self, default_name):
        return filedialog.asksaveasfilename(
            defaultextension=".pdf", initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")],
        )

    def generate_daily_report(self):
        if not self.connected:
            messagebox.showwarning("غير متصل", "قم بإعداد الاتصال بجوجل شيت أولاً.")
            return
        date_str = self.date_entry.get().strip() or date.today().isoformat()
        out_path = self._ask_save_path(f"تقرير_يومي_{date_str}.pdf")
        if not out_path:
            return
        try:
            records = self.sm.get_all_records()
            pdf_reports.daily_report(records, date_str, out_path)
            messagebox.showinfo("تم", f"تم إنشاء التقرير:\n{out_path}")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def generate_monthly_report(self):
        if not self.connected:
            messagebox.showwarning("غير متصل", "قم بإعداد الاتصال بجوجل شيت أولاً.")
            return
        win = tk.Toplevel(self)
        win.title("تقرير شهري")
        win.geometry("300x160")
        win.configure(bg="#F4F6F5")
        ttk.Label(win, text="السنة:").pack(pady=(15, 2))
        year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(win, textvariable=year_var).pack()
        ttk.Label(win, text="الشهر (1-12):").pack(pady=(10, 2))
        month_var = tk.StringVar(value=str(date.today().month))
        ttk.Entry(win, textvariable=month_var).pack()

        def do_generate():
            try:
                year = int(year_var.get())
                month = int(month_var.get())
            except ValueError:
                messagebox.showwarning("خطأ", "أدخل سنة وشهر صحيحين")
                return
            out_path = self._ask_save_path(f"تقرير_شهري_رفض_{year}-{month:02d}.pdf")
            if not out_path:
                return
            try:
                records = self.sm.get_all_records()
                pdf_reports.monthly_rejected_report(records, year, month, out_path)
                messagebox.showinfo("تم", f"تم إنشاء التقرير:\n{out_path}")
                win.destroy()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        ttk.Button(win, text="إنشاء التقرير", style="Accent.TButton", command=do_generate).pack(pady=15)

    def generate_supplier_report(self):
        if not self.connected:
            messagebox.showwarning("غير متصل", "قم بإعداد الاتصال بجوجل شيت أولاً.")
            return
        win = tk.Toplevel(self)
        win.title("بحث عن مورد")
        win.geometry("320x150")
        win.configure(bg="#F4F6F5")
        ttk.Label(win, text="اسم المورد (كامل أو جزء منه):").pack(pady=(15, 2))
        supplier_var = tk.StringVar()
        ttk.Entry(win, textvariable=supplier_var).pack()

        def do_generate():
            supplier = supplier_var.get().strip()
            if not supplier:
                messagebox.showwarning("خطأ", "أدخل اسم المورد")
                return
            out_path = self._ask_save_path(f"تقرير_مورد_{supplier}.pdf")
            if not out_path:
                return
            try:
                records = self.sm.get_all_records()
                pdf_reports.supplier_report(records, supplier, out_path)
                messagebox.showinfo("تم", f"تم إنشاء التقرير:\n{out_path}")
                win.destroy()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        ttk.Button(win, text="إنشاء التقرير", style="Accent.TButton", command=do_generate).pack(pady=15)


if __name__ == "__main__":
    app = HorriaLabApp()
    app.mainloop()
