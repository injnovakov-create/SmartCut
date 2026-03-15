import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Интерактивна таблица: Кликни два пъти върху клетка за редакция. Маркирай ред вляво и натисни Delete (Кошче) за изтриване.")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- ПОМОЩНА ФУНКЦИЯ ЗА ЗАПИС ---
def add_item(modul, detail, count, l, w, kant, flader, note=""):
    return {
        "Модул": modul, 
        "Детайл": detail, 
        "Брой": count, 
        "L": l, 
        "W": w, 
        "Кант": kant, 
        "Фладер": flader, 
        "Забележка": note
    }

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=40)
    
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Тип модул", [
        "Шкаф Мивка", 
        "Горен Шкаф", 
        "Стандартен Долен", 
        "Шкаф 3 Чекмеджета"
    ])
    
    name = st.text_input("Име/№ на модула", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    
    runner_len = 500
    if tip == "Шкаф 3 Чекмеджета":
        runner_len = st.number_input("Дължина водач Blum (мм)", value=500, step=50)
        
    d = st.number_input("Дълбочина (D) страници", value=550)
    flader = st.selectbox("Шарка (Фладер)", ["Няма", "Да (по L)", "Да (по W)"])

    if st.button("➕ Добави към списъка"):
        new_items = []
        
        h_stranica = 742 
        h_shkaf_korpus = h_stranica + deb 
        h_vrata_standart = h_shkaf_korpus - fuga_obshto
        w_vrata = (w/2) - (fuga_obshto/2)

        if tip == "Шкаф Мивка":
            new_items.append(add_item(name, "Дъно", 1, w, 480, "1д", flader))
            new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", flader))
            new_items.append(add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", flader))
            new_items.append(add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader))
            
        elif tip == "Стандартен Долен":
            new_items.append(add_item(name, "Дъно", 1, w, 520, "1д", flader))
            new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", flader))
            new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader))
            new_items.append(add_item(name, "Рафт", 1, w-(2*deb), 510, "1д", flader))
            new_items.append(add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader))

        elif tip == "Горен Шкаф":
            h_goren = 720
            new_items.append(add_item(name, "Страница", 2, h_goren, 300, "1д", flader))
            new_items.append(add_item(name, "Дъно/Таван", 2, w-(2*deb), 300, "1д", flader))
            new_items.append(add_item(name, "Врата", 2, h_goren-fuga_obshto, w_vrata, "4 страни", flader))
            
        elif tip == "Шкаф 3 Чекмеджета":
            new_items.append(add_item(name, "Дъно", 1, w, 520, "1д", flader))
            new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", flader))
            new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader))
            
            w_chelo = w - fuga_obshto
            block_note = "В БЛОК" if flader != "Няма" else ""
            
            new_items.append(add_item(name, "Чело горно", 1, 180-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            new_items.append(add_item(name, "Чело средно", 1, 250-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            new_items.append(add_item(name, "Чело долно", 1, 330-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            
            w_cargi = w - (2*deb) - 49
            l_stranici_chek = runner_len - 10
            
            new_items.append(add_item(name, "Царги чекм. 1", 2, w_cargi, 80, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 1", 2, l_stranici_chek, 80+15, "2д", flader))
            
            new_items.append(add_item(name, "Царги чекм. 2", 2, w_cargi, 160, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 2", 2, l_stranici_chek, 160+15, "2д", flader))
            
            new_items.append(add_item(name, "Царги чекм. 3", 2, w_cargi, 200, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 3", 2, l_stranici_chek, 200+15, "2д", flader))

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")
        st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic",
            use_container_width=True,
            key="editor"
        )
        
        st.session_state.order_list = edited_df.to_dict('records')
        
        csv = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Свали за Excel",
            data=csv,
            file_name="razkroi_vitya_blum.csv",
            mime="text/csv",
        )
        
        try:
            total_m2 = (pd.to_numeric(edited_df['L']) * pd.to_numeric(edited_df['W']) * pd.to_numeric(edited_df['Брой'])).sum() / 1000000
            st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
        except:
            st.warning("Въведи валидни числа за размерите, за да се изчисли площта.")
    else:
        st.info("Списъкът е празен. Добави първия си модул!")
