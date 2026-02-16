import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات ---
DB_NAME = 'gallery.db'
API_URL = "https://api-inference.huggingface.co"
HF_TOKEN = st.secrets.get("HF_TOKEN", "")

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_url TEXT)''')

# --- 2. محرك البحث الذكي (API) ---
def query_ai(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        if response.status_code == 200: return response.json()
        return {"error": "المحرك يستعد.. انتظر 20 ثانية وحاول مجدداً."}
    except: return {"error": "فشل الاتصال."}

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

st.set_page_config(page_title="جاليري PRO السحابي", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم")
    menu = st.sidebar.radio("القائمة", ["عرض المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨"])

    if menu == "عرض المخزن 🖼️":
        st.header("🖼️ المقتنيات")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        if df.empty: st.info("المخزن فارغ.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        # عرض الصورة من الرابط
                        if row['image_url']: st.image(row['image_url'], use_container_width=True)
                        st.subheader(row['name'])
                        st.write(f"💰 {row['price']} $")
                        if st.button(f"🗑️ حذف {row['id']}", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn:
                                conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()

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

    elif menu == "إضافة قطعة ✨":
        with st.form("add"):
            st.info("💡 ملاحظة: استخدم رابط الصورة (URL) لضمان ظهورها دائماً أونلاين.")
            fid = st.text_input("الكود (ID)"); fn = st.text_input("الاسم")
            fp = st.number_input("السعر"); f_url = st.text_input("رابط الصورة (URL)")
            if st.form_submit_button("💾 حفظ"):
                if fid and f_url:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques (id, name, price, image_url) VALUES (?,?,?,?)", 
                                     (fid, fn, fp, f_url))
                    st.success("تم الحفظ!"); st.rerun()
