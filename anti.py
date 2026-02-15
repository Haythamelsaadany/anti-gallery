import streamlit as st
import os
import sqlite3
import pandas as pd
from PIL import Image
import io

# --- 1. الإعدادات وقاعدة البيانات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. نظام الحماية (Login) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        with st.form("Login"):
            st.subheader("🔐 تسجيل الدخول للجاليري")
            user = st.text_input("اسم المستخدم")
            pwd = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول"):
                if user == "admin" and pwd == "1234": # يمكنك تغيير كلمة المرور هنا
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("بيانات الدخول خاطئة")
        return False
    return True

# --- 3. الدوال المساعدة (التعديل) ---
@st.dialog("تعديل القطعة")
def edit_dialog(row):
    n = st.text_input("الاسم", value=row['name'])
    p = st.number_input("السعر", value=float(row['price']))
    d = st.text_area("الوصف", value=row['description'])
    if st.button("حفظ التعديلات"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE antiques SET name=?, price=?, description=? WHERE id=?", 
                         (n, p, d, row['id']))
        st.success("تم التحديث!"); st.rerun()

# --- 4. واجهة البرنامج الرئيسية ---
st.set_page_config(page_title="نظام الجاليري PRO", layout="wide")
init_db()

if check_password():
    st.sidebar.title("🏛️ لوحة التحكم")
    menu = st.sidebar.radio("القائمة", ["عرض المخزن 🖼️", "إضافة قطعة ✨", "التقارير والإكسيل 📊"])

    # --- عرض المخزن ---
    if menu == "عرض المخزن 🖼️":
        st.header("🖼️ المقتنيات الحالية")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        if df.empty: st.info("المخزن فارغ.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        if os.path.exists(row['image_path']):
                            st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name'])
                        st.write(f"💰 {row['price']} $")
                        if st.button("⚙️ تعديل", key=f"ed_{row['id']}"):
                            edit_dialog(row)

    # --- إضافة قطعة ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add"):
            f_id = st.text_input("ID"); f_n = st.text_input("الاسم")
            f_p = st.number_input("السعر"); f_i = st.file_uploader("الصورة")
            if st.form_submit_button("حفظ"):
                if f_id and f_i:
                    path = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                    with open(path, "wb") as f: f.write(f_i.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", 
                                     (f_id, f_n, "", f_p, path))
                    st.success("تم الحفظ!"); st.rerun()

    # --- التقارير والإكسيل ---
    elif menu == "التقارير والإكسيل 📊":
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        tab1, tab2 = st.tabs(["📥 تصدير Excel", "📤 استيراد Excel"])
        with tab1:
            st.dataframe(df)
            if not df.empty:
                towrite = io.BytesIO()
                df.to_excel(towrite, index=False, engine='openpyxl')
                st.download_button("تحميل الملف 📥", towrite.getvalue(), "inventory.xlsx")
        with tab2:
            file = st.file_uploader("ارفع ملف Excel")
            if file and st.button("تأكيد الاستيراد"):
                new_df = pd.read_excel(file)
                with sqlite3.connect(DB_NAME) as conn:
                    new_df.to_sql("antiques", conn, if_exists="append", index=False)
                st.success("تم الاستيراد!"); st.rerun()
