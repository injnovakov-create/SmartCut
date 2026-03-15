import streamlit as st
import pandas as pd

st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Настройки за Витя-М: Шкаф мивка (3 бленди, без гръб) и точни врати.")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга на врати (общо мм)", value=3.0)
    kant_otstyp = st.number_input("Отстъп за кант (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=40)
    
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []
        st.rerun()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Избери тип", ["Шкаф Мивка", "Горен Шкаф"])
    
    name = st.text_input("Име на модула", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    # По подразбиране смятаме за обща височина 900
    h_obshta = st.number_input("Обща височина (с плот)", value=900)
    d = st.number_input("Дълбочина (D) в мм", value=550)

    if st.button("➕ Добави към списъка"):
        new_items = []
        # Изчисления според твоите изисквания
        h_stranica = 742 # Фиксирано според твоята логика (900 - 40 - 100 - 18)
        h_shkaf_bez_kraka = h_stranica + deb # 760мм
        h_vrata = h_shkaf_bez_kraka - fuga_obshto - kant_otstyp

        if tip == "Шкаф Мивка":
            # Специфично дъно 480мм
            new_items.append({"Детайл": f"Дъно ({name})", "Брой": 1, "L": w, "W": 480, "Кант": "1д"})
            new_items.append({"Детайл": f"Страница ({name})", "Брой": 2, "L": h_stranica, "W": d, "Кант": "1д"})
            # 3 бленди
            new_items.append({"Детайл": f"Бленда ({name})", "Брой": 3, "L": w-(2*deb), "W": 112, "Кант": "1д"})
            # Врати
            new_items.append({"Детайл": f"Врата ({name})", "Брой": 2, "L": h_vrata, "W": (w/2)-(fuga_obshto/2)-(kant_otstyp/2), "Кант": "4 страни"})
        
        elif tip == "Горен Шкаф":
            new_items.append({"Детайл": f"Страница ({name})", "Брой": 2, "L": 720, "W": 300, "Кант": "1д"})
            new_items.append({"Детайл": f"Дъно/Таван ({name})", "Брой": 2, "L": w-(2*deb), "W": 300, "Кант": "1д"})
            new_items.append({"Детайл": f"Врата ({name})", "Брой": 2, "L": 720-fuga_obshto, "W": (w/2)-(fuga_obshto/2), "Кант": "4 страни"})

        st.session_state.order_list.extend(new_items)
        st.success(f"Добавен: {name}")

with col2:
    st.subheader("📋 Списък за разкрой")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.table(df)
        total_m2 = (df['L'] * df['W'] * df['Брой']).sum() / 1000000
        st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
    else:
        st.info("Добави модул от менюто вляво.")
