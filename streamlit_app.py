import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

# Заглавие
st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Конфигурация за Витя-М: Врата 757мм, 3 бленди, плитко дъно 480мм.")

# Инициализиране на списъка
if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга на врати (общо мм)", value=3.0)
    kant_otstyp_w = st.number_input("Отстъп кант ширина (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=40)
    
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Тип модул", ["Шкаф Мивка", "Горен Шкаф"])
    
    name = st.text_input("Име/№ на модула", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    h_target = st.number_input("Обща височина (с плот)", value=900)
    d = st.number_input("Дълбочина (D) в мм", value=550)

    if st.button("➕ Добави към списъка"):
        new_items = []
        
        # Логика за Долен Шкаф
        h_stranica = 742 # Фиксирано за обща височина 900
        h_shkaf_korpus = h_stranica + deb # 760мм
        
        # Врата: 760 - 3мм фуга = 757мм височина
        h_vrata = h_shkaf_korpus - fuga_obshto
        # Ширина на вратата: (W/2) - фуга/2 - кант/2
        w_vrata = (w/2) - (fuga_obshto/2) - (kant_otstyp_w/2)

        if tip == "Шкаф Мивка":
            # Детайли за мивка
            new_items.append({"Модул": name, "Детайл": "Дъно", "Брой": 1, "L": w, "W": 480, "Кант": "1д"})
            new_items.append({"Модул": name, "Детайл": "Страница", "Брой": 2, "L": h_stranica, "W": d, "Кант": "1д"})
            new_items.append({"Модул": name, "Детайл": "Бленда", "Брой": 3, "L": w-(2*deb), "W": 112, "Кант": "1д"})
            new_items.append({"Модул": name, "Детайл": "Врата", "Брой": 2, "L": h_vrata, "W": w_vrata, "Кант": "4 страни"})
        
        elif tip == "Горен Шкаф":
            h_goren = 720
            new_items.append({"Модул": name, "Детайл": "Страница", "Брой": 2, "L": h_goren, "W": 300, "Кант": "1д"})
            new_items.append({"Модул": name, "Детайл": "Дъно/Таван", "Брой": 2, "L": w-(2*deb), "W": 300, "Кант": "1д"})
            new_items.append({"Модул": name, "Детайл": "Врата", "Брой": 2, "L": h_goren-fuga_obshto, "W": w_vrata, "Кант": "4 страни"})

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")

with col2:
    st.subheader("📋 Списък за разкрой")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.table(df)
        
        # Най-сигурният начин за сваляне на таблица (CSV формат за Excel)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Свали за Excel",
            data=csv,
            file_name="razkroi_vitya.csv",
            mime="text/csv",
        )
        
        total_m2 = (df['L'] * df['W'] * df['Брой']).sum() / 1000000
        st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
    else:
        st.info("Списъкът е празен. Добави първия си шкаф отляво!")
