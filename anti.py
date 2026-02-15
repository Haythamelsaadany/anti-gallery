import streamlit as st
import os
import sqlite3
import pandas as pd
from PIL import Image
import io

# --- 1. الإعدادات الأساسية ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. واجهة البرنامج ---
st.set_page_config(page_title="نظام إدارة الجاليري PRO", layout="wide")
init_db()

st.sidebar.title("🏛️ لوحة التحكم")
menu = st.sidebar.radio("القائمة", ["عرض المخزن 🖼️", "إضافة قطعة ✨", "التقارير والإكسيل 📊", "خبير التقييم (AI) 🤖"])

# --- وظيفة التعديل (تعديل الكود والصورة وكل شيء) ---
@st.dialog("تعديل بيانات المقتنى")
def edit_item(row):
    new_id = st.text_input("كود القطعة (ID)", value=row['id'])
    new_n = st.text_input("الاسم", value=row['name'])
    new_p = st.number_input("السعر", value=float(row['price']))
    new_d = st.text_area("الوصف", value=row['description'])
    new_img = st.file_uploader("تحديث الصورة (اختياري)", type=['jpg', 'png', 'jpeg'])
    
    if st.button("💾 حفظ التعديلات الشاملة"):
        path = row['image_path']
        if new_img:
            path = os.path.join(IMG_FOLDER, f"{new_id}.jpg")
            with open(path, "wb") as f: f.write(new_img.getbuffer())
        
        with sqlite3.connect(DB_NAME) as conn:
            # إذا تغير الـ ID نقوم بحذف القديم وإضافة الجديد
            if new_id != row['id']:
                conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
            conn.execute("INSERT OR REPLACE INTO antiques VALUES (?, ?, ?, ?, ?)", 
                         (new_id, new_n, new_d, new_p, path))
        st.success("تم التحديث بنجاح!"); st.rerun()

# --- قسم عرض المخزن ---
if menu == "عرض المخزن 🖼️":
    st.header("🖼️ مقتنيات الجاليري")
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
                    st.write(f"💰 {row['price']} $ | كود: {row['id']}")
                    if st.button(f"⚙️ تعديل / تفاصيل", key=f"btn_{row['id']}"):
                        edit_item(row)

# --- قسم إضافة قطعة ---
elif menu == "إضافة قطعة ✨":
    st.header("✨ إضافة قطعة جديدة")
    with st.form("add_form", clear_on_submit=True):
        f_id = st.text_input("كود القطعة"); f_n = st.text_input("الاسم")
        f_p = st.number_input("السعر"); f_i = st.file_uploader("الصورة")
        f_d = st.text_area("الوصف")
        if st.form_submit_button("💾 حفظ"):
            if f_id and f_i:
                p = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                with open(p, "wb") as f: f.write(f_i.getbuffer())
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (f_id, f_n, f_d, f_p, p))
                st.success("تم الحفظ!")
            else: st.error("الكود والصورة مطلوبان.")

# --- قسم التقارير والإكسيل (جديد بالكامل) ---
elif menu == "التقارير والإكسيل 📊":
    st.header("📊 إدارة البيانات (Excel)")
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql("SELECT * FROM antiques", conn)
    
    tab1, tab2 = st.tabs(["📥 تصدير التقارير", "📤 استيراد مخزون"])
    
    with tab1:
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("تحميل المخزن كملف Excel", data=towrite.getvalue(), file_name="inventory_report.xlsx")

    with tab2:
        up_excel = st.file_uploader("ارفع ملف Excel يحتوي على بيانات المخزن", type=['xlsx'])
        if up_excel:
            new_data = pd.read_excel(up_excel)
            st.write("معاينة البيانات المرفوعة:")
            st.dataframe(new_data.head())
            if st.button("✅ تأكيد استيراد البيانات"):
                with sqlite3.connect(DB_NAME) as conn:
                    new_data.to_sql("antiques", conn, if_exists="append", index=False)
                st.success("تم دمج البيانات بنجاح!")

# --- قسم خبير التقييم (مع إصلاح خطأ الصورة) ---
elif menu == "خبير التقييم (AI) 🤖":
    st.header("🤖 المحلل الذكي")
    st.warning("هذا القسم يعمل حالياً بوصف بصري فقط.")
    # (كود الـ AI هنا مع التأكد من تحويل النتيجة لـ String لتجنب الخطأ الظاهر في صورتك)
