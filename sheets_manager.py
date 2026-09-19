# -*- coding: utf-8 -*-
"""
sheets_manager.py
------------------
طبقة الاتصال بجوجل شيت لبرنامج Horria Lab
مطلوب ملف اعتماد Service Account (JSON) من Google Cloud
راجع ملف README.md لطريقة الإعداد بالتفصيل
"""

import gspread
from google.oauth2.service_account import Credentials

HEADERS = ["التاريخ", "نوع الوارد", "اسم المورد", "اسم المنتج", "الحالة", "ملاحظات", "الكمية", "الوحدة"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsManager:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheet = None

    def connect(self, credentials_path: str, sheet_id: str, worksheet_name: str = "بيانات"):
        """يفتح اتصال بالشيت (من مسار ملف JSON) ويجهز الشيت الفرعي (worksheet)."""
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        return self._finish_connect(creds, sheet_id, worksheet_name)

    def connect_from_info(self, credentials_info: dict, sheet_id: str, worksheet_name: str = "بيانات"):
        """يفتح اتصال بالشيت من محتوى JSON مباشرة (مفيد لـ Streamlit secrets / رفع ملف)."""
        creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
        return self._finish_connect(creds, sheet_id, worksheet_name)

    def _finish_connect(self, creds, sheet_id, worksheet_name):
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(sheet_id)

        try:
            self.worksheet = self.sheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            self.worksheet = self.sheet.add_worksheet(title=worksheet_name, rows=2000, cols=10)

        self._ensure_headers()
        return True

    def _ensure_headers(self):
        first_row = self.worksheet.row_values(1)
        if first_row != HEADERS:
            self.worksheet.update("A1", [HEADERS])

    def append_record(self, date_str, incoming_type, supplier, product, status, notes, quantity="", unit=""):
        row = [date_str, incoming_type, supplier, product, status, notes, quantity, unit]
        self.worksheet.append_row(row, value_input_option="USER_ENTERED")

    def get_all_records(self):
        """يرجع كل الصفوف كقاموس (dict) لكل صف."""
        return self.worksheet.get_all_records(expected_headers=HEADERS)

    def get_all_records_with_row(self):
        """
        زي get_all_records بالظبط، بس كل صف بييجي معاه رقم صفه الحقيقي في الشيت
        (مفتاح "_row") عشان نقدر نعدله أو نمسحه بعدين.
        """
        records = self.get_all_records()
        return [
            {**r, "_row": i + 2}  # +2: أول صف بيانات هو رقم 2 (بعد الهيدر)
            for i, r in enumerate(records)
        ]

    def update_row(self, row_number, date_str, incoming_type, supplier, product, status, notes, quantity="", unit=""):
        """يعدّل صف موجود بالكامل عن طريق رقمه في الشيت."""
        values = [date_str, incoming_type, supplier, product, status, notes, quantity, unit]
        self.worksheet.update(f"A{row_number}:H{row_number}", [values], value_input_option="USER_ENTERED")

    def delete_row(self, row_number):
        """يمسح صف بالكامل من الشيت عن طريق رقمه."""
        self.worksheet.delete_rows(row_number)

    def get_unique_suppliers(self, incoming_type=None):
        records = self.get_all_records()
        vals = {
            r["اسم المورد"].strip()
            for r in records
            if r.get("اسم المورد")
            and (incoming_type is None or r.get("نوع الوارد") == incoming_type)
        }
        return sorted(vals, key=lambda s: s)

    def get_unique_products(self, supplier=None, incoming_type=None):
        records = self.get_all_records()
        vals = {
            r["اسم المنتج"].strip()
            for r in records
            if r.get("اسم المنتج")
            and (supplier is None or r.get("اسم المورد") == supplier)
            and (incoming_type is None or r.get("نوع الوارد") == incoming_type)
        }
        return sorted(vals, key=lambda s: s)
