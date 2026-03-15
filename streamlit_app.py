import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Витя-М: Софтуер за Мебели", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ Витя-М: Конструктор на Модули v1.0")
st.info("Добре дошъл, Викторе! Тук твоите скици стават готови таблици за разкрой.")

# Инициализиране на списъка с детайли, ако не съществува
if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- СТРАНИЧНО МЕНЮ (НАСТРОЙКИ) ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    st.write("Промени тези стойности и всички сметки ще се обновят.")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга на врати (мм)", value=4)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=38)
    
    if st.button("Изчисти цялата поръчка"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📝 Добави нов модул")
    tip = st.selectbox("Избери тип", ["Шкаф Мивка", "Горен Шкаф", "Чекмедже (Kasa)"])
    
    name = st.text_input("Име на модула (напр. Долен 1)", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    h = st.number_input("Височина (H) в мм", value=870)
    d = st.number_input("Дълбочина (D) в мм", value=550)

    if st.button("➕ Добави към списъка"):
        new_items = []
        if tip == "Шкаф Мивка":
            # Логика Виктор
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
            
        st.session_state.order_list.extend(new_items)
        st.success("Добавено!")

with col2:
    st.subheader("📋 Списък за разкрой (Word/Excel готовност)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.table(df)
        
        # Изчисляване на площ
        total_m2 = (df['L'] * df['W'] * df['Брой']).sum() / 1000000
        st.metric("Обща площ ПДЧ", f"{total_m2:.2f} м2")
        st.write("💡 Можеш да копираш тази таблица директно в Word или Excel.")
    else:
        st.write("Списъкът е празен. Добави модул отляво.")
