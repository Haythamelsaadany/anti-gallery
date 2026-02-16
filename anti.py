import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات (نفس المجلد والأسماء الأصلية) ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. محرك البحث الذكي (باستخدام API لضمان السرعة) ---
HF_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co"

def query_ai(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        if response.status_code == 200: return response.json()
        return {"error": "المحرك يستعد.. حاول مرة أخرى بعد قليل."}
    except: return {"error": "فشل الاتصال."}

# --- 3. نظام الحماية والدخول ---
def check_auth():
    if "auth" not in st.session_state: st.session_state["auth"] = False
    if not st.session_state["auth"]:
        with st.form("Login"):
            st.subheader("🔐 دخول نظام الجاليري الذكي")
            u = st.text_input("المستخدم"); p = st.text_input("كلمة السر", type="password")
            if st.form_submit_button("دخول"):
                if u == "admin" and p == "1234": st.session_state["auth"] = True; st.rerun()
                else: st.error("بيانات خاطئة!")
        return False
    return True

# --- 4. واجهة البرنامج الكاملة ---
st.set_page_config(page_title="نظام الجاليري الذكي PRO", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم الشامل")
    menu = st.sidebar.radio("القائمة", ["عرض وتعديل المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير والإكسيل 📊"])

    # --- قسم عرض وتعديل المخزن (تعديل الكود، الصورة، السعر) ---
    if menu == "عرض وتعديل المخزن 🖼️":
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
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"🗑️ حذف", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()
                        if c2.button(f"⚙️ تعديل", key=f"edit_{row['id']}"):
                            st.session_state[f"edit_active_{row['id']}"] = True

                        if st.session_state.get(f"edit_active_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                n_n = st.text_input("الاسم الجديد", row['name'])
                                n_p = st.number_input("السعر الجديد", value=float(row['price']))
                                n_i = st.file_uploader("تحديث الصورة", type=['jpg', 'png', 'jpeg'], key=f"up_{row['id']}")
                                if st.form_submit_button("💾 حفظ التعديل"):
                                    if n_i:
                                        with open(row['image_path'], "wb") as f: f.write(n_i.getbuffer())
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=? WHERE id=?", (n_n, n_p, row['id']))
                                    st.session_state[f"edit_active_{row['id']}"] = False
                                    st.success("تم التعديل!"); st.rerun()

    # --- قسم البحث الذكي العالمي (AI) ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الشامل للمقتنيات والأسعار")
        up = st.file_uploader("ارفع صورة القطعة للبحث", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 تحليل شامل وتقييم"):
                with st.spinner("جاري استجواب الذكاء الاصطناعي..."):
                    result = query_ai(up.getvalue())
                    if isinstance(result, list) and len(result) > 0:
                        res_text = result[0].get('generated_text', '')
                        encoded_q = urllib.parse.quote_plus(res_text)
                        st.success(f"✅ التعرف البصري: {res_text}")
                        st.link_button("🛒 بحث في eBay (الأسعار المباعة)", f"https://www.ebay.com{encoded_q}&LH_Sold=1")
                        st.link_button("🖼️ أرشيف الصور (Google Search)", f"https://www.google.com{encoded_q}&tbm=isch")
                    elif "error" in result: st.warning(result["error"])

    # --- إضافة قطعة ✨ (بنفس الطريقة القديمة) ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add_new"):
            f_id = st.text_input("ID"); f_n = st.text_input("الاسم"); f_p = st.number_input("السعر"); f_i = st.file_uploader("الصورة")
            if st.form_submit_button("💾 حفظ"):
                if f_id and f_i:
                    path = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                    with open(path, "wb") as f: f.write(f_i.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (f_id, f_n, "", f_p, path))
                    st.success("تم الحفظ!"); st.rerun()

    # --- التقارير والإكسيل 📊 (كما كانت) ---
    elif menu == "التقارير والإكسيل 📊":
        with sqlite3.connect(DB_NAME) as conn: df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 تحميل Excel", towrite.getvalue(), "inventory.xlsx")
