import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

# Заглавие на софтуера
st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Добре дошъл, Викторе! Твоят личен инструмент за автоматичен разкрой.")

# Инициализиране на списъка с поръчки
if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- СТРАНИЧНО МЕНЮ (НАСТРОЙКИ) ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга на врати (мм)", value=4)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=38)
    
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
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
            new_items.append({"Детайл": f"Страница ({
