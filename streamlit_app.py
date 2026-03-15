import streamlit as st
import pandas as pd

st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Интерактивна таблица и вграден бърз разкрой (Плоча 2800x2070, Сряз 8мм, Окрайчване 8мм).")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

def add_item(modul, detail, count, l, w, kant, flader, note=""):
    return {"Модул": modul, "Детайл": detail, "Брой": count, "L": l, "W": w, "Кант": kant, "Фладер": flader, "Забележка": note}

with st.sidebar:
    st.header("⚙️ Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.rerun()

col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Тип модул", ["Шкаф Мивка", "Горен Шкаф", "Стандартен Долен", "Шкаф 3 Чекмеджета"])
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
            new_items.extend([
                add_item(name, "Дъно", 1, w, 480, "1д", flader),
                add_item(name, "Страница", 2, h_stranica, d, "1д", flader),
                add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", flader),
                add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader)
            ])
        elif tip == "Стандартен Долен":
            new_items.extend([
                add_item(name, "Дъно", 1, w, 520, "1д", flader),
                add_item(name, "Страница", 2, h_stranica, d, "1д", flader),
                add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader),
                add_item(name, "Рафт", 1, w-(2*deb), 510, "1д", flader),
                add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader)
            ])
        elif tip == "Горен Шкаф":
            h_goren = 720
            new_items.
