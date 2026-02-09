import streamlit as st
import os
import sqlite3
import pandas as pd
from PIL import Image
import numpy as np

# --- 1. الإعدادات الأساسية ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS antiques
                 (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                  price REAL, image_path TEXT)''')
    conn.commit()
    conn.close()

# --- 2. إدارة قاعدة البيانات ---
def add_antique(id, name, desc, price, img_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO antiques VALUES (?, ?, ?, ?, ?)", 
                  (id, name, desc, price, img_path))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def get_all_antiques():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM antiques")
    items = c.fetchall()
    conn.close()
    return items

# --- 3. وظائف الإكسيل (تعتمد على الترتيب) ---
def import_from_excel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        success_count = 0
        for _, row in df.iterrows():
            # سحب البيانات بالترتيب: 0=ID, 1=الاسم, 2=الوصف, 3=السعر, 4=المسار
            ant_id = str(row.iloc[0])
            ant_name = str(row.iloc[1])
            ant_desc = str(row.iloc[2])
            price_raw = str(row.iloc[3]).replace('$', '').replace(',', '').strip()
            ant_price = float(price_raw) if price_raw != 'nan' else 0.0
            ant_img = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ""
            
            if add_antique(ant_id, ant_name, ant_desc, ant_price, ant_img):
                success_count += 1
        return success_count
    except Exception as e:
        st.error(f"خطأ في قراءة ملف الإكسيل: {e}")
        return 0

# --- 4. واجهة البرنامج ---
st.set_page_config(page_title="ANTI Dashboard", layout="wide")
init_db()

# تنسيق CSS بسيط لتحسين المظهر
st.markdown("""<style> .stButton>button { width: 100%; border-radius: 5px; } </style>""", unsafe_allow_html=True)

st.sidebar.title("💎 ANTI Gallery")
menu = ["عرض المخزن 🖼️", "التقارير والإكسيل 📊", "إضافة يدوية ✨"]
choice = st.sidebar.selectbox("القائمة", menu)

# --- قسم عرض المخزن مع خاصية "الفتح" ---
if choice == "عرض المخزن 🖼️":
    st.header("🖼️ مقتنيات الجاليري")
    items = get_all_antiques()
    if items:
        cols = st.columns(3)
        for idx, item in enumerate(items):
            id, name, desc, price, img_path = item
            with cols[idx % 3]:
                with st.container(border=True):
                    # عرض الصورة أو مكان بديل
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.info("الصورة غير متوفرة")
                    
                    st.subheader(name[:25] + "..." if len(name) > 25 else name)
                    st.write(f"💰 **{price:,.2f} $**")
                    
                    # زر فتح العنصر (Pop-up)
                    if st.button(f"🔍 تفاصيل القطعة", key=f"btn_{id}"):
                        @st.dialog(f"بيانات: {name}")
                        def show_modal():
                            if img_path and os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                            st.write(f"**كود القطعة:** {id}")
                            st.write(f"**السعر التقديري:** {price:,.2f} $")
                            st.divider()
                            st.write("**الوصف الكامل:**")
                            st.write(desc)
                            if st.button("إغلاق"): st.rerun()
                        show_modal()
    else:
        st.warning("المخزن فارغ حالياً.")

# --- قسم الإكسيل ---
elif choice == "التقارير والإكسيل 📊":
    st.header("📊 إدارة ملفات الإكسيل")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("تحميل البيانات (Export)")
        if st.button("📥 استخراج تقرير شامل"):
            all_data = get_all_antiques()
            df_out = pd.DataFrame(all_data, columns=['ID', 'الاسم', 'الوصف', 'السعر', 'مسار الصورة'])
            df_out.to_excel("inventory.xlsx", index=False)
            with open("inventory.xlsx", "rb") as f:
                st.download_button("حفظ الملف على جهازك", f, file_name="ANTI_Inventory.xlsx")
    
    with col2:
        st.subheader("رفع بيانات (Import)")
        up_file = st.file_uploader("ارفع ملف الإكسيل (تأكد من ترتيب الأعمدة)", type=['xlsx'])
        if up_file and st.button("تأكيد الرفع"):
            count = import_from_excel(up_file)
            st.success(f"تم إضافة {count} قطعة بنجاح!")
            st.rerun()

# --- قسم الإضافة اليدوية ---
elif choice == "إضافة يدوية ✨":
    st.header("✨ إضافة قطعة جديدة")
    with st.form("manual_form"):
        f_id = st.text_input("كود التحفة (ID)")
        f_name = st.text_input("اسم القطعة")
        f_price = st.number_input("السعر ($)", min_value=0.0)
        f_img = st.file_uploader("ارفع صورة", type=['jpg', 'png'])
        f_desc = st.text_area("الوصف")
        if st.form_submit_button("حفظ الآن"):
            if f_id and f_name and f_img:
                p = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                with open(p, "wb") as f: f.write(f_img.getbuffer())
                add_antique(f_id, f_name, f_desc, f_price, p)
                st.success("تم الحفظ!")
