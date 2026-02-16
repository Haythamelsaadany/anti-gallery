import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات والربط الذكي ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
API_URL = "https://api-inference.huggingface.co"

# جلب التوكن بأمان من السكرتس
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except:
    HF_TOKEN = None

if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- 2. محرك البحث الذكي (محسن) ---
def query_ai(image_bytes):
    if not HF_TOKEN:
        return {"error": "التوكن غير موجود في إعدادات Secrets"}
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(API_URL, headers=headers, data=image_bytes)
    return response.json()

# --- 3. نظام الحماية وقاعدة البيانات ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

def check_auth():
    if "auth" not in st.session_state: st.session_state["auth"] = False
    if not st.session_state["auth"]:
        with st.form("Login"):
            u = st.text_input("المستخدم"); p = st.text_input("كلمة السر", type="password")
            if st.form_submit_button("دخول"):
                if u == "admin" and p == "1234": st.session_state["auth"] = True; st.rerun()
                else: st.error("بيانات خاطئة!")
        return False
    return True

st.set_page_config(page_title="جاليري PRO المطور", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم")
    menu = st.sidebar.radio("القائمة", ["عرض وتعديل المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨"])

    # --- حل مشكلة التعديل وتحديث الصورة الفوري ---
    if menu == "عرض وتعديل المخزن 🖼️":
        st.header("🖼️ إدارة المقتنيات")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        if df.empty: st.info("المخزن فارغ.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        # الحل: إضافة معلمة متغيرة للرابط لإجبار المتصفح على تحديث الصورة
                        img_path = f"{row['image_path']}?v={os.path.getmtime(row['image_path'])}" if os.path.exists(row['image_path']) else None
                        if img_path: st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name'])
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"🗑️ حذف", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()
                        if c2.button(f"⚙️ تعديل", key=f"edit_btn_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = True

                        if st.session_state.get(f"edit_mode_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                new_n = st.text_input("الاسم", row['name'])
                                new_p = st.number_input("السعر", value=float(row['price']))
                                new_img = st.file_uploader("تحديث الصورة", type=['jpg', 'png', 'jpeg'], key=f"img_{row['id']}")
                                if st.form_submit_button("✅ حفظ وتحديث"):
                                    if new_img:
                                        with open(row['image_path'], "wb") as f: f.write(new_img.getbuffer())
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=? WHERE id=?", (new_n, new_p, row['id']))
                                    st.session_state[f"edit_mode_{row['id']}"] = False
                                    st.success("تم الحفظ وتحديث الصورة!"); st.rerun()

    # --- البحث الذكي (مع معالجة خطأ Secrets) ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الذكي")
        up = st.file_uploader("ارفع صورة للتحليل", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 تحليل وبحث"):
                with st.spinner("جاري التحليل..."):
                    result = query_ai(up.getvalue())
                    if isinstance(result, list) and len(result) > 0:
                        res_text = result[0].get('generated_text', '')
                        encoded_q = urllib.parse.quote_plus(res_text)
                        st.success(f"النتيجة: {res_text}")
                        st.link_button("🛒 بحث eBay", f"https://www.ebay.com{encoded_q}")
                    elif "error" in result:
                        st.error(f"❌ خطأ: {result['error']}")
                    else:
                        st.warning("🔄 الموديل يستعد.. حاول مرة أخرى خلال 10 ثوانٍ.")
