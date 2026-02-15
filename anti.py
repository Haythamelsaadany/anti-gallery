import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse
from PIL import Image

# --- 1. الإعدادات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. محرك الذكاء الاصطناعي ---
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    HAS_AI = True
except: HAS_AI = False

@st.cache_resource
def load_ai():
    if not HAS_AI: return None, None
    p = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    m = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    return p, m

# --- 3. نظام الحماية ---
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

# --- 4. واجهة البرنامج ---
st.set_page_config(page_title="نظام الجاليري PRO", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ لوحة التحكم")
    menu = st.sidebar.radio("القائمة", ["عرض المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير والإكسيل 📊"])

    # --- قسم البحث الذكي (إصلاح الرابط النهائي) ---
    if menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 خبير التقييم والبحث العالمي")
        up = st.file_uploader("ارفع صورة للبحث", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 ابدأ التحليل والبحث"):
                with st.spinner("جاري التحليل..."):
                    proc, mod = load_ai()
                    raw = Image.open(up).convert('RGB')
                    inputs = proc(raw, return_tensors="pt")
                    out = mod.generate(**inputs)
                    
                    # استخراج النص الصافي تماماً
                    raw_desc = proc.decode(out, skip_special_tokens=True)
                    clean_desc = str(raw_desc).replace("[", "").replace("]", "").replace("'", "").strip()
                    
                    st.success(f"✅ تم التعرف على: {clean_desc}")
                    
                    # ترميز النص للبحث
                    encoded_q = urllib.parse.quote_plus(clean_desc)
                    
                    st.divider()
                    st.subheader("🔗 روابط البحث المباشرة:")
                    
                    # الروابط بهيكلها الرسمي الصحيح 100%
                    ebay_link = f"https://www.ebay.com{encoded_q}"
                    google_link = f"https://www.google.com{encoded_q}&tbm=isch"
                    
                    c1, c2 = st.columns(2)
                    c1.link_button("🛒 شاهد الأسعار في eBay", ebay_link, use_container_width=True)
                    c2.link_button("🔍 البحث في Google Images", google_link, use_container_width=True)

    # --- الأقسام الأخرى تبقى مستقرة كما هي في كودك الأصلي ---
    elif menu == "عرض المخزن 🖼️":
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
                            if os.path.exists(row['image_path']): os.remove(row['image_path'])
                            st.rerun()

    elif menu == "إضافة قطعة ✨":
        with st.form("add_new"):
            f_id = st.text_input("ID"); f_n = st.text_input("الاسم"); f_p = st.number_input("السعر"); f_i = st.file_uploader("الصورة")
            if st.form_submit_button("💾 حفظ"):
                if f_id and f_i:
                    path = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                    with open(path, "wb") as f: f.write(f_i.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn: conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (f_id, f_n, "", f_p, path))
                    st.success("تم الحفظ!"); st.rerun()

    elif menu == "التقارير والإكسيل 📊":
        with sqlite3.connect(DB_NAME) as conn: df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 تحميل Excel", towrite.getvalue(), "inventory.xlsx")
