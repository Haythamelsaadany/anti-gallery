import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات وقاعدة البيانات ---
DB_NAME = 'gallery_pro.db' 
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

st.set_page_config(page_title="نظام الجاليري الشامل", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم")
    menu = st.sidebar.radio("القائمة", ["إدارة المخزن 🖼️", "البحث الذكي (AI) 🤖", "رفع مقتنيات (Excel) 📥", "التقارير 📊"])

    # --- إدارة وعرض المخزن ---
    if menu == "إدارة المخزن 🖼️":
        st.header("🖼️ عرض وتعديل المقتنيات")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        if df.empty: st.info("المخزن فارغ. يمكنك الرفع عبر ملف Excel أو إضافة قطعة.")
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

    # --- ميزة رفع ملف Excel (التي طلبتها) ---
    elif menu == "رفع مقتنيات (Excel) 📥":
        st.header("📥 رفع المخزون دفعة واحدة")
        uploaded_file = st.file_uploader("اختر ملف Excel يحتوي على (id, name, price, description, image_path)", type=['xlsx'])
        if uploaded_file:
            df_upload = pd.read_excel(uploaded_file)
            if st.button("🚀 بدء استيراد البيانات"):
                with sqlite3.connect(DB_NAME) as conn:
                    df_upload.to_sql('antiques', conn, if_exists='append', index=False)
                st.success(f"تم رفع {len(df_upload)} قطعة بنجاح!"); st.rerun()

    # --- البحث الذكي ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الذكي")
        up = st.file_uploader("ارفع صورة للبحث", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 تحليل وبحث"):
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
        st.header("📊 التقارير والإحصائيات")
        with sqlite3.connect(DB_NAME) as conn: df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 تحميل التقرير الحالي كـ Excel", towrite.getvalue(), "report.xlsx")
