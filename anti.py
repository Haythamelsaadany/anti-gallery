import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse
from PIL import Image

# --- 1. الإعدادات وقاعدة البيانات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. محرك الذكاء الاصطناعي ---
@st.cache_resource
def load_ai():
    from transformers import BlipProcessor, BlipForConditionalGeneration
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

st.set_page_config(page_title="جاليري PRO المطور", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ لوحة التحكم")
    menu = st.sidebar.radio("القائمة", ["عرض وتعديل المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير 📊"])

    # --- حل مشكلة التعديل (إضافته بجانب الحذف) ---
    if menu == "عرض وتعديل المخزن 🖼️":
        st.header("🖼️ إدارة المقتنيات (عرض/تعديل/حذف)")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        if df.empty: st.info("المخزن فارغ.")
        else:
            cols = st.columns(3)
            for i, row in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        if os.path.exists(row['image_path']): st.image(row['image_path'], use_container_width=True)
                        st.subheader(row['name'])
                        st.write(f"💰 {row['price']} $")
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"🗑️ حذف", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            st.rerun()
                        
                        if c2.button(f"⚙️ تعديل", key=f"edit_btn_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = True

                        # نموذج التعديل يظهر عند الضغط على زر تعديل
                        if st.session_state.get(f"edit_mode_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                new_n = st.text_input("الاسم الجديد", row['name'])
                                new_p = st.number_input("السعر الجديد", value=float(row['price']))
                                new_d = st.text_area("الوصف الجديد", row['description'])
                                if st.form_submit_button("✅ حفظ التغييرات"):
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=?, description=? WHERE id=?", 
                                                     (new_n, new_p, new_d, row['id']))
                                    st.session_state[f"edit_mode_{row['id']}"] = False
                                    st.success("تم التحديث!"); st.rerun()

    # --- حل مشكلة TypeError في البحث الذكي ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 البحث والتحليل العالمي")
        up = st.file_uploader("ارفع صورة", type=['jpg', 'png', 'jpeg'])
        if up:
            img = Image.open(up).convert('RGB')
            st.image(img, width=300)
            if st.button("🚀 بدء التحليل"):
                with st.spinner("جاري التحليل..."):
                    proc, mod = load_ai()
                    inputs = proc(img, return_tensors="pt")
                    out = mod.generate(**inputs)
                    res_text = proc.decode(out, skip_special_tokens=True)
                    
                    # الحل: التأكد من تحويل النص إلى String نظيف قبل الترميز
                    clean_text = str(res_text).strip()
                    encoded_q = urllib.parse.quote_plus(clean_text)
                    
                    st.success(f"النتيجة: {clean_text}")
                    st.link_button("🛒 بحث في eBay", f"https://www.ebay.com{encoded_q}")
                    st.link_button("🔍 بحث Google", f"https://www.google.com{encoded_q}")

    # --- إضافة قطعة ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add"):
            fid = st.text_input("ID"); fn = st.text_input("الاسم"); fp = st.number_input("السعر"); fi = st.file_uploader("الصورة")
            if st.form_submit_button("💾 حفظ"):
                if fid and fi:
                    path = os.path.join(IMG_FOLDER, f"{fid}.jpg")
                    with open(path, "wb") as f: f.write(fi.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (fid, fn, "", fp, path))
                    st.success("تم الحفظ!"); st.rerun()

    # --- التقارير ---
    elif menu == "التقارير 📊":
        with sqlite3.connect(DB_NAME) as conn: df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
