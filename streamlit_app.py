import streamlit as st
import pandas as pd

st.set_page_config(page_title="Витя-М: Поръчка за Разкрой", layout="wide")

st.title("📋 Витя-М: Генератор на таблици за разкрой")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- НАСТРОЙКИ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    dekor = st.text_input("Декор (Плоскост)", value="U899")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга (мм)", value=4)
    if st.button("Изчисти всичко"):
        st.session_state.order_list = []
        st.rerun()

# --- ДОБАВЯНЕ НА МОДУЛИ ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🛠️ Нов модул")
    tip = st.selectbox("Тип", ["Шкаф Мивка", "Горен Шкаф"])
    modul_name = st.text_input("Име/№ на модула", value="1")
    w = st.number_input("Ширина (W)", value=600)
    h = st.number_input("Височина (H)", value=720)
    d = st.number_input("Дълбочина (D)", value=550)

    if st.button("Добави"):
        new_items = []
        # Логика за автоматично попълване на кантовете (H, I, J, K)
        if tip == "Шкаф Мивка":
            h_stranica = h - 100 - 18 # Приемаме 100мм крака
            # Детайл | Дължина | Ширина | Бр | Кант Д1 | Кант Д2 | Кант Ш1 | Кант Ш2
            new_items.append({"Плоскост": dekor, "№": modul_name, "Детайл": "ДЪНО", "Дължина": w, "Ширина": d, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_name, "Детайл": "СТР", "Дължина": h_stranica, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})
        
        elif tip == "Горен Шкаф":
            new_items.append({"Плоскост": dekor, "№": modul_name, "Детайл": "СТР", "Дължина": h, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_name, "Детайл": "ДЪНО/ТАВАН", "Дължина": w-(2*deb), "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})

        st.session_state.order_list.extend(new_items)

with col2:
    st.subheader("📊 Готова Таблица (за копиране)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        # Преподреждаме колоните точно като на снимката
        df = df[["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]]
        st.dataframe(df, use_container_width=True)
        
        # Бутон за сваляне в Excel
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Свали като Excel/CSV", csv, "poruchka_mebeli.csv", "text/csv")
