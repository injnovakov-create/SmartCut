import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Витя-М: Поръчка за Разкрой", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏭 Витя-М: Професионален Генератор за Разкрой")

# Инициализиране на базата данни
if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    dekor = st.text_input("Плоскост (Декор)", value="U899")
    deb_pdch = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга на врати (мм)", value=4)
    kraka_h = st.number_input("Височина крака (мм)", value=100)
    plot_h = st.number_input("Дебелина плот (мм)", value=38)
    
    st.divider()
    if st.button("🗑️ ИЗЧИСТИ ВСИЧКО"):
        st.session_state.order_list = []
        st.rerun()

# --- ВЪВЕЖДАНЕ НА ДАННИ ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("➕ Добави Модул")
    tip = st.selectbox("Тип модул", ["Шкаф Мивка", "Горен Шкаф", "Чекмедже (Kasa)"])
    modul_no = st.text_input("№ / Име на модула", value="1")
    
    w = st.number_input("Ширина (W)", value=600)
    h = st.number_input("Височина (H)", value=870)
    d = st.number_input("Дълбочина (D)", value=550)

    if st.button("🚀 ГЕНЕРИРАЙ ДЕТАЙЛИ"):
        temp_list = []
        
        if tip == "Шкаф Мивка":
            h_str = h - kraka_h - plot_h
            # Име | Дълж | Шир | Бр | Д1 | Д2 | Ш1 | Ш2 | Забележка
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "ДЪНО", "Дължина": w, "Ширина": d, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": 0, "Ш1": 0, "Ш2": 0, "Забележка": tip})
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "СТР", "Дължина": h_str, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 0, "Ш1": 0, "Ш2": 0, "Забележка": tip})
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "БЛЕНДА", "Дължина": w-(2*deb_pdch), "Ширина": 112, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 0, "Ш1": 0, "Ш2": 0, "Забележка": tip})
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "ВР", "Дължина": h_str+15, "Ширина": (w/2)-(fuga/2), "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице 2мм кант"})

        elif tip == "Горен Шкаф":
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "СТР", "Дължина": h, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 0, "Забележка": tip})
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "ДЪНО/Т", "Дължина": w-(2*deb_pdch), "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 0, "Ш1": 0, "Ш2": 0, "Забележка": tip})
            temp_list.append({"Плоскост": dekor, "№": modul_no, "Детайл": "ВР", "Дължина": h-fuga, "Ширина": (w/2)-(fuga/2), "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице 2мм кант"})

        st.session_state.order_list.extend(temp_list)
        st.success(f"Модул {modul_no} е добавен!")

# --- ПОКАЗВАНЕ НА РЕЗУЛТАТА ---
with col2:
    st.subheader("📝 Текуща поръчка")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        # Подредба точно по твоята снимка
        df = df[["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]]
        
        # Интерактивна таблица
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Информация за материали
        area = (df['Дължина'] * df['Ширина'] * df['Бр']).sum() / 1000000
        st.write(f"📊 **Обща площ:** {area:.2f} m² | **Ориентировъчно плоскости:** {area/5.8:.1f} бр.")
        
        # Експорт
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 СВАЛИ КАТО EXCEL (CSV)", csv, "razkroi_vitya.csv", "text/csv")
    else:
        st.info("Добави първия модул, за да видиш таблицата тук.")
