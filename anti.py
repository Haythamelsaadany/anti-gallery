import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات ---
DB_NAME = 'gallery_final_v5.db' # قاعدة بيانات جديدة نظيفة تماماً
IMG_FOLDER = "images"
API_URL = "https://api-inference.huggingface.co"
HF_TOKEN = st.secrets.get("HF_TOKEN", "")

if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. محرك البحث الذكي (API) ---
def query_ai(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        if response.status_code == 200: return response.json()
        return {"error": "المحرك يستعد.. حاول مرة أخرى بعد قليل."}
    except: return {"error": "فشل الاتصال بالذكاء الاصطناعي."}

# --- 3. نظام الحماية ---
def check_auth():
    if "auth" not in st.session_state: st.session_state["auth"] = False
    if not st.session_state["auth"]:
        with st.form("Login"):
            st.subheader("🔐 دخول نظام الجاليري")
            u = st.text_input("المستخدم"); p = st.text_input("كلمة السر", type="password")
            if st.form_submit_button("دخول"):
                if u == "admin" and p == "1234": st.session_state["auth"] = True; st.rerun()
                else: st.error("بيانات خاطئة!")
        return False
    return True

st.set_page_config(page_title="جاليري PRO المتكامل", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم")
    menu = st.sidebar.radio("القائمة", ["إدارة المخزن 🖼️", "البحث الذكي (AI) 🤖", "رفع مقتنيات (Excel) 📥", "التقارير 📊"])

    # --- إدارة المخزن ---
    if menu == "إدارة المخزن 🖼️":
        st.header("🖼️ المقتنيات الحالية")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        if df.empty: st.info("المخزن فارغ.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        if os.path.exists(row['image_path']): st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name']); st.write(f"💰 {row['price']} $")
                        if st.button(f"🗑️ حذف {row['id']}", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()

    # --- حل مشكلة رفع الإكسيل (تصحيح الخطأ) ---
    elif menu == "رفع مقتنيات (Excel) 📥":
        st.header("📥 رفع المخزون من إكسيل")
        st.info("تأكد أن ملف الإكسيل يحتوي على الأعمدة: id, name, description, price, image_path")
        up_ex = st.file_uploader("اختر الملف", type=['xlsx'])
        if up_ex:
            df_new = pd.read_excel(up_ex)
            if st.button("🚀 تنفيذ الرفع الآن"):
                try:
                    # التأكد من توافق الأعمدة قبل الرفع لمنع الـ Traceback
                    cols_needed = ['id', 'name', 'description', 'price', 'image_path']
                    df_final = df_new[cols_needed]
                    with sqlite3.connect(DB_NAME) as conn:
                        df_final.to_sql('antiques', conn, if_exists='append', index=False)
                    st.success("تم الرفع بنجاح!"); st.rerun()
                except Exception as e:
                    st.error(f"خطأ في ملف الإكسيل: تأكد من أسماء الأعمدة. التفاصيل: {e}")

    # --- البحث الذكي ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الذكي")
        up = st.file_uploader("ارفع صورة", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 تحليل"):
                with st.spinner("جاري التحليل..."):
                    result = query_ai(up.getvalue())
                    if isinstance(result, list) and len(result) > 0:
                        res_text = result[0].get('generated_text', '')
                        encoded_q = urllib.parse.quote_plus(res_text)
                        st.success(f"النتيجة: {res_text}")
                        st.link_button("🛒 بحث eBay", f"https://www.ebay.com{encoded_q}&LH_Sold=1")
                    elif "error" in result: st.warning(result["error"])

    # --- التقارير ---
    elif menu == "التقارير 📊":
        st.header("📊 التقارير")
        with sqlite3.connect(DB_NAME) as conn: df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            tow = io.BytesIO(); df.to_excel(tow, index=False, engine='openpyxl')
            st.download_button("📥 تحميل Excel", tow.getvalue(), "report.xlsx")
