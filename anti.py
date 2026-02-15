import streamlit as st
import os, sqlite3, pandas as pd, io, urllib.parse
from PIL import Image

# --- الإعدادات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- محرك الذكاء الاصطناعي ---
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

# --- الواجهة الرئيسية ---
st.set_page_config(page_title="نظام الجاليري PRO", layout="wide")

# (نظام الحماية admin / 1234)
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    with st.form("Login"):
        u = st.text_input("المستخدم"); p = st.text_input("السر", type="password")
        if st.form_submit_button("دخول"):
            if u == "admin" and p == "1234": st.session_state["auth"] = True; st.rerun()
            else: st.error("خطأ!")
else:
    st.sidebar.title("🏛️ لوحة التحكم")
    # تأكد من وجود "البحث الذكي (AI)" في هذه القائمة
    menu = st.sidebar.radio("القائمة", ["عرض المخزن 🖼️", "البحث الذكي (AI) 🤖", "إضافة قطعة ✨", "التقارير والإكسيل 📊"])

    if menu == "البحث الذكي (AI) 🤖":
        st.header("🤖 خبير التقييم والبحث العالمي")
        up = st.file_uploader("ارفع صورة للتحليل", type=['jpg', 'png', 'jpeg'])
        if up:
            st.image(up, width=300)
            if st.button("🚀 ابدأ التحليل والبحث"):
                with st.spinner("جاري الفحص..."):
                    proc, mod = load_ai()
                    raw = Image.open(up).convert('RGB')
                    out = mod.generate(**proc(raw, return_tensors="pt"))
                    desc = proc.decode(out, skip_special_tokens=True)
                    st.success(f"التعرف على: {desc}")
                    q = urllib.parse.quote(desc)
                    st.link_button("نتائج eBay 🛒", f"https://www.ebay.com{q}")
                    st.link_button("نتائج Google 🔍", f"https://www.google.com{q}&tbm=isch")

    elif menu == "عرض المخزن 🖼️":
        st.header("🖼️ المقتنيات الحالية")
        # (باقي كود العرض المحلي من قاعدة البيانات)
