import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse
from PIL import Image
from duckduckgo_search import DDGS

# --- 1. الإعدادات وقاعدة البيانات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS antiques
                     (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                      price REAL, image_path TEXT)''')

# --- 2. محرك الذكاء الاصطناعي والبحث في الويب ---
@st.cache_resource
def load_ai():
    from transformers import BlipProcessor, BlipForConditionalGeneration
    p = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    m = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    return p, m

def web_search(query):
    try:
        with DDGS() as ddgs:
            return
    except Exception as e:
        return []

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

st.set_page_config(page_title="جاليري PRO | إدارة وبحث ذكي", layout="wide")
init_db()

if check_auth():
    st.sidebar.title("🏛️ لوحة التحكم")
    menu = st.sidebar.radio("انتقل إلى:", ["عرض المخزن 🖼️", "تعديل المخزون ⚙️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير 📊"])

    # --- البحث الذكي العالمي المطور ---
    if menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 المحلل الشامل والبحث العالمي")
        up = st.file_uploader("ارفع صورة القطعة للفحص", type=['jpg', 'png', 'jpeg'])
        if up:
            col1, col2 = st.columns([1, 2])
            img = Image.open(up).convert('RGB')
            col1.image(img, caption="الصورة المرفوعة", use_container_width=True)
            
            if st.button("🚀 بدء التحليل والبحث"):
                with st.spinner("جاري تحليل الصورة والبحث في المكتبات والنت..."):
                    proc, mod = load_ai()
                    inputs = proc(img, return_tensors="pt")
                    out = mod.generate(**inputs)
                    res_text = proc.decode(out, skip_special_tokens=True)
                    encoded_q = urllib.parse.quote_plus(res_text)
                    
                    with col2:
                        st.subheader("📝 الوصف المستنتج (AI Caption):")
                        st.success(res_text)
                        
                        st.divider()
                        st.subheader("🌐 نتائج البحث المباشر من الويب:")
                        results = web_search(res_text)
                        for r in results:
                            st.markdown(f"🔗 **[{r['title']}]({r['href']})**")
                            st.caption(r['body'][:150] + "...")
                        
                        st.subheader("📌 روابط بحث سريعة (مصححة):")
                        c1, c2 = st.columns(2)
                        # تصحيح روابط eBay و Google Lens
                        c1.link_button("🛒 البحث في eBay (مباع)", f"https://www.ebay.com{encoded_q}&LH_Sold=1")
                        c2.link_button("🔍 Google Lens Search", f"https://www.google.com{encoded_q}&tbm=isch")

    # --- إدارة المخزون (تعديل الكود، التوصيف، الصورة، السعر) ---
    elif menu == "تعديل المخزون ⚙️":
        st.header("⚙️ تعديل بيانات القطع الحالية")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        
        if df.empty: st.info("المخزن فارغ.")
        else:
            target_id = st.selectbox("اختر كود القطعة المراد تعديلها", df['id'].tolist())
            row = df[df['id'] == target_id].iloc[0]
            
            with st.form("edit_item"):
                st.write(f"### تعديل القطعة: {row['name']}")
                c1, c2 = st.columns(2)
                with c1:
                    new_id = st.text_input("تعديل الكود (ID)", row['id'])
                    new_name = st.text_input("تعديل الاسم", row['name'])
                    new_price = st.number_input("تعديل السعر", value=float(row['price']))
                with c2:
                    new_desc = st.text_area("تعديل التوصيف", row['description'])
                    new_img = st.file_uploader("تحديث الصورة (اتركه فارغاً للاحتفاظ بالصورة الحالية)")
                
                if st.form_submit_button("💾 حفظ التعديلات"):
                    path = row['image_path']
                    if new_img:
                        path = os.path.join(IMG_FOLDER, f"{new_id}.jpg")
                        with open(path, "wb") as f: f.write(new_img.getbuffer())
                    
                    with sqlite3.connect(DB_NAME) as conn:
                        # حذف القديم وإضافة الجديد لضمان تحديث الـ ID بنجاح
                        conn.execute("DELETE FROM antiques WHERE id=?", (target_id,))
                        conn.execute("INSERT INTO antiques VALUES (?,?,?,?,?)", 
                                     (new_id, new_name, new_desc, new_price, path))
                    st.success("تم تحديث البيانات بنجاح!"); st.rerun()

    # --- عرض المخزن ---
    elif menu == "عرض المخزن 🖼️":
        st.header("🖼️ المقتنيات المتوفرة")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        if df.empty: st.warning("المخزن فارغ!")
        else:
            cols = st.columns(3)
            for i, r in df.iterrows():
                with cols[i % 3]:
                    with st.container(border=True):
                        if os.path.exists(r['image_path']): st.image(r['image_path'], use_container_width=True)
                        st.subheader(r['name']); st.caption(r['description'])
                        st.write(f"💰 **{r['price']} $** | كود: `{r['id']}`")
                        if st.button(f"🗑️ حذف", key=f"del_{r['id']}"):
                            with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM antiques WHERE id=?", (r['id'],))
                            if os.path.exists(r['image_path']): os.remove(r['image_path'])
                            st.rerun()

    # --- إضافة قطعة ---
    elif menu == "إضافة قطعة ✨":
        with st.form("add"):
            st.subheader("إضافة قطعة جديدة للمخزن")
            f1, f2 = st.columns(2)
            fid = f1.text_input("كود القطعة (ID)"); fn = f1.text_input("اسم القطعة")
            fp = f2.number_input("السعر"); fi = f2.file_uploader("الصورة")
            fd = st.text_area("التوصيف")
            if st.form_submit_button("💾 حفظ"):
                if fid and fi:
                    path = os.path.join(IMG_FOLDER, f"{fid}.jpg")
                    with open(path, "wb") as f: f.write(fi.getbuffer())
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR REPLACE INTO antiques VALUES (?,?,?,?,?)", (fid, fn, fd, fp, path))
                    st.success("تمت الإضافة!"); st.rerun()

    # --- التقارير ---
    elif menu == "التقارير 📊":
        st.header("📊 إحصائيات المخزون")
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql("SELECT * FROM antiques", conn)
        st.dataframe(df, use_container_width=True)
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("📥 تحميل ملف Excel الكامل", towrite.getvalue(), "inventory_report.xlsx")
