import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Конфигурация Витя-М: Blum Tandem чекмеджета, Фладер и рязане 'в блок'.")

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
    fuga_obshto = st.number_input("Фуга на врати/чела (мм)", value=3.0)
    kant_otstyp_w = st.number_input("Отстъп кант ширина (мм)", value=3.0)
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
    
    # Показваме дължина на водача само ако е шкаф с чекмеджета
    if tip == "Шкаф 3 Чекмеджета":
        runner_len = st.number_input("Дължина водач Blum (мм)", value=500, step=50)
        
    d = st.number_input("Дълбочина (D) страници", value=550)
    flader = st.selectbox("Шарка (Фладер)", ["Няма", "Да (по L)", "Да (по W)"])

    if st.button("➕ Добави към списъка"):
        new_items = []
        
        # Общи сметки за долни шкафове
        h_stranica = 742 
        h_shkaf_korpus = h_stranica + deb # 760мм
        h_vrata_standart = h_shkaf_korpus - fuga_obshto
        w_vrata = (w/2) - (fuga_obshto/2) - (kant_otstyp_w/2)

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
            # Корпус
            new_items.append(add_item(name, "Дъно", 1, w, 520, "1д", flader))
            new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", flader))
            new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader))
            
            # Чела (с вадене на фугата от твоите точни размери 180, 250, 330)
            w_chelo = w - fuga_obshto - kant_otstyp_w
            block_note = "В БЛОК" if flader != "Няма" else ""
            
            new_items.append(add_item(name, "Чело горно", 1, 180-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            new_items.append(add_item(name, "Чело средно", 1, 250-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            new_items.append(add_item(name, "Чело долно", 1, 330-fuga_obshto, w_chelo, "4 страни", flader, block_note))
            
            # Логика за Blum Tandem
            w_cargi = w - (2*deb) - 49
            l_stranici_chek = runner_len - 10
            
            # Горно чекмедже (80мм)
            new_items.append(add_item(name, "Царги чекм. 1", 2, w_cargi, 80, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 1", 2, l_stranici_chek, 80+15, "2д", flader))
            
            # Средно чекмедже (160мм)
            new_items.append(add_item(name, "Царги чекм. 2", 2, w_cargi, 160, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 2", 2, l_stranici_chek, 160+15, "2д", flader))
            
            # Долно чекмедже (200мм)
            new_items.append(add_item(name, "Царги чекм. 3", 2, w_cargi, 200, "1д", flader))
            new_items.append(add_item(name, "Страници чекм. 3", 2, l_stranici_chek, 200+15, "2д", flader))

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")

with col2:
    st.subheader("📋 Списък за разкрой")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Свали за Excel",
            data=csv,
            file_name="razkroi_vitya_blum.csv",
            mime="text/csv",
        )
        
        total_m2 = (df['L'] * df['W'] * df['Брой']).sum() / 1000000
        st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
    else:
        st.info("Списъкът е празен.")
