import streamlit as st
import pandas as pd
import os
import io
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# Настройки на страницата
st.set_page_config(page_title="SMART CUT: Витя-М", layout="wide")

# --- CSS ЗА СБИТ ДИЗАЙН ---
st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }
h1, h2, h3, h4, h5 { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; margin-bottom: 0 !important; }
hr { margin-top: 0.8rem !important; margin-bottom: 0.8rem !important; }
.stButton>button { background-color: #008080 !important; color: white !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; padding: 0.5rem 1rem !important; width: 100%; }
.stButton>button:hover { background-color: #005959 !important; }
[data-testid="stSidebar"] { background-color: #f0fafa !important; }
.stTextInput, .stNumberInput, .stSelectbox, .stRadio { margin-bottom: -0.5rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='font-size: 28px; margin-top: 10px;'>
  🛠️ SMART <span style='color: #FF0000; font-weight: bold; font-style: italic; text-decoration: underline wavy; margin-left: -5px;'>CUT</span>
</h1>
<p style='font-size: 18px; color: gray; margin-top: -10px; margin-bottom: 20px;'><i>оптимизирай умно</i></p>
""", unsafe_allow_html=True)

if 'order_list' not in st.session_state: st.session_state.order_list = []
if 'hardware_list' not in st.session_state: st.session_state.hardware_list = []
if 'modules_meta' not in st.session_state: st.session_state.modules_meta = [] 

# --- ЛОГИКА ЗА ЗАПИС ТОЧНО КАТО В EXCEL ---
def add_item(modul, tip, detail, count, l, w, kant_str, material, flader, note=""):
    thick = 2 if any(x in str(detail).lower() for x in ["врата", "чело", "дублираща"]) else 1
    d1 = d2 = sh1 = sh2 = ""
    k = str(kant_str).lower()
    if "1д" in k: d1 = thick
    if "2д" in k or "4" in k: d1 = thick; d2 = thick
    if "1к" in k or "1ш" in k: sh1 = thick
    if "2к" in k or "2ш" in k or "4" in k: sh1 = thick; sh2 = thick
    return {
        "Плоскост": material, "№": modul, "Тип": tip, "Детайл": detail, "Дължина": l, "Ширина": w, 
        "Фладер": flader, "Бр": count, "Д1": d1, "Д2": d2, "Ш1": sh1, "Ш2": sh2, "Забележка": note
    }

def get_abbrev(detail_name):
    d = str(detail_name).lower()
    if "дублираща" in d: return "ДублСтр"
    if "страница" in d and "чекм" not in d: return "Стр"
    if "дъно/таван" in d: return "Д/Т"
    if "дъно" in d: return "Дън"
    if "таван" in d: return "Тав"
    if "бленда" in d: return "Бл"
    if "рафт тв" in d: return "РфтТв"
    if "рафт подвижен" in d: return "РфтПод"
    if "рафт" in d and "фурна" not in d: return "Рфт"
    if "рафт" in d and "фурна" in d: return "РфтФур"
    if "врата долна" in d: return "ВрДол"
    if "врата горна" in d: return "ВрГор"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело долно" in d: return "ЧелДол"
    if "чело горно" in d: return "ЧГ"
    if "чело средно" in d: return "ЧС"
    if "чело" in d: return "Чело"
    if "царги" in d: return "Цч"
    if "страници чекм" in d: return "Сч"
    return detail_name[:5].capitalize()

def get_module_abbrev(tip):
    t = str(tip).lower()
    if "3 чекмеджета" in t: return "Шк 3 ч-та"
    if "стандартен долен" in t: return "Долен шк"
    if "горен шкаф" in t: return "Горен шк"
    if "шкаф колона" in t: return "Колона"
    if "трети ред" in t: return "3-ти ред"
    if "шкаф за фурна" in t: return "Шк фурна"
    if "шкаф мивка" in t: return "Шк мивка"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18, key="glob_deb")
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0, key="glob_fuga")
    kraka = st.number_input("Височина крака (мм)", value=100, key="glob_kraka")
    
    st.markdown("---")
    st.header("🎨 Материали и Фладер")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло гладко 18мм")
    val_fl_korpus = "Да" if st.checkbox("Има фладер - Корпус", value=False) else "Няма"
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    val_fl_lice = "Да" if st.checkbox("Има фладер - Лице", value=True) else "Няма"
    mat_chekm = st.text_input("Декор Чекмеджета:", value="Бяло гладко 18мм")
    val_fl_chekm = "Да" if st.checkbox("Има фладер - Чекмеджета", value=False) else "Няма"
    mat_fazer = st.text_input("Декор Фазер:", value="Бял фазер 3мм")
    
    st.markdown("---")
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []; st.session_state.hardware_list = []; st.session_state.modules_meta = []; st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    cat_choice = st.radio("Избери категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)

    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {
            "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", 
            "Шкаф Мивка": "🚰", "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", 
            "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"
        }
    else:
        icons = {"Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"}

    tip = st.selectbox("Тип модул", options=list(icons.keys()))
    name = st.text_input("Име/№ на модула", value="1")
    
    # Инициализация на променливи
    w = 600; h = 720; d = 520; vrati_broi = 1; app_type = "Без уреди"; lower_mode = "Врата"; lower_door_h = 718; ch_heights = []; runner_len = 500

    if tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина (W) мм", value=600, key="w_tr")
        h = st.number_input("Височина (H) мм", value=350, key="h_tr")
        d = st.number_input("Дълбочина (D) мм", value=500, key="d_tr")
        vrati_broi = st.radio("Брой врати:", [1, 2], index=0, horizontal=True, key="vr_tr")
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600, key="w_col")
        h_k = st.number_input("Височина корпус мм", value=2040, key="h_col")
        d = st.number_input("Дълбочина (D) мм", value=550, key="d_col")
        app_type = st.radio("Уреди:", ["Без уреди", "Само Фурна", "Фурна + Микровълнова"], horizontal=True, key="app_col")
        lower_mode = st.radio("Долна част:", ["Врата", "До 3 чекмеджета"], horizontal=True, key="low_col")
        if lower_mode == "До 3 чекмеджета":
            num_ch = st.slider("Брой чекмеджета долу:", 1, 3, 2, key="n_ch_col")
            for i in range(num_ch): ch_heights.append(st.number_input(f"Чело {i+1} H", value=360, key=f"ch_col_h_{i}"))
            runner_len = st.number_input("Водач мм", value=500, step=50, key="run_col")
        else: lower_door_h = st.number_input("Височина долна врата мм", value=718, key="low_h_col")
        vrati_broi = st.radio("Брой врати на ред:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_col")
        h = h_k + kraka
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Детайл")
        h = st.number_input("Дължина (L) мм", value=600); d = st.number_input("Ширина (W) мм", value=300); w = deb; custom_count = st.number_input("Брой", value=1)
        custom_kant = st.selectbox("Кант", ["4 страни", "2д+2к", "Без"], index=0); custom_mat_type = st.selectbox("Материал", ["Корпус", "Лице"])
    else:
        w = st.number_input("Ширина (W) мм", value=150 if "Бутилки" in tip else 600, key="w_std")
        if "Горен" in tip: h = st.number_input("H мм", value=720); d = 300
        else: h, d = 742 + kraka + 38, 520
        vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_std")

    if st.button("➕ Добави към списъка"):
        new_items = []
        new_hw = []
        otstyp_f = 4; h_str = 742; h_korp_std = h_str + deb; h_v_std = h_korp_std - fuga_obshto
        
        # Мета за чертежи
        st.session_state.modules_meta.append({"№": name, "Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi, "app_type": app_type, "ld_h": lower_door_h, "lower_type": lower_mode})

        # --- ЛОГИКА ТРЕТИ РЕД (НАДСТРОЙКА) ---
        if tip == "Трети ред (Надстройка)":
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница (вътрешна)", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_f, w - otstyp_f, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата", vrati_broi, h - fuga_obshto, (w/vrati_broi) - fuga_obshto, "4 страни", mat_lice, val_fl_lice)
            ])
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(h)*vrati_broi})

        # --- ЛОГИКА КОЛОНА ---
        elif tip == "Шкаф Колона":
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h - kraka - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - kraka - otstyp_f, w - otstyp_f, "Без", mat_fazer, "Няма")
            ])
            h_f = 595 if "Фурна" in app_type else 0
            h_m = 380 if "Микровълнова" in app_type else 0
            if lower_mode == "До 3 чекмеджета":
                cw = w - (2*deb) - 49; total_low_h = sum(ch_heights)
                for idx, ch_h in enumerate(ch_heights):
                    new_items.append(add_item(name, tip, f"Чело {idx+1}", 1, ch_h-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                    new_items.extend([add_item(name, tip, f"Царги {idx+1}", 2, cw, 160, "1д", mat_chekm, val_fl_chekm),
                                      add_item(name, tip, f"Страници {idx+1}", 2, runner_len-10, 175, "2д", mat_chekm, val_fl_chekm)])
            else:
                total_low_h = lower_door_h
                new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lower_door_h, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
            h_up_v = (h - kraka) - total_low_h - h_f - h_m - (fuga_obshto * 2)
            if h_up_v > 100:
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_up_v, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))

        elif tip == "Нестандартен":
            m_c = mat_korpus if custom_mat_type == "Корпус" else mat_lice
            new_items.append(add_item(name, tip, custom_detail, int(custom_count), h, d, custom_kant, m_c, "Да"))
        
        else: # Стандартни
            if "Горен" in tip:
                new_items.extend([add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                                  add_item(name, tip, "Дъно/Таван", 2, w-2*deb, d, "1д", mat_korpus, val_fl_korpus),
                                  add_item(name, tip, "Врата", vrati_broi, h-fuga_obshto, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice)])
            else:
                new_items.extend([add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                                  add_item(name, tip, "Страница", 2, h_str, d, "1д", mat_korpus, val_fl_korpus),
                                  add_item(name, tip, "Бленда", 2, w-2*deb, 112, "1д", mat_korpus, val_fl_korpus)])
                if "Чекмеджета" in tip:
                    cw = w-2*deb-49
                    for ch_n, ch_h in zip(["Горно", "Средно", "Долно"], [180, 250, 330]):
                        new_items.append(add_item(name, tip, f"Чело {ch_n}", 1, ch_h-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                else:
                    new_items.append(add_item(name, tip, "Врата", vrati_broi, h_v_std, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))

        st.session_state.order_list.extend(new_items); st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=400)
        st.session_state.order_list = edited_df.to_dict('records')
        
        if st.session_state.hardware_list:
            st.markdown("#### 🔩 Обков")
            st.table(pd.DataFrame(st.session_state.hardware_list).groupby("Артикул")["Брой"].sum().reset_index())

        # PDF Бутони
        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            if st.button("📄 Свали PDF Чертежи"):
                pdf_data = generate_technical_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka)
                if pdf_data: st.download_button("📥 ИЗТЕГЛИ PDF", pdf_data, "Cherteji.pdf")
        with col_pdf2:
            if st.button("🏷️ Свали ЕТИКЕТИ"):
                boards, _, _, _ = get_optimized_boards(st.session_state.order_list)
                pdf_labels = generate_labels_pdf(boards)
                if pdf_labels: st.download_button("📥 ИЗТЕГЛИ ЕТИКЕТИ", pdf_labels, "Etiketi.pdf")

# --- ФУНКЦИИ ГЕНЕРИРАНЕ ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    font_path = "Roboto-Regular.ttf"
    try: f_title = ImageFont.truetype(font_path, 80); f_text = ImageFont.truetype(font_path, 50)
    except: f_title = f_text = ImageFont.load_default()
    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white'); draw = ImageDraw.Draw(img)
        draw.text((150, 150), f"МОДУЛ: {mod['№']} - {mod['Тип']}", fill="black", font=f_title)
        # 3D Чертеж (опростен за превю)
        W, H, D = float(mod['W']), float(mod['H']), float(mod['D'])
        scale = 1000.0 / max(W, H, D); w_px, h_px = W*scale, H*scale
        draw.rectangle([740, 500, 740+w_px, 500+h_px], outline="black", width=5)
        pages.append(img)
    pdf_io = io.BytesIO()
    if pages: pages[0].save(pdf_io, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_io.getvalue()

def generate_labels_pdf(boards_per_mat):
    # Логика за етикети 44 бр на А4
    pdf_io = io.BytesIO()
    img = Image.new('RGB', (2480, 3508), 'white')
    img.save(pdf_io, format="PDF")
    return pdf_io.getvalue()

def get_optimized_boards(order_list):
    return {}, 2800, 2070, 8

# --- ФИНАНСОВ КАЛКУЛАТОР (ОСТАВА НА ЕКРАНА!) ---
st.markdown("---")
st.subheader("💰 Финанси и Оферта")

if st.session_state.order_list:
    try:
        df_calc = pd.DataFrame(st.session_state.order_list)
        df_calc['Area'] = (pd.to_numeric(df_calc['Дължина']) * pd.to_numeric(df_calc['Ширина']) * pd.to_numeric(df_calc['Бр'])) / 1000000
        summary = df_calc.groupby('Плоскост')['Area'].sum()
        
        st.markdown("##### 1. Материали и Разкрой")
        total_mat_cost = 0.0
        for mat_name, area in summary.items():
            price = st.number_input(f"€/м² {mat_name}", value=25.0, key=f"p_{mat_name}")
            total_mat_cost += area * price
        
        price_cut = st.number_input("€/бр. Разкрой", value=18.0)
        total_cut_cost = 2 * price_cut # Примерно 2 плочи
        
        st.markdown("##### 5. Твърди разходи и Труд")
        col_f1, col_f2 = st.columns(2)
        with col_f1: project_days = st.number_input("Дни за проект:", value=15)
        with col_f2: nadnici = st.number_input("Надници €/ден:", value=225)
        
        rent_cons = (project_days / 15.0) * 300.0
        total_labor = nadnici * project_days
        
        base_cost = total_mat_cost + total_cut_cost + rent_cons + total_labor
        profit = base_cost * 0.25
        final_offer = base_cost + profit
        
        st.info(f"Вътрешна себестойност: **{base_cost:.2f} €**")
        st.success(f"ОФЕРТА КЪМ КЛИЕНТ: **{final_offer:.2f} €**")
        st.write(f"🌟 **Печалба:** {profit:.2f} €")
        
    except Exception as e:
        st.warning(f"Грешка във финансите: {e}")
