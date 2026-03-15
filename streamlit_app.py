import streamlit as st
import pandas as pd

st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Добре дошъл, Викторе! Твоят личен инструмент за автоматичен разкрой.")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга на врати (мм)", value=4)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=38)
    
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []
        st.rerun()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Избери тип", ["Шкаф Мивка", "Горен Шкаф", "Чекмедже (Kasa)"])
    
    name = st.text_input("Име на модула", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    h = st.number_input("Височина (H) в мм", value=870)
    d = st.number_input("Дълбочина (D) в мм", value=550)

    if st.button("➕ Добави към списъка"):
        new_items = []
        if tip == "Шкаф Мивка":
            h_stranica = h - kraka - plot
            new_items.append({"Детайл": f"Дъно ({name})", "Брой": 1, "L": w, "W": d, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Страница ({name})", "Брой": 2, "L": h_stranica, "W": d, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Бленда ({name})", "Брой": 2, "L": w-(2*deb), "W": 112, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Врата ({name})", "Брой": 2, "L": h_stranica+15, "W": (w/2)-(fuga/2), "Кант": "2д+2к (2.0)"})
        
        elif tip == "Горен Шкаф":
            new_items.append({"Детайл": f"Страница ({name})", "Брой": 2, "L": h, "W": d, "Кант": "2д+1к (0.8)"})
            new_items.append({"Детайл": f"Дъно/Таван ({name})", "Брой": 2, "L": w-(2*deb), "W": d, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Рафт ({name})", "Брой": 1, "L": w-(2*deb), "W": d-10, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Врата ({name})", "Брой": 2, "L": h-fuga, "W": (w/2)-(fuga/2), "Кант": "2д+2к (2.0)"})
            
        elif tip == "Чекмедже (Kasa)":
            kasa_w = (w - (2*deb)) - 26
            new_items.append({"Детайл": f"Чело/Гръб чекмедже", "Брой": 2, "L": kasa_w - (2*deb), "W": 150, "Кант": "1д (0.8)"})
            new_items.append({"Детайл": f"Страница чекмедже", "Брой": 2, "L": d, "W": 150, "Кант": "1д (0.8)"})

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")

with col2:
    st.subheader("📋 Списък за разкрой")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.table(df)
        total_m2 = (df['L'] * df['W'] * df['Брой']).sum() / 1000000
        st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
    else:
        st.info("Списъкът е празен.")
