import streamlit as st
import os
import sqlite3
from PIL import Image
import numpy as np
import faiss
import torch
from transformers import CLIPModel, CLIPProcessor 
import requests # تم إضافة مكتبة requests للاتصال بالإنترنت
import json # لإدارة بيانات JSON الراجعة من الـ API

# --- 1. إعدادات المسارات وقاعدة البيانات ---
DB_NAME = 'gallery.db'
IMG_FOLDER = "images"

if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS antiques
                 (id TEXT PRIMARY KEY, name TEXT, description TEXT, 
                  price REAL, image_path TEXT)''')
    conn.commit()
    conn.close()

# ... (باقي دوال add_antique, delete_antique, get_all_antiques زي ما هي) ...
def add_antique(id, name, desc, price, img_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO antiques VALUES (?, ?, ?, ?, ?)", 
                  (id, name, desc, price, img_path))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_antique(id, img_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM antiques WHERE id=?", (id,))
    conn.commit()
    conn.close()
    if os.path.exists(img_path):
        os.remove(img_path)

def get_all_antiques():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, description, price, image_path FROM antiques")
    items = c.fetchall()
    conn.close()
    return items

# --- 2. محرك الذكاء الاصطناعي (CLIP) ---
@st.cache_resource
def load_clip_model():
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to("cpu")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32") 
    return model, processor

model, processor = load_clip_model()

def get_image_embedding(image_source):
    if isinstance(image_source, str):
        image = Image.open(image_source).convert("RGB")
    else:
        image = image_source.convert("RGB")
    inputs = processor(images=image, text=["an antique item"], return_tensors="pt").to("cpu")
    with torch.no_grad():
        image_features = model.get_image_features(inputs["pixel_values"])
    return image_features.numpy().flatten().astype('float32')

# --- 3. دالة البحث والتقييم عبر الإنترنت (جديدة) ---
def search_internet_for_price(image_file):
    # ***************** هام جداً *****************
    # هذا مجرد كود توضيحي (Mockup) لطريقة عمل الـ API
    # APIs زي SerpApi أو Google Custom Search مدفوعة وبتحتاج مفتاح (API Key)
    # عشان الكود ده يشتغل بجد، لازم تشترك في خدمة API وتعدل الكود
    # عشان نختبره دلوقتي، هنرجع قيمة وهمية
    st.warning("جاري البحث عن أسعار في السوق العالمي... (هذه النتيجة اختبارية)")
    
    # محاكاة لنتيجة بحث ناجحة
    return {
        "success": True,
        "estimated_price": 5500.00,
        "currency": "EGP",
        "match_link": "https://www.example-auction-house.com"
    }

# --- 4. واجهة البرنامج (UI) ---
st.set_page_config(page_title="جاليري التحف الذكي", layout="wide")
init_db()

st.sidebar.title("💎 إدارة الأنتيكات")
menu = ["إضافة تحفة جديدة", "عرض المخزن", "البحث الذكي", "البحث والتقييم العالمي"]
choice = st.sidebar.selectbox("القائمة", menu)

# ... (أقسام "إضافة تحفة" و "عرض المخزن" زي ما هي) ...
if choice == "إضافة تحفة جديدة":
    st.header("✨ تسجيل قطعة جديدة")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            ant_id = st.text_input("كود التحفة (ID)")
            ant_name = st.text_input("اسم القطعة")
        with col2:
            ant_price = st.number_input("التقدير المادي (EGP)", min_value=0.0)
            ant_img = st.file_uploader("صورة القطعة", type=['jpg', 'png', 'jpeg'])
        ant_desc = st.text_area("وصف التفاصيل")
        
        if st.form_submit_button("حفظ في الجاليري"):
            if ant_img and ant_id and ant_name:
                img_path = os.path.join(IMG_FOLDER, f"{ant_id}.jpg")
                with open(img_path, "wb") as f:
                    f.write(ant_img.getbuffer())
                if add_antique(ant_id, ant_name, ant_desc, ant_price, img_path):
                    st.success(f"تم حفظ {ant_name} بنجاح!")
                else:
                    st.error("الكود مكرر! اختر كود مختلف.")
            else:
                st.warning("برجاء رفع صورة وإدخال البيانات الأساسية.")

elif choice == "عرض المخزن":
    st.header("🖼️ معرض المقتنيات")
    items = get_all_antiques()
    if items:
        cols = st.columns(3)
        for idx, item in enumerate(items):
            id, name, desc, price, img_path = item
            with cols[idx % 3]:
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                    st.subheader(name)
                    st.write(f"💰 **السعر:** {price:,.2f} EGP")
                    with st.expander("خيارات"):
                        st.write(f"🆔 {id}")
                        st.write(desc)
                        if st.button(f"🗑️ حذف", key=f"del_{id}"):
                            delete_antique(id, img_path)
                            st.rerun()
                st.markdown("---")
    else:
        st.info("لا توجد تحف مسجلة حالياً.")

# ... (قسم البحث الذكي المحلي زي ما هو) ...
elif choice == "البحث الذكي":
    st.header("🔍 البحث بصورة مشابهة")
    uploaded_file = st.file_uploader("ارفع صورة للبحث عن مثيل لها محلياً", type=['jpg','png','jpeg'])
    # ... (باقي كود البحث المحلي) ...
    if uploaded_file:
        all_items = get_all_antiques()
        if all_items:
            with st.spinner('جاري البحث في القاعدة المحلية...'):
                try:
                    embeddings = []
                    item_data_map = []
                    for item in all_items:
                        path = item[4] # مسار الصورة
                        if os.path.exists(path):
                            embeddings.append(get_image_embedding(path))
                            item_data_map.append(item)
                    
                    if embeddings:
                        embeddings_np = np.array(embeddings)
                        d = embeddings_np.shape[1]
                        index = faiss.IndexFlatL2(d)
                        index.add(embeddings_np)
                        
                        query_img = Image.open(uploaded_file)
                        query_vec = get_image_embedding(query_img).reshape(1, -1)
                        
                        D, I = index.search(query_vec, k=min(3, len(item_data_map)))
                        
                        st.success("أقرب النتائج المطابقة محلياً:")
                        cols_res = st.columns(len(I[0]))
                        for rank, idx in enumerate(I[0]):
                            if idx != -1:
                                matched_item_data = item_data_map[idx]
                                id, name, desc, price, img_path = matched_item_data
                                similarity_score = max(0, (1 - (D[0][rank] / (d**0.5)))) * 100 

                                with cols_res[rank]:
                                    st.image(img_path, caption=f"تشابه: {similarity_score:.1f}%", use_container_width=True)
                                    st.write(f"**{name}**")
                                    st.write(f"السعر: {price:,.2f} EGP")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء البحث المحلي: {e}")
        else:
            st.warning("المخزن فارغ! لا يوجد صور للمقارنة.")


# --- 5. القسم الجديد: البحث العالمي والتقييم ---
elif choice == "البحث والتقييم العالمي":
    st.header("🌍 التقييم العالمي عبر الإنترنت")
    uploaded_file_global = st.file_uploader("ارفع صورة للبحث عن سعرها عالمياً", type=['jpg','png','jpeg'])

    if uploaded_file_global:
        if not uploaded_file_global.name.lower().endswith(('.png', '.jpg', '.jpeg')):
             st.error("الرجاء رفع ملف صورة صالح.")
        else:
            with st.spinner('جاري البحث على الإنترنت... قد يستغرق الأمر بعض الوقت.'):
                # هنا بنستخدم الدالة الوهمية
                result = search_internet_for_price(uploaded_file_global) 
                
                if result.get("success"):
                    st.success("🎉 تم العثور على نتائج عالمية!")
                    st.image(uploaded_file_global, width=300)
                    st.markdown(f"**السعر التقديري العالمي:** {result['estimated_price']:,.2f} {result['currency']}")
                    st.markdown(f"**رابط المصدر:** [اضغط هنا للتحقق]({result['match_link']})")
                    st.info("هذا التقييم يعتمد على بيانات السوق العالمية في الوقت الحالي.")
                else:
                    st.error("عفواً، لم نتمكن من العثور على سعر تقديري لهذه القطعة على الإنترنت حالياً.")

