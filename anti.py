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
                            if os.path.exists(row['image_path']): os.remove(row['image_path'])
                            st.rerun()
                        
                        if c2.button(f"⚙️ تعديل", key=f"edit_btn_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = True

                        if st.session_state.get(f"edit_mode_{row['id']}", False):
                            with st.form(f"form_{row['id']}"):
                                new_n = st.text_input("الاسم الجديد", row['name'])
                                new_p = st.number_input("السعر الجديد", value=float(row['price']))
                                new_d = st.text_area("الوصف الجديد", row['description'])
                                # إضافة خيار رفع صورة جديدة
                                new_img = st.file_uploader("تحديث الصورة (اختياري)", type=['jpg', 'png', 'jpeg'], key=f"img_{row['id']}")
                                
                                if st.form_submit_button("✅ حفظ التغييرات شاملة الصورة"):
                                    img_path = row['image_path']
                                    if new_img: # إذا رفع المستخدم صورة جديدة
                                        with open(img_path, "wb") as f:
                                            f.write(new_img.getbuffer())
                                    
                                    with sqlite3.connect(DB_NAME) as conn:
                                        conn.execute("UPDATE antiques SET name=?, price=?, description=? WHERE id=?", 
                                                     (new_n, new_p, new_d, row['id']))
                                    
                                    st.session_state[f"edit_mode_{row['id']}"] = False
                                    st.success("تم تحديث البيانات والصورة بنجاح!")
                                    st.rerun()
