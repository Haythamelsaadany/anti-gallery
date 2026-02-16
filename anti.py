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

# --- 2. محرك الذكاء الاصطناعي (تحميل محسن للسحابة) ---
@st.cache_resource
def load_ai():
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        # استخدام نسخة base خفيفة لضمان العمل على Streamlit Cloud
        p = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        m = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        return p, m
    except Exception as e:
        return None, None

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

# --- 4. واجهة البرنامج الرئيسية ---
st.set_page_config(page_title="نظام الجاليري الذكي PRO", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ التحكم الشامل")
    menu = st.sidebar.radio("القائمة", ["عرض وتعديل المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير 📊"])

    # --- القسم 1: عرض وتعديل وحذف المقتنيات (شامل تعديل الصور) ---
    if menu == "عرض وتعديل المخزن 🖼️":
        st.header("🖼️ إدارة المقتنيات")
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
                        st.write(f"💰 السعر: {row['price']} $")
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"🗑️ حذف", key=f"del_{row['id']}"):
                            with sqlite3.connect(DB_NAME) as conn:
                                conn.execute("DELETE FROM antiques WHERE id=?", (row['id'],))
                            if os.path.exists(row['image_path']): os.remove(row['image_path'])
                            st.rerun()
                        
                        if c2.button(f"⚙️ تعديل", key=f"edit_btn_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = True

                        # نموذج التعديل المنبثق
                        if st.session_state.get(f"edit_mode_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                st.write("📝 تعديل البيانات:")
                                new_n = st.text_input("الاسم", row['name'])
                                new_p = st.number_input("السعر", value=float(row['price']))
                                new_d = st.text_area("الوصف", row['description'])
                                new_img = st.file_uploader("تحديث الصورة (اختياري)", type=['jpg', 'png', 'jpeg'], key=f"file_{row['id']}")
                                
                                if st.form_submit_button("✅ حفظ التعديلات"):
                                    path = row['image_path']
                                    if new_img: # تحديث ملف الصورة الفعلي
                                        with open(path, "wb") as f:
                                            f.write(new_img.getbuffer())
                                    
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=?, description=? WHERE id=?", 
                                                     (new_n, new_p, new_d, row['id']))
                                    st.session_state[f"edit_mode_{row['id']}"] = False
                                    st.success("تم التحديث بنجاح!"); st.rerun()

    # --- القسم 2: البحث الذكي العالمي (حل مشكلة عدم العمل) ---
    elif menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الذكي للقطع الأثرية")
        up = st.file_uploader("ارفع صورة القطعة للتحليل والبحث في النت", type=['jpg', 'png', 'jpeg'])
        
        if up:
            img = Image.open(up).convert('RGB')
            st.image(img, width=300, caption="القطعة المرفوعة")
            
            if st.button("🚀 تحليل شامل وبحث عالمي"):
                with st.spinner("جاري تشغيل محرك الذكاء الاصطناعي..."):
                    proc, mod = load_ai()
                    if proc and mod:
                        inputs = proc(img, return_tensors="pt")
                        out = mod.generate(**inputs, max_new_tokens=40)
                        res_text = proc.decode(out, skip_special_tokens=True)
                        
                        # ترميز النص للبحث في الويب
                        clean_q = str(res_text).strip()
                        encoded_q = urllib.parse.quote_plus(clean_q)
                        
                        st.success(f"✅ تم التعرف على: {clean_q}")
                        st.divider()
                        st.subheader("🌐 روابط البحث المباشرة:")
                        col_a, col_b = st.columns(2)
                        col_a.link_button("🛒 أسعار eBay (Sold)", f"https://www.ebay.com{encoded_q}&LH_Sold=1")
                        col_b.link_button("🔍 صور Google Lens", f"https://www.google.com{encoded_q}&tbm=isch")
                    else:
                        st.error("عذراً، المحرك الذكي يواجه ضغطاً على السيرفر، حاول مرة أخرى.")

    # --- القسم 3: إضافة قطعة جديدة ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add_new"):
            st.subheader("إضافة قطعة جديدة للمخزن")
            f_id = st.text_input("ID / كود القطعة")
            f_n = st.text_input("اسم القطعة")
            f_p = st.number_input("السعر")
            f_i = st.file_uploader("صورة القطعة")
            f_d = st.text_area("وصف إضافي")
            if st.form_submit_button("💾 حفظ في القاعدة"):
                if f_id and f_i:
                    path = os.path.join(IMG_FOLDER, f"{f_id}.jpg")
                    with open(path, "wb") as f: f.write(f_i.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (f_id, f_n, f_d, f_p, path))
                    st.success("تم الحفظ بنجاح!"); st.rerun()
                else: st.warning("يرجى إدخال الكود والصورة.")

    # --- القسم 4: التقارير ---
    elif menu == "التقارير 📊":
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button("📥 تحميل ملف إكسيل", towrite.getvalue(), "gallery_report.xlsx")
