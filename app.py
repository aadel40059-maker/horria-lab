# -*- coding: utf-8 -*-
"""
app.py
-------
Horria Lab — نسخة ويب (Streamlit)
Developed By Eng. Ahmed Adel

تشغيل محلي:  streamlit run app.py
أو ينشر مجانًا على streamlit.io (راجع README.md)
"""

import io
import json
from datetime import date

import pandas as pd
import streamlit as st

from sheets_manager import SheetsManager
import pdf_reports
from master_data import SUPPLIERS_BY_TYPE, PRODUCTS_BY_SUPPLIER

APP_NAME = "Horria Lab"
DEVELOPER = "Developed By Eng. Ahmed Adel"
INCOMING_TYPES = ["خامات رئيسية", "خامات تعبئة وتغليف", "CF"]
UNITS = ["كرتونة", "كيس", "طن", "كيلوجرام", "لتر", "برميل", "علبة", "شيكارة", "وحدة", "أخرى"]
EDIT_PASSWORD = "lab1111"

st.set_page_config(page_title=APP_NAME, page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
    .block-container { direction: rtl; }
    h1, h2, h3, h4, p, label, .stMarkdown { text-align: right; }
    div[data-testid="stMetricLabel"] { text-align: right; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="جاري الاتصال بجوجل شيت...")
def get_sheets_manager(creds_json: str, sheet_id: str, worksheet_name: str):
    sm = SheetsManager()
    creds_info = json.loads(creds_json)
    sm.connect_from_info(creds_info, sheet_id, worksheet_name)
    return sm


def load_credentials_and_sheet_id():
    """يحاول القراءة من secrets أولاً (للنشر على streamlit.io)، وإلا يعرض رفع ملف يدوي."""
    if "gcp_service_account" in st.secrets:
        creds_json = json.dumps(dict(st.secrets["gcp_service_account"]))
        sheet_id = st.secrets.get("sheet_id", "")
        worksheet_name = st.secrets.get("worksheet_name", "بيانات")
        return creds_json, sheet_id, worksheet_name

    st.sidebar.header("⚙ إعدادات الاتصال بجوجل شيت")
    uploaded = st.sidebar.file_uploader("ملف اعتماد Google (JSON)", type="json")
    sheet_id = st.sidebar.text_input("Sheet ID", value=st.session_state.get("sheet_id", ""))
    worksheet_name = st.sidebar.text_input("اسم الشيت الفرعي", value="بيانات")

    creds_json = None
    if uploaded is not None:
        creds_json = uploaded.read().decode("utf-8")
        st.session_state["creds_json"] = creds_json
    elif "creds_json" in st.session_state:
        creds_json = st.session_state["creds_json"]

    st.session_state["sheet_id"] = sheet_id
    return creds_json, sheet_id, worksheet_name


def df_from_records(records):
    if not records:
        return pd.DataFrame(columns=["التاريخ", "نوع الوارد", "اسم المورد", "اسم المنتج", "الحالة", "ملاحظات"])
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
def main():
    st.markdown(f"<h1 style='color:#1B4332;'>🧪 {APP_NAME}</h1>", unsafe_allow_html=True)
    st.caption(DEVELOPER)

    creds_json, sheet_id, worksheet_name = load_credentials_and_sheet_id()

    if not creds_json or not sheet_id:
        st.info(
            "من فضلك أدخل بيانات الاتصال بجوجل شيت من الشريط الجانبي "
            "(ملف الاعتماد JSON + Sheet ID) للبدء. راجع README.md لطريقة الإعداد."
        )
        return

    try:
        sm = get_sheets_manager(creds_json, sheet_id, worksheet_name)
    except Exception as e:
        st.error(f"فشل الاتصال بجوجل شيت:\n\n{e}")
        return

    st.toast("متصل بجوجل شيت ✅")

    if "records" not in st.session_state or st.session_state.get("_needs_refresh", True):
        st.session_state["records"] = sm.get_all_records()
        st.session_state["_needs_refresh"] = False

    tab1, tab2, tab3, tab4 = st.tabs(["📝 تسجيل توريد", "📋 سجلات اليوم", "📊 التقارير", "✏️ تعديل / حذف"])

    # ------------------------------------------------------------------
    with tab1:
        st.subheader("تسجيل توريد جديد")
        records = st.session_state["records"]

        incoming_type = st.selectbox("نوع الوارد", INCOMING_TYPES)

        # دمج قوائم الموردين الجاهزة (master_data.py) مع أي موردين جدد اتسجلوا في الشيت
        suppliers_from_sheet = {
            r["اسم المورد"].strip() for r in records
            if r.get("اسم المورد") and r.get("نوع الوارد") == incoming_type
        }
        suppliers_from_master = set(SUPPLIERS_BY_TYPE.get(incoming_type, []))
        suppliers = sorted(suppliers_from_sheet | suppliers_from_master)

        supplier_choice = st.selectbox(
            "اسم المورد (اكتب داخل القائمة للفلترة)",
            options=["-- مورد جديد --"] + suppliers,
        )
        if supplier_choice == "-- مورد جديد --":
            supplier = st.text_input("اكتب اسم المورد الجديد")
        else:
            supplier = supplier_choice

        # دمج قوائم المنتجات الجاهزة مع أي منتجات جديدة اتسجلت في الشيت لنفس المورد
        products_from_sheet = {
            r["اسم المنتج"].strip() for r in records
            if r.get("اسم المنتج") and r.get("اسم المورد") == supplier
        }
        products_from_master = set(PRODUCTS_BY_SUPPLIER.get(supplier, []))
        products = sorted(products_from_sheet | products_from_master)

        product_choice = st.selectbox(
            "اسم المنتج (اكتب داخل القائمة للفلترة)",
            options=["-- منتج جديد --"] + products,
        )
        if product_choice == "-- منتج جديد --":
            product = st.text_input("اكتب اسم المنتج الجديد")
        else:
            product = product_choice

        col_qty, col_unit = st.columns(2)
        with col_qty:
            quantity = st.number_input("الكمية", min_value=0.0, step=1.0, format="%g")
        with col_unit:
            unit_choice = st.selectbox("الوحدة", UNITS)
            if unit_choice == "أخرى":
                unit = st.text_input("اكتب الوحدة")
            else:
                unit = unit_choice

        col1, col2 = st.columns(2)
        with col1:
            record_date = st.date_input("التاريخ", value=date.today())
        with col2:
            status = st.radio("الحالة", ["مقبول", "مرفوض"], horizontal=True)

        notes = st.text_input("ملاحظات")

        if st.button("💾 حفظ التوريد", type="primary", use_container_width=True):
            if not supplier or not product:
                st.warning("من فضلك أدخل اسم المورد واسم المنتج.")
            else:
                sm.append_record(
                    record_date.isoformat(), incoming_type, supplier, product, status, notes,
                    quantity=quantity if quantity else "", unit=unit,
                )
                st.session_state["_needs_refresh"] = True
                st.success("تم حفظ التوريد بنجاح ✅")
                st.rerun()

    # ------------------------------------------------------------------
    with tab2:
        st.subheader("سجلات اليوم")
        if st.button("🔄 تحديث السجلات"):
            st.session_state["_needs_refresh"] = True
            st.rerun()

        records = st.session_state["records"]
        today_str = date.today().isoformat()
        today_records = [r for r in records if str(r.get("التاريخ", "")).strip() == today_str]
        df = df_from_records(today_records)

        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي اليوم", len(df))
        c2.metric("مقبول", len(df[df["الحالة"] == "مقبول"]) if not df.empty else 0)
        c3.metric("مرفوض", len(df[df["الحالة"] == "مرفوض"]) if not df.empty else 0)

        st.dataframe(df, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------
    with tab3:
        st.subheader("التقارير")
        records = st.session_state["records"]

        st.markdown("#### 📄 تقرير يومي")
        report_date = st.date_input("اختر التاريخ", value=date.today(), key="daily_date")
        if st.button("إنشاء تقرير اليوم PDF"):
            buf = io.BytesIO()
            pdf_reports.daily_report(records, report_date.isoformat(), buf)
            st.download_button(
                "⬇ تحميل التقرير اليومي",
                data=buf.getvalue(),
                file_name=f"تقرير_يومي_{report_date.isoformat()}.pdf",
                mime="application/pdf",
            )

        st.divider()
        st.markdown("#### 📊 تقرير شهري (حالات الرفض)")
        colm1, colm2 = st.columns(2)
        with colm1:
            year = st.number_input("السنة", min_value=2000, max_value=2100, value=date.today().year, step=1)
        with colm2:
            month = st.number_input("الشهر", min_value=1, max_value=12, value=date.today().month, step=1)
        if st.button("إنشاء التقرير الشهري PDF"):
            buf = io.BytesIO()
            pdf_reports.monthly_rejected_report(records, int(year), int(month), buf)
            st.download_button(
                "⬇ تحميل التقرير الشهري",
                data=buf.getvalue(),
                file_name=f"تقرير_شهري_رفض_{year}-{month:02d}.pdf",
                mime="application/pdf",
            )

        st.divider()
        st.markdown("#### 🔍 بحث عن مورد")
        supplier_q = st.text_input("اسم المورد (كامل أو جزء منه)", key="supplier_search")
        if st.button("بحث وإنشاء تقرير PDF"):
            if not supplier_q.strip():
                st.warning("أدخل اسم المورد أولاً.")
            else:
                matched = [r for r in records if supplier_q.strip() in str(r.get("اسم المورد", ""))]
                rejected = [r for r in matched if "مرفوض" in str(r.get("الحالة", ""))]
                accepted = [r for r in matched if "مقبول" in str(r.get("الحالة", ""))]

                c1, c2, c3 = st.columns(3)
                c1.metric("إجمالي التوريدات", len(matched))
                c2.metric("مقبول", len(accepted))
                c3.metric("مرفوض", len(rejected))
                st.dataframe(df_from_records(matched), use_container_width=True, hide_index=True)

                buf = io.BytesIO()
                pdf_reports.supplier_report(records, supplier_q.strip(), buf)
                st.download_button(
                    "⬇ تحميل تقرير المورد PDF",
                    data=buf.getvalue(),
                    file_name=f"تقرير_مورد_{supplier_q.strip()}.pdf",
                    mime="application/pdf",
                )

    # ------------------------------------------------------------------
    with tab4:
        st.subheader("تعديل أو حذف توريد")

        if not st.session_state.get("edit_unlocked", False):
            pwd = st.text_input("أدخل كلمة المرور", type="password", key="edit_pwd_input")
            if st.button("دخول"):
                if pwd == EDIT_PASSWORD:
                    st.session_state["edit_unlocked"] = True
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")
        else:
            col_lock, _ = st.columns([1, 5])
            with col_lock:
                if st.button("🔒 خروج"):
                    st.session_state["edit_unlocked"] = False
                    st.rerun()

            rows = sm.get_all_records_with_row()
            if not rows:
                st.info("لا توجد سجلات بعد.")
            else:
                # فلترة بحث سريعة بالتاريخ أو اسم المورد أو المنتج
                search_q = st.text_input("بحث (بالتاريخ أو اسم المورد أو المنتج)", key="edit_search")
                filtered = rows
                if search_q.strip():
                    q = search_q.strip()
                    filtered = [
                        r for r in rows
                        if q in str(r.get("التاريخ", "")) or q in str(r.get("اسم المورد", ""))
                        or q in str(r.get("اسم المنتج", ""))
                    ]

                # الأحدث أولاً
                filtered = list(reversed(filtered))

                if not filtered:
                    st.warning("لا توجد نتائج مطابقة للبحث.")
                else:
                    options = {
                        f"صف {r['_row']} | {r.get('التاريخ','')} | {r.get('اسم المورد','')} | "
                        f"{r.get('اسم المنتج','')} | {r.get('الحالة','')}": r
                        for r in filtered
                    }
                    chosen_label = st.selectbox("اختر السجل", options=list(options.keys()))
                    chosen = options[chosen_label]

                    st.markdown("---")
                    e_date = st.date_input(
                        "التاريخ",
                        value=date.fromisoformat(str(chosen.get("التاريخ"))[:10])
                        if chosen.get("التاريخ") else date.today(),
                        key=f"e_date_{chosen['_row']}",
                    )
                    e_type = st.selectbox(
                        "نوع الوارد", INCOMING_TYPES,
                        index=INCOMING_TYPES.index(chosen.get("نوع الوارد"))
                        if chosen.get("نوع الوارد") in INCOMING_TYPES else 0,
                        key=f"e_type_{chosen['_row']}",
                    )
                    e_supplier = st.text_input(
                        "اسم المورد", value=chosen.get("اسم المورد", ""), key=f"e_sup_{chosen['_row']}"
                    )
                    e_product = st.text_input(
                        "اسم المنتج", value=chosen.get("اسم المنتج", ""), key=f"e_prod_{chosen['_row']}"
                    )
                    col_eq, col_eu = st.columns(2)
                    with col_eq:
                        existing_qty = chosen.get("الكمية", "")
                        try:
                            existing_qty = float(existing_qty) if str(existing_qty).strip() != "" else 0.0
                        except ValueError:
                            existing_qty = 0.0
                        e_quantity = st.number_input(
                            "الكمية", min_value=0.0, step=1.0, format="%g",
                            value=existing_qty, key=f"e_qty_{chosen['_row']}",
                        )
                    with col_eu:
                        existing_unit = chosen.get("الوحدة", "")
                        e_unit = st.selectbox(
                            "الوحدة", UNITS,
                            index=UNITS.index(existing_unit) if existing_unit in UNITS else len(UNITS) - 1,
                            key=f"e_unit_{chosen['_row']}",
                        )
                        if e_unit == "أخرى":
                            e_unit = st.text_input(
                                "اكتب الوحدة", value=existing_unit, key=f"e_unit_txt_{chosen['_row']}"
                            )
                    e_status = st.radio(
                        "الحالة", ["مقبول", "مرفوض"],
                        index=0 if chosen.get("الحالة") == "مقبول" else 1,
                        horizontal=True, key=f"e_status_{chosen['_row']}",
                    )
                    e_notes = st.text_input(
                        "ملاحظات", value=chosen.get("ملاحظات", ""), key=f"e_notes_{chosen['_row']}"
                    )

                    col_save, col_delete = st.columns(2)
                    with col_save:
                        if st.button("💾 حفظ التعديل", type="primary", use_container_width=True):
                            sm.update_row(
                                chosen["_row"], e_date.isoformat(), e_type,
                                e_supplier.strip(), e_product.strip(), e_status, e_notes.strip(),
                                quantity=e_quantity if e_quantity else "", unit=e_unit,
                            )
                            st.session_state["_needs_refresh"] = True
                            st.success("تم حفظ التعديل ✅")
                            st.rerun()

                    with col_delete:
                        confirm = st.checkbox("متأكد إني عايز أمسح السجل ده نهائيًا", key=f"confirm_del_{chosen['_row']}")
                        if st.button("🗑 حذف نهائي", use_container_width=True, disabled=not confirm):
                            sm.delete_row(chosen["_row"])
                            st.session_state["_needs_refresh"] = True
                            st.success("تم حذف السجل ✅")
                            st.rerun()


if __name__ == "__main__":
    main()
