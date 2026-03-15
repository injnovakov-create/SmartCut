import streamlit as st
import pandas as pd
import os
from PIL import Image

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Добавено: Автоматично изрязване и показване на скица за всеки избран модул.")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

def add_item(modul, detail, count, l, w, kant, material, flader, note=""):
    return {
        "Модул": modul, "Детайл": detail, "Брой": count, "L": l, "W": w, 
        "Кант": kant, "Материал": material, "Фладер": flader, "Забележка": note
    }

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    st.markdown("---")
    st.header("🎨 Материали и Фладер")
    
    st.markdown("**1. Корпус (Страници, Дъна, Рафтове)**")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло гладко 18мм")
    fl_korpus = st.checkbox("Има фладер - Корпус", value=False)
    val_fl_korpus = "Да" if fl_korpus else "Няма"
    
    st.markdown("**2. Лице (Врати, Чела)**")
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    fl_lice = st.checkbox("Има фладер - Лице", value=True)
    val_fl_lice = "Да" if fl_lice else "Няма"
    
    st.markdown("**3. Чекмеджета (Царги)**")
    mat_chekm = st.text_input("Декор Чекмеджета:", value="Бяло гладко 18мм")
    fl_chekm = st.checkbox("Има фладер - Чекмеджета", value=False)
    val_fl_chekm = "Да" if fl_chekm else "Няма"
    
    st.markdown("**4. Гръб (Фазер)**")
    mat_fazer = st.text_input("Декор Фазер:", value="Бял фазер 3мм")
    
    st.markdown("---")
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    
    icons = {
        "Стандартен Долен": "🗄️",
        "Горен Шкаф": "⬆️",
        "Шкаф Мивка": "🚰",
        "Шкаф 3 Чекмеджета": "🔢",
        "Шкаф Бутилки 15см": "🍾",
        "Шкаф за Фурна": "🍳",
        "Глух Ъгъл (Долен)": "📐"
    }
    
    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons[x]} {x}")
    
    # --- МАГИЯТА ЗА КАРТИНКИТЕ ---
    try:
        if os.path.exists("sketches.jpg"):
            img = Image.open("sketches.jpg")
            w_img, h_img = img.size
            step = w_img / 7 # Режем на 7 равни части
            
            # Индекси според подредбата в твоята картинка (отляво надясно)
            cabinet_index = {
                "Стандартен Долен": 0,
                "Горен Шкаф": 1,
                "Шкаф Мивка": 2,
                "Шкаф 3 Чекмеджета": 3,
                "Шкаф Бути
