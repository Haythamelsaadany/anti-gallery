import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse, requests
from PIL import Image

# --- 1. الإعدادات والربط ---
DB_NAME = 'gallery_v3.db' # تغيير الاسم لضمان إنشاء قاعدة بيانات جديدة نظيفة
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
        return {"error": "المحرك يستعد.. حاول مرة أخرى بعد 20 ثانية."}
    except: return {"error": "فشل الاتصال بالمحرك الذكي."}

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
    st.sidebar.title("🏛️ التحكم الشامل")
    menu = st.sidebar.radio("القائمة", ["عرض وتعديل المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير والإكسيل 📊"])

    # --- عرض وتعديل وحذف المخزن ---
    if menu == "عرض وتعديل المخزن 🖼️":
        st.header("🖼️ المقتنيات")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        if df.empty: st.info("المخزن فارغ حالياً.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        if os.path.exists(row['image_path']): 
                            st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name'])
                        st.write(f"💰 {row['price']} $")
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"🗑️ حذف", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()
                        if c2.button(f"⚙️ تعديل", key=f"edit_btn_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = True

                        if st.session_state.get(f"edit_mode_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                n_n = st.text_input("الاسم", row['name'])
                                n_p = st.number_input("السعر", value=float(row['price']))
                                n_d = st.text_area("الوصف", row['description'])
                                n_i = st.file_uploader("تحديث الصورة", type=['jpg', 'png', 'jpeg'], key=f"img_{row['id']}")
                                if st.form_submit_button("✅ حفظ"):
                                    path = row['image_path']
                                    if n_i:
                                        with open(path, "wb") as f: f.write(n_i.getbuffer())
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=?, description=? WHERE id=?", (n_n, n_p, n_d, row['id']))
                                    st.session_state[f"edit_mode_{row['id']}"] = False
                                    st.success("تم التحديث!"); st.rerun()

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

    # --- إضافة قطعة ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add"):
            fid = st.text_input("ID"); fn = st.text_input("الاسم"); fd = st.text_area("الوصف")
            fp = st.number_input("السعر"); fi = st.file_uploader("الصورة")
            if st.form_submit_button("💾 حفظ"):
                if fid and fi:
                    path = os.path.join(IMG_FOLDER, f"{fid}.jpg")
                    with open(path, "wb") as f: f.write(fi.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (fid, fn, fd, fp, path))
                    st.success("تم الحفظ!"); st.rerun()

    # --- التقارير والإكسيل (تمت إعادتها بطلبك) ---
    elif menu == "التقارير والإكسيل 📊":
        st.header("📊 تقارير المخزون")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 تحميل Excel", towrite.getvalue(), "inventory.xlsx")
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
