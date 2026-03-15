import streamlit as st
import pandas as pd

st.set_page_config(page_title="Витя-М: Пълна Система", layout="wide")

# Дизайн
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; background-color: #2e7d32; color: white; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

st.title("🚀 Витя-М: Професионален Конструктор v3.0 (Пълна версия)")

# --- СТРАНИЧНО МЕНЮ (НАСТРОЙКИ И ФИНАНСИ) ---
with st.sidebar:
    st.header("⚙️ Технически Настройки")
    dekor = st.text_input("Декор (Колона А)", value="U899")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга врати (мм)", value=4)
    kraka = st.number_input("Височина крака (мм)", value=100)
    plot = st.number_input("Дебелина плот (мм)", value=38)
    
    st.divider()
    st.header("💰 Финанси и Материали")
    cena_pdch = st.number_input("Цена ПДЧ (лв/м2)", value=25.0)
    dni_proekt = st.number_input("Време за проекта (дни)", value=15)
    
    # Автоматична стратегия за разходите
    razhod_naem_konsumativi_eur = (dni_proekt / 15.0) * 300
    st.info(f"Калкулиран стандартен разход 'Наем и консумативи': **{razhod_naem_konsumativi_eur:.0f} €**")
    
    st.divider()
    if st.button("🗑️ ИЗЧИСТИ ЦЯЛАТА ПОРЪЧКА"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ПАНЕЛ ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📦 Конструктор на Модули")
    tip = st.selectbox("Избери тип", ["Шкаф Мивка", "Горен Шкаф", "Блок Чекмеджета (3 бр.)"])
    modul_id = st.text_input("№ на модул", value="1")
    
    w = st.number_input("Ширина (W)", value=600)
    h = st.number_input("Височина (H)", value=870)
    d = st.number_input("Дълбочина (D)", value=550)
    
    if tip == "Блок Чекмеджета (3 бр.)":
        vodač = st.selectbox("Тип водачи", ["Стандартни съчмени (-26мм)", "Blum Tandembox / Antaro (-75мм)"])
        h_malko = st.number_input("Височина малко чело", value=160)

    if st.button("➕ ДОБАВИ В ТАБЛИЦАТА"):
        new_items = []
        
        # 1. ЛОГИКА ЗА ШКАФ МИВКА
        if tip == "Шкаф Мивка":
            h_str = h - kraka - plot
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ДЪНО", "Дължина": w, "Ширина": d, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "СТР", "Дължина": h_str, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "БЛЕНДА", "Дължина": w-(2*deb), "Ширина": 112, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Отпред/Отзад"})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ВР", "Дължина": h_str+15, "Ширина": (w/2)-(fuga/2), "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице"})
            
        # 2. ЛОГИКА ЗА ГОРЕН ШКАФ
        elif tip == "Горен Шкаф":
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "СТР", "Дължина": h, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ДЪНО/ТАВАН", "Дължина": w-(2*deb), "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": tip})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "РАФТ", "Дължина": w-(2*deb), "Ширина": d-10, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Вътрешен"})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ВР", "Дължина": h-fuga, "Ширина": (w/2)-(fuga/2), "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице"})

        # 3. ЛОГИКА ЗА БЛОК ЧЕКМЕДЖЕТА (Пълна детайлизация)
        elif tip == "Блок Чекмеджета (3 бр.)":
            h_str = h - kraka - plot
            svetlo_w = w - (2*deb)
            
            # Корпус
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ДЪНО", "Дължина": w, "Ширина": d, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Корпус"})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "СТР", "Дължина": h_str, "Ширина": d, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Корпус"})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "БЛЕНДА", "Дължина": w-(2*deb), "Ширина": 112, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Корпус"})
            
            # Чела
            h_goliamo = h_str - (2 * h_malko) - (3 * fuga) + 15
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ЧЕЛО МАЛКО", "Дължина": h_malko, "Ширина": w-fuga, "Фладер": 1, "Бр": 2, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице"})
            new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ЧЕЛО ГОЛЯМО", "Дължина": h_goliamo, "Ширина": w-fuga, "Фладер": 1, "Бр": 1, "Д1": 1, "Д2": 1, "Ш1": 1, "Ш2": 1, "Забележка": "Лице"})
            
            # Изчисления за самите чекмеджета спрямо водача
            if "Стандартни" in vodač:
                kasa_w = svetlo_w - 26
                # Предно/Задно парче на касата
                new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ГР/ЧЕЛО КАСА", "Дължина": kasa_w-(2*deb), "Ширина": 100, "Фладер": 1, "Бр": 6, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Вътрешни"})
                # Страници на касата
                new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "СТР КАСА", "Дължина": d-10, "Ширина": 100, "Фладер": 1, "Бр": 6, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Вътрешни"})
            elif "Blum" in vodač:
                duno_w = svetlo_w - 75
                duno_l = d - 24
                new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ДЪНО ЧЕКМЕДЖЕ", "Дължина": duno_l, "Ширина": duno_w, "Фладер": 0, "Бр": 3, "Д1": "", "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "ПДЧ 16мм/18мм"})
                new_items.append({"Плоскост": dekor, "№": modul_id, "Детайл": "ГРЪБ ЧЕКМЕДЖЕ", "Дължина": svetlo_w - 87, "Ширина": 84, "Фладер": 1, "Бр": 3, "Д1": 1, "Д2": "", "Ш1": "", "Ш2": "", "Забележка": "Гръбчета Blum"})

        st.session_state.order_list.extend(new_items)
        st.success("Детайлите са пресметнати и добавени!")

with col2:
    st.subheader("📋 Експорт към Пакетен Циркуляр")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        cols = ["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        
        # Показваме таблицата в правилния формат
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        
        # Изчисляване на площ и цена
        total_m2 = (df['Дължина'] * df['Ширина'] * df['Бр']).sum() / 1000000
        cena_mat = total_m2 * cena_pdch
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("📊 Общо Площ ПДЧ", f"{total_m2:.2f} м2")
        col_m2.metric("💳 Цена ПДЧ за поръчката", f"{cena_mat:.2f} лв")
        
        # Експорт бутон
        csv = df[cols].to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 СВАЛИ КАТО ФАЙЛ ЗА РАЗКРОЙ", csv, "Porychka_Razkroi.csv", "text/csv")
    else:
        st.info("Въведи размери и добави модул, за да генерираш таблицата.")
