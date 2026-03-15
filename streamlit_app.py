import streamlit as st
import pandas as pd

# Настройки на страницата
st.set_page_config(page_title="Витя-М: Поръчка за Разкрой", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏭 Витя-М: Генератор за Разкрой")

# Инициализиране на паметта за списъка
if 'order_list' not in st.session_state:
    st.session_state.order_list = []

# --- ПОМОЩНА ФУНКЦИЯ (Гарантира, че няма да има KeyError) ---
def suzdai_red(ploskost, no, detail, l, w, flader, br, d1, d2, sh1, sh2, zabelejka):
    return {
        "Плоскост": ploskost,
        "№": no,
        "Детайл": detail,
        "Дължина": int(l),
        "Ширина": int(w),
        "Фладер": flader,
        "Бр": int(br),
        "Д1": d1,
        "Д2": d2,
        "Ш1": sh1,
        "Ш2": sh2,
        "Забележка": zabelejka
    }

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    dekor = st.text_input("Плоскост (Декор)", value="U899")
    deb_pdch = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга (мм)", value=4)
    kraka_h = st.number_input("Височина крака (мм)", value=100)
    plot_h = st.number_input("Дебелина плот (мм)", value=38)
    
    st.divider()
    if st.button("🗑️ ИЗЧИСТИ ВСИЧКО"):
        st.session_state.order_list = []
        st.rerun()

# --- ОСНОВЕН ЕКРАН ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("➕ Добави Модул")
    tip = st.selectbox("Тип модул", ["Шкаф Мивка", "Горен Шкаф", "Чекмедже (Каса)"])
    modul_no = st.text_input("№ / Име на модула", value="1")
    
    w_input = st.number_input("Ширина (W)", value=600)
    h_input = st.number_input("Височина (H)", value=870)
    d_input = st.number_input("Дълбочина (D)", value=550)

    if st.button("🚀 ГЕНЕРИРАЙ ДЕТАЙЛИ"):
        new_items = []
        
        if tip == "Шкаф Мивка":
            h_str = h_input - kraka_h - plot_h
            # Параметри: Плоскост, №, Детайл, Дължина, Ширина, Фладер, Бр, Д1, Д2, Ш1, Ш2, Забележка
            new_items.append(suzdai_red(dekor, modul_no, "ДЪНО", w_input, d_input, 1, 1, 1, "", "", "", tip))
            new_items.append(suzdai_red(dekor, modul_no, "СТР", h_str, d_input, 1, 2, 1, "", "", "", tip))
            new_items.append(suzdai_red(dekor, modul_no, "БЛЕНДА", w_input-(2*deb_pdch), 112, 1, 2, 1, "", "", "", tip))
            new_items.append(suzdai_red(dekor, modul_no, "ВР", h_str+15, (w_input/2)-(fuga/2), 1, 2, 1, 1, 1, 1, "Лице 2мм"))

        elif tip == "Горен Шкаф":
            new_items.append(suzdai_red(dekor, modul_no, "СТР", h_input, d_input, 1, 2, 1, 1, 1, "", tip))
            new_items.append(suzdai_red(dekor, modul_no, "ДЪНО/Т", w_input-(2*deb_pdch), d_input, 1, 2, 1, "", "", "", tip))
            new_items.append(suzdai_red(dekor, modul_no, "РАФТ", w_input-(2*deb_pdch), d_input-10, 1, 1, 1, "", "", "", "Вътрешен"))
            new_items.append(suzdai_red(dekor, modul_no, "ВР", h_input-fuga, (w_input/2)-(fuga/2), 1, 2, 1, 1, 1, 1, "Лице 2мм"))

        elif tip == "Чекмедже (Каса)":
            kasa_w = (w_input - 36) - 26 # Светъл отвор минус 26мм за водачи
            new_items.append(suzdai_red(dekor, modul_no, "ЧЕЛО Ч", kasa_w - 36, 150, 1, 2, 1, "", "", "", "Каса"))
            new_items.append(suzdai_red(dekor, modul_no, "СТР Ч", d_input - 10, 150, 1, 2, 1, "", "", "", "Каса"))

        # Добавяме новите детайли към общия списък
        st.session_state.order_list.extend(new_items)
        st.rerun()

with col2:
    st.subheader("📝 Текуща поръчка")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        
        # Подреждаме колоните ТОЧНО като в твоя Excel
        columns_order = ["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[columns_order]
        
        # Показваме таблицата
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Смятане на площ
        area = (df['Дължина'] * df['Ширина'] * df['Бр']).sum() / 1000000
        st.info(f"📊 **Обща площ ПДЧ:** {area:.2f} m² | **Ориентировъчно плоскости:** {area/5.8:.1f} бр.")
        
        # Експорт бутон
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 СВАЛИ КАТО EXCEL (CSV)", csv, "razkroi_vitya.csv", "text/csv")
    else:
        st.write("Списъкът е празен. Добави първия модул отляво.")
