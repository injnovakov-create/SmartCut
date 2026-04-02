import streamlit as st
import pandas as pd
import os
import io
import json  # За работа със запис/зареждане на файлове
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA, GuillotineBssfMaxas
# Настройки на страницата
st.set_page_config(page_title="OPTIVIK: Витя-М", layout="wide")

# --- CSS ЗА СБИТ ДИЗАЙН ---
st.markdown("""
<style>
html { zoom: 0.95; }
.stApp { background-color: #dce1e6 !important; } 
.opti-text { color: #000000; font-weight: bold; }
.vik-text { color: #FF0000; font-weight: bold; font-style: italic; }
div[data-baseweb="select"] {
    border: 2px solid #008080 !important;
    border-radius: 6px !important;
}
hr { margin-top: 0.8rem !important; margin-bottom: 0.8rem !important; border-color: #a3b0bd !important; }
.stButton>button { background-color: #008080 !important; color: white !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; padding: 0.5rem 1rem !important; width: 100%; }
.stButton>button:hover { background-color: #005959 !important; }
[data-testid="stSidebar"] { background-color: #cdd4db !important; border-right: 2px solid #a3b0bd !important; } 
[data-testid="stDataFrame"] { filter: brightness(0.90) contrast(0.95); border-radius: 8px; overflow: hidden; }
.stTextInput, .stNumberInput, .stSelectbox, .stRadio { margin-bottom: -0.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ГЛАВНОТО ЗАГЛАВИЕ С НОВАТА МАРКА
st.markdown("""
<h1 style='font-size: 32px; margin-top: 10px;'>
    <span class='opti-text'>OPTI</span><span class='vik-text'>VIK</span>
</h1>
<p style='font-size: 18px; color: gray; margin-top: -10px; margin-bottom: 20px;'><i>оптимизирай умно</i></p>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ НА STATE ---
if 'order_list' not in st.session_state: 
    st.session_state.order_list = []
if 'hardware_list' not in st.session_state: 
    st.session_state.hardware_list = []
if 'modules_meta' not in st.session_state: 
    st.session_state.modules_meta = [] 
if 'history' not in st.session_state: 
    st.session_state.history = []  # НОВО: За история на стъпките (Undo)

# --- ПОМОЩНИ ФУНКЦИИ ---
def get_edge_thick(val):
    v = str(val).lower().strip()
    if not v or v == "без кант": return 0
    if "2мм" in v or v == "2" or v == "2.0": return 2
    if "0.8" in v or "1мм" in v or v == "1" or v == "1.0": return 1
    if "2" in v: return 2
    return 1

def get_edge_label_text(val):
    thick = get_edge_thick(val)
    if thick == 2: return "2"
    if thick == 1: return "0.8"
    return ""

# --- ЛОГИКА ЗА ЗАПИС ТОЧНО КАТО В EXCEL ---
def add_item(modul, tip, detail, count, l, w, kant_str, material, flader, note="", custom_edges=None):
    final_l, final_w = float(l), float(w)
    
    if custom_edges:
        d1 = custom_edges.get("Д1", "")
        d2 = custom_edges.get("Д2", "")
        sh1 = custom_edges.get("Ш1", "")
        sh2 = custom_edges.get("Ш2", "")
        d1 = "" if d1 == "Без кант" else d1
        d2 = "" if d2 == "Без кант" else d2
        sh1 = "" if sh1 == "Без кант" else sh1
        sh2 = "" if sh2 == "Без кант" else sh2
    else:
        thick = 2 if any(x in str(detail).lower() for x in ["врата", "чело", "дублираща"]) else 1
        d1 = d2 = sh1 = sh2 = ""
        k = str(kant_str).lower()
        if "1д" in k: d1 = str(thick)
        if "2д" in k or "4" in k: d1 = str(thick); d2 = str(thick)
        if "1к" in k or "1ш" in k: sh1 = str(thick)
        if "2к" in k or "2ш" in k or "4" in k: sh1 = str(thick); sh2 = str(thick)
        
    if st.session_state.get("deduct_edge", False):
        final_w -= (get_edge_thick(d1) + get_edge_thick(d2))
        final_l -= (get_edge_thick(sh1) + get_edge_thick(sh2))

    return {
        "Плоскост": material, "№": modul, "Тип": tip, "Детайл": detail, 
        "Дължина": int(final_l), "Ширина": int(final_w), 
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
    if "шкаф с чекмеджета" in t: return "Шк чекм"
    if "стандартен долен" in t: return "Долен шк"
    if "горен шкаф" in t: return "Горен шк"
    if "шкаф мивка" in t: return "Шк мивка"
    if "шкаф за фурна" in t: return "Шк фурна"
    if "шкаф колона" in t: return "Колона"
    if "бутилки" in t: return "Бутилки"
    if "глух ъгъл (долен)" in t: return "Глух дол"
    if "глух ъгъл (горен)" in t: return "Глух гор"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    deduct_edge = st.checkbox("Приспадай дебелината на канта от разкроя", value=False, key="deduct_edge")
    # НОВО: Отметка за профил Gola
    gola_profile = st.checkbox("Профил Gola (долни врати и чела -30мм)", value=False, key="gola_profile")
    
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
    st.header("🪚 Кантове (Библиотека)")
    st.info("Въведи кантовете по един на ред. Те ще се появят в падащите менюта за нестандартни детайли.")
    edges_input = st.text_area("Налични кантове:", value="Без кант\n0.8мм\n2мм\nБяло 0.8мм\nБяло 2мм\nДъб Вотан 0.8мм\nДъб Вотан 2мм", height=150)
    available_edges = [e.strip() for e in edges_input.split('\n') if e.strip()]
    if "Без кант" not in available_edges:
        available_edges.insert(0, "Без кант")
        
    st.markdown("---")
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.session_state.hardware_list = []
        st.session_state.modules_meta = []
        st.rerun()

    # --- НОВО: ЗАПИС И ЗАРЕЖДАНЕ НА ПРОЕКТ ---
    st.markdown("---")
    st.header("💾 Управление на проекта")
    
    if st.session_state.order_list:
        export_data = {
            "order": st.session_state.order_list,
            "hw": st.session_state.hardware_list,
            "meta": st.session_state.modules_meta
        }
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Запази проекта (Файл)",
            data=json_data,
            file_name=f"proekt_kuhnya.json",
            mime="application/json"
        )
    
    uploaded_file = st.file_uploader("📂 Зареди проект", type="json", key="uploader")
    
    if uploaded_file is not None:
        try:
            # 1. Прочитаме данните от файла
            file_content = json.load(uploaded_file)
            
            # 2. Показваме бутон за потвърждение
            if st.button("🔄 ВЪЗСТАНОВИ ДАННИТЕ В ТАБЛИЦАТА"):
                # 3. Записваме ги в паметта (Session State)
                st.session_state.order_list = file_content.get("order", [])
                st.session_state.hardware_list = file_content.get("hw", [])
                # Важно: ако във файла няма 'meta', слагаме празен списък
                st.session_state.modules_meta = file_content.get("meta", [])
                
                # Изчистваме историята за Undo, за да не се обърка
                st.session_state.history = []
                
                st.success("✅ Проектът е зареден успешно!")
                # 4. Форсираме презареждане на страницата
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Грешка при четенето: {e}")

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    
    cat_choice = st.radio("Избери категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)

    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {
            "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", 
            "Шкаф Мивка": "🚰", "Шкаф с чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", 
            "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"
        }
    else:
        icons = {
            "Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"
        }

    # -------------------------------------------------------------
# -------------------------------------------------------------

# -------------------------------------------------------------

    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    name = st.text_input("Име/№ на модула", value=tip)
    
    appliances_type = "Без уреди"
    split_doors = False
    lower_door_h = 0
    lower_type = "Врата"
    vrati_broi = 1
    ch_heights = []
    runner_len = 500
    custom_mat_name = "ПДЧ 18мм (Друго)"
    custom_edges_dict = {}
    
    if tip == "Дублираща страница долен":
        h = st.number_input("Височина (H) мм", value=860)
        d = st.number_input("Дълбочина (D) мм", value=580)
        w = deb
    elif tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина (W) на корпуса (мм)", value=600, key="w_tret")
        h = st.number_input("Височина (H) в мм", value=350, key="h_tret")
        d = st.number_input("Дълбочина (D) в мм", value=500, key="d_tret")
        vrati_broi = st.radio("Брой врати:", [1, 2], index=0, horizontal=True, key="vr_tret")
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Нестандартен детайл")
        colA, colB, colC = st.columns(3)
        h = custom_l = colA.number_input("Дължина (L) мм", value=600)
        d = custom_w = colB.number_input("Ширина (W) мм", value=300)
        w = deb
        custom_count = colC.number_input("Брой", value=1, min_value=1)
        
        colE, colF = st.columns(2)
        custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер", "Специфичен (въведи)"])
        custom_flader = colF.radio("Спазва фладер?", ["Да", "Не"], index=0, horizontal=True)
        if custom_mat_type == "Специфичен (въведи)":
            custom_mat_name = st.text_input("Въведи име на материала:", value="ПДЧ 18мм (Друго)")
            
        st.markdown("##### 📏 Кантове по страни")
        st.caption("Избери конкретен кант за всяка страна. Програмата сама ще го приспадне!")
        colD1, colD2, colSh1, colSh2 = st.columns(4)
        c_d1 = colD1.selectbox("Дължина 1 (Д1)", available_edges, index=0)
        c_d2 = colD2.selectbox("Дължина 2 (Д2)", available_edges, index=0)
        c_sh1 = colSh1.selectbox("Ширина 1 (Ш1)", available_edges, index=0)
        c_sh2 = colSh2.selectbox("Ширина 2 (Ш2)", available_edges, index=0)
        custom_edges_dict = {"Д1": c_d1, "Д2": c_d2, "Ш1": c_sh1, "Ш2": c_sh2}
        
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600, key="w_col")
        h_korpus = st.number_input("Височина корпуса (H) мм", value=2040, key="h_col")
        d = st.number_input("Дълбочина (D) мм", value=550, key="d_col")
        appliances_type = st.radio("Вградени уреди:", ["Без уреди", "Само Фурна", "Фурна + Микровълнова"], horizontal=True)
        if appliances_type != "Без уреди":
            lower_door_h = st.number_input("Височина на долната част мм", value=718)
            lower_type = st.radio("Тип долна част:", ["Врата", "2 Чекмеджета", "3 Чекмеджета"], horizontal=True)
            if "Чекмеджета" in lower_type: runner_len = st.number_input("Дължина водач (мм)", value=500, step=50, key="run_col")
        else:
            split_doors = st.checkbox("Две врати по височина (Долна + Горна)?", value=True)
            if split_doors: lower_door_h = st.number_input("Височина долна врата (мм)", value=718)
        vrati_broi = st.radio("Брой врати на ред:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_col")
        h = h_korpus + kraka 
    elif tip == "Шкаф с чекмеджета":
        w = st.number_input("Ширина (W) мм", value=600, key="w_ch")
        h_box = st.number_input("Височина на корпуса без крака (мм)", value=760, key="h_box_ch")
        num_ch = st.slider("Брой чекмеджета:", 1, 6, 3, key="n_ch")
        
        # Оставяме интерфейса да показва чистата математика на корпуса
        total_front_h = h_box
        st.markdown(f"##### ↕️ Разпределение на височината (Общо: {total_front_h} мм):")
        
        cols_ch = st.columns(num_ch)
        ch_heights = []
        accumulated_h = 0
        
        for i in range(num_ch - 1):
            with cols_ch[i]:
                rem_drawers = num_ch - i
                default_h = int((total_front_h - accumulated_h) / rem_drawers)
                val_h = st.number_input(f"Чело {i+1} (мм)", value=default_h, min_value=50, max_value=total_front_h, key=f"ch_h_inp_{i}")
                ch_heights.append(val_h)
                accumulated_h += val_h
                
        last_ch_h = total_front_h - accumulated_h
        ch_heights.append(last_ch_h)
        
        with cols_ch[-1]:
            st.info(f"Чело {num_ch} (Остатък)")
            if last_ch_h < 50:
                st.error(f"⚠️ {last_ch_h} мм")
            else:
                st.success(f"**{last_ch_h}** мм")
                
        runner_len = st.number_input("Водач (мм)", value=500, step=50, key="run_ch")
        d = st.number_input("Дълбочина (D) мм", value=520, key="d_ch")
        h = h_box + kraka
    elif tip == "Гардероб чекм+врати":
        w = st.number_input("Ширина (W) мм", value=900, key="w_gard")
        h_korpus = st.number_input("Височина корпус (H) мм", value=2000, key="h_gard")
        d = st.number_input("Дълбочина (D) мм", value=550, key="d_gard")
        h_drawers = st.number_input("Височина за чекмеджетата (мм)", value=450, help="Колко от общата височина се пада на долния блок чекмеджета")
        runner_len = st.number_input("Дължина водач (мм)", value=500, step=50, key="run_gard")
        vrati_broi = 2
        h = h_korpus + kraka
        
        # Оставяме интерфейса да показва чистата математика на корпуса
        total_front_h = h_box
        st.markdown(f"##### ↕️ Разпределение на височината (Общо: {total_front_h} мм):")
        
        cols_ch = st.columns(num_ch)
        ch_heights = []
        accumulated_h = 0
        
        for i in range(num_ch - 1):
            with cols_ch[i]:
                rem_drawers = num_ch - i
                default_h = int((total_front_h - accumulated_h) / rem_drawers)
                val_h = st.number_input(f"Чело {i+1} (мм)", value=default_h, min_value=50, max_value=total_front_h, key=f"ch_h_inp_{i}")
                ch_heights.append(val_h)
                accumulated_h += val_h
                
        last_ch_h = total_front_h - accumulated_h
        ch_heights.append(last_ch_h)
        
        with cols_ch[-1]:
            st.info(f"Чело {num_ch} (Остатък)")
            if last_ch_h < 50:
                st.error(f"⚠️ {last_ch_h} мм")
            else:
                st.success(f"**{last_ch_h}** мм")
                
        runner_len = st.number_input("Водач (мм)", value=500, step=50, key="run_ch")
        d = st.number_input("Дълбочина (D) мм", value=520, key="d_ch")
        h = h_box + kraka
    else:
        default_w = 150 if tip == "Шкаф Бутилки 15см" else (1000 if "Глух" in tip else 600)
        w = st.number_input("Ширина (W) мм", value=default_w, key="w_std")
        if "Горен" in tip:
            h = st.number_input("Височина (H) мм", value=720, key="h_up")
            d = st.number_input("Дълбочина (D) мм", value=300, key="d_up")
            vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_up")
            vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални"], horizontal=True) if tip == "Горен Шкаф" else "Вертикални"
        else:
            # ВЕЧЕ Е 760:
            h_box = st.number_input("Височина на корпуса без крака (мм)", value=760, key="h_box_low")
            d = st.number_input("Дълбочина (D) мм", value=(550 if tip == "Шкаф Мивка" else 520), key="d_low")
            # Крайната височина за алгоритъма е корпус + крака
            h = h_box + kraka 
            vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_low")
    st.markdown("---")
    temp_meta = {"Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi}
    try:
        preview_img = draw_mini_preview(temp_meta, kraka)
        st.image(preview_img, caption="Скица на модула")
    except:
        pass

    if st.button("➕ Добави към списъка"):
        # --- СТЪПКА 1: "СНИМКА" ЗА ИСТОРИЯТА (UNDO) ---
        current_snap = {
            "order": json.loads(json.dumps(st.session_state.order_list)),
            "hw": json.loads(json.dumps(st.session_state.hardware_list)),
            "meta": json.loads(json.dumps(st.session_state.modules_meta))
        }
        st.session_state.history.append(current_snap)
        
        # Ограничаваме историята до 15 стъпки, за да не бави браузъра
        if len(st.session_state.history) > 15:
            st.session_state.history.pop(0)

        # --- СТЪПКА 2: ТВОИТЕ ИЗЧИСЛЕНИЯ (ПРОДЪЛЖАВАТ НАДОЛУ) ---
        new_items = []
        new_hw = []
        otstyp_fazer = 4
        
        if "Долен" in tip or tip in ["Шкаф Мивка", "Шкаф Бутилки 15см", "Шкаф за Фурна", "Шкаф с чекмеджета"]:
            h_stranica = int(h - kraka - deb)
        else:
            h_stranica = 742 
            
        h_shkaf_korpus = h_stranica + deb
        
        # НОВО: Проверява дали има Gola профил и вади 30мм само от долните врати
        gola_offset = 30 if st.session_state.get("gola_profile", False) else 0
        h_vrata_standart = h_shkaf_korpus - fuga_obshto - gola_offset
        
        meta_dict = {"№": name, "Тип": tip, "W": w, "H": h, "D": d}
        
        meta_dict = {"№": name, "Тип": tip, "W": w, "H": h, "D": d}
        if tip == "Шкаф Колона":
            meta_dict.update({"app_type": appliances_type, "ld_h": lower_door_h, "lower_type": lower_type})
        st.session_state.modules_meta.append(meta_dict)

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Шкаф Бутилки 15см", "Глух Ъгъл (Долен)", "Шкаф за Фурна", "Шкаф с чекмеджета", "Шкаф Колона"]:
            hw_legs = 5 if w > 900 else 4
            new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": hw_legs})

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Горен Шкаф"]:
            h_door_hw = h_vrata_standart if tip != "Горен Шкаф" else (h - fuga_obshto if vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto)))
            hw_hinges = calculate_hinges(h_door_hw) * vrati_broi
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})

        elif tip == "Гардероб чекм+врати":
            w_in = w - 2 * deb
            # Корпус
            st.session_state.order_list.append(add_item(name, tip, "Страница лява", 1, h_korpus, d, "1д 2к", mat_korpus, val_fl_korpus))
            st.session_state.order_list.append(add_item(name, tip, "Страница дясна", 1, h_korpus, d, "1д 2к", mat_korpus, val_fl_korpus))
            st.session_state.order_list.append(add_item(name, tip, "Дъно", 1, w_in, d, "1д", mat_korpus, val_fl_korpus))
            st.session_state.order_list.append(add_item(name, tip, "Таван", 1, w_in, d, "1д", mat_korpus, val_fl_korpus))
            st.session_state.order_list.append(add_item(name, tip, "Твърд рафт (между чекм. и врати)", 1, w_in, d, "1д", mat_korpus, val_fl_korpus))
            st.session_state.order_list.append(add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - 2, w - 2, "Без кант", mat_fazer, "Няма"))
            
            # Чекмеджета (2 бр. широки)
            h_front = int((h_drawers - 3 * fuga_obshto) / 2) # Две чела по височина
            w_front = w - 2 * fuga_obshto
            st.session_state.order_list.append(add_item(name, tip, "Чело", 2, h_front, w_front, "4", mat_lice, val_fl_lice))
            
            h_box = h_front - 30
            w_box_front = w_in - 26 # 13мм луфт за водачи на страна
            st.session_state.order_list.append(add_item(name, tip, "Царги предни/задни", 4, w_box_front, h_box, "1д", mat_chekm, val_fl_chekm))
            st.session_state.order_list.append(add_item(name, tip, "Страници чекмедже", 4, runner_len, h_box, "1д", mat_chekm, val_fl_chekm))
            st.session_state.order_list.append(add_item(name, tip, "Дъно чекмедже", 2, runner_len - 2, w_box_front + 2*deb - 2, "Без кант", mat_fazer, "Няма"))

            # Врати (2 бр. над чекмеджетата)
            h_doors = h_korpus - h_drawers - int(1.5 * fuga_obshto)
            w_door = int((w - 3 * fuga_obshto) / 2)
            st.session_state.order_list.append(add_item(name, tip, "Врата горна", 2, h_doors, w_door, "4", mat_lice, val_fl_lice))
            
        elif tip == "Трети ред (Надстройка)":
            hw_hinges = calculate_hinges(h - fuga_obshto) * vrati_broi
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})
            new_hw.append({"№": name, "Артикул": "Окачвачи за горен шкаф", "Брой": 2})

        elif tip == "Шкаф Бутилки 15см":
            hw_hinges = calculate_hinges(h_vrata_standart) * 1
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 1})
            new_hw.append({"№": name, "Артикул": "Механизъм за бутилки", "Брой": 1})
            
        elif tip in ["Глух Ъгъл (Долен)", "Глух Ъгъл (Горен)"]:
            h_door_hw = h_vrata_standart if "Долен" in tip else h - fuga_obshto
            hw_hinges = calculate_hinges(h_door_hw) * 1
            new_hw.append({"№": name, "Артикул": "Панти в една равнина (за глухи)", "Брой": hw_hinges})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 1})
            
        if tip == "Шкаф с чекмеджета":
            new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": len(ch_heights)})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": len(ch_heights)})
        elif tip == "Шкаф за Фурна":
            new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": 1})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 1})

        if "Горен" in tip:
            new_hw.append({"№": name, "Артикул": "Окачвачи за горен шкаф", "Брой": 2})
            new_hw.append({"№": name, "Артикул": "LED осветление (л.м.)", "Брой": w / 1000.0})

        if tip == "Дублираща страница долен":
            new_items.append(add_item(name, tip, "Дублираща страница", 1, h, d, "4 страни", mat_lice, val_fl_lice))
            
        elif tip == "Трети ред (Надстройка)":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else int(w - fuga_obshto)
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница (вътрешна)", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата", vrati_broi, h - fuga_obshto, w_izbrana, "4 страни", mat_lice, val_fl_lice)
            ])

        elif tip == "Нестандартен":
            if custom_mat_type == "Лице": m_choice = mat_lice
            elif custom_mat_type == "Чекмеджета": m_choice = mat_chekm
            elif custom_mat_type == "Фазер": m_choice = mat_fazer
            elif custom_mat_type == "Специфичен (въведи)": m_choice = custom_mat_name
            else: m_choice = mat_korpus
            
            f_choice = custom_flader 
            new_items.append(add_item(name, tip, custom_detail, custom_count, custom_l, custom_w, "", m_choice, f_choice, custom_edges=custom_edges_dict))
            
        elif tip == "Шкаф Колона":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else int(w - fuga_obshto)
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h_korpus - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            
            if appliances_type != "Без уреди":
                h_furn = 595
                h_mw = 380 if appliances_type == "Фурна + Микровълнова" else 0
                h_door_upper = h_korpus - lower_door_h - h_furn - h_mw - (fuga_obshto * 2) 
                
                if appliances_type == "Фурна + Микровълнова":
                    new_items.extend([
                        add_item(name, tip, "Рафт тв. (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (под МВ)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (над МВ)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт подвижен", 2, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                    ])
                    new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 8})
                elif appliances_type == "Само Фурна":
                    new_items.extend([
                        add_item(name, tip, "Рафт тв. (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (над фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт подвижен", 2, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                    ])
                    new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 8})
                
                if lower_type == "Врата":
                    new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lower_door_h, w_izbrana, "4 страни", mat_lice, val_fl_lice))
                    new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(lower_door_h) * vrati_broi})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})
                elif lower_type == "2 Чекмеджета":
                    chelo_h = lower_door_h / 2.0
                    cargi_w = w - (2*deb) - 49
                    duno_w = cargi_w + 12
                    duno_l = runner_len - 13
                    block_note = "В БЛОК" if val_fl_lice == "Да" else ""
                    
                    # НОВО: Точно чело - 60 мм
                    h_tsarga = int(chelo_h - 60)
                    new_items.extend([
                        add_item(name, tip, "Чело долно 1", 1, chelo_h - fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                        add_item(name, tip, "Чело долно 2", 1, chelo_h - fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                        add_item(name, tip, "Царги чекм.", 4, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, "Страници чекм.", 4, runner_len - 10, h_tsarga, "2д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, "Дъно чекмедже", 2, duno_l, duno_w, "Без", mat_fazer, "Няма")
                    ])
                    new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": 2})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 2})
                elif lower_type == "3 Чекмеджета":
                    ch_h = lower_door_h / 3.0
                    cargi_w = w - (2*deb) - 49
                    duno_w = cargi_w + 12
                    duno_l = runner_len - 13
                    block_note = "В БЛОК" if val_fl_lice == "Да" else ""
                    
                    # НОВО: Точно чело - 60 мм
                    h_tsarga = int(ch_h - 60)
                    for idx in range(3):
                        new_items.extend([
                            add_item(name, tip, f"Чело долно {idx+1}", 1, ch_h - fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                            add_item(name, tip, f"Царги чекм. {idx+1}", 2, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                            add_item(name, tip, f"Страници чекм. {idx+1}", 2, runner_len - 10, h_tsarga, "2д", mat_chekm, val_fl_chekm)
                        ])
                    
                    new_items.append(add_item(name, tip, "Дъно чекмедже", 3, duno_l, duno_w, "Без", mat_fazer, "Няма"))
                    new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": 3})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 3})
                
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_door_upper, w_izbrana, "4 страни", mat_lice, val_fl_lice))
                new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(h_door_upper) * vrati_broi})
                new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})
                
            else:
                new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 12})
                new_items.extend([
                    add_item(name, tip, "Рафт твърд", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Рафт подвижен", 3, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                ])
                if split_doors:
                    h_door_lower = lower_door_h
                    h_door_upper = h_korpus - lower_door_h - fuga_obshto
                    new_items.append(add_item(name, tip, "Врата долна", vrati_broi, h_door_lower, w_izbrana, "4 страни", mat_lice, val_fl_lice))
                    new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_door_upper, w_izbrana, "4 страни", mat_lice, val_fl_lice))
                    new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": (calculate_hinges(h_door_lower) + calculate_hinges(h_door_upper)) * vrati_broi})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi * 2})
                else:
                    h_door_full = h_korpus - fuga_obshto
                    new_items.append(add_item(name, tip, "Врата", vrati_broi, h_door_full, w_izbrana, "4 страни", mat_lice, val_fl_lice))
                    new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(h_door_full) * vrati_broi})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})
                    
        elif tip == "Горен Шкаф":
            shelves_count = 2 if h > 800 else 1
            new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": shelves_count * 4})
            new_items.extend([
                add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Рафт", shelves_count, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            h_vrata = h - fuga_obshto if vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto))
            w_vrata = w - fuga_obshto if vrati_orientacia != "Вертикални" else (w - fuga_obshto if vrati_broi == 1 else int((w/2) - fuga_obshto))
            new_items.append(add_item(name, tip, "Врата", vrati_broi, h_vrata, w_vrata, "4 страни", mat_lice, val_fl_lice))
            
        elif tip == "Глух Ъгъл (Горен)":
            shelves_count = 2 if h > 800 else 1
            new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": shelves_count * 4})
            new_items.extend([
                add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Рафт", shelves_count, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата", 1, h - fuga_obshto, int(w_vrata_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                add_item(name, tip, "Глуха част (Чело)", 1, h - fuga_obshto, int(w_gluha_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice)
            ])
            
        else:
            w_vrata_dvoina, w_vrata_edinichna = int((w/2) - fuga_obshto), w - fuga_obshto
            if tip == "Шкаф Мивка":
                w_izbrana = w_vrata_edinichna if vrati_broi == 1 else w_vrata_dvoina
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, 480, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 3, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Врата", vrati_broi, h_vrata_standart, w_izbrana, "4 страни", mat_lice, val_fl_lice)
                ])
            elif tip == "Стандартен Долен":
                w_izbrana = w_vrata_edinichna if vrati_broi == 1 else w_vrata_dvoina
                new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 4})
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Врата", vrati_broi, h_vrata_standart, w_izbrana, "4 страни", mat_lice, val_fl_lice), add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Шкаф Бутилки 15см":
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Врата", 1, h_vrata_standart, w_vrata_edinichna, "4 страни", mat_lice, val_fl_lice),
                    add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Глух Ъгъл (Долен)":
                new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 4})
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Врата", 1, h_vrata_standart, int(w_vrata_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                    add_item(name, tip, "Глуха част (Чело)", 1, h_vrata_standart, int(w_gluha_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                    add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Шкаф за Фурна":
                new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 4})
                cargi_w = w - (2*deb) - 49
                duno_w = cargi_w + 12
                duno_l = runner_len - 13
                
                # НОВО: Точно чело - 60 мм (тъй като челото тук е винаги 157 мм, царгите стават точно 97 мм)
                h_tsarga_furna = 157 - 60
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Чело чекмедже", 1, 157, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice), 
                    add_item(name, tip, "Царги чекм.", 2, cargi_w, h_tsarga_furna, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Страници чекм.", 2, runner_len - 10, h_tsarga_furna, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Дъно чекмедже", 1, duno_l, duno_w, "Без", mat_fazer, "Няма")
                ])
                
            elif tip == "Шкаф с чекмеджета":
                block_note = "В БЛОК" if val_fl_lice == "Да" else ""
                cargi_w = w - (2*deb) - 49
                duno_w = cargi_w + 12
                duno_l = runner_len - 13
                
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                    add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                    add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
                
                for idx, ch_h in enumerate(ch_heights):
                    # НОВО: Тук вадим профила Gola (30мм) и фугата (3мм) за всяко едно чело!
                    final_front_h = ch_h - fuga_obshto - gola_offset
                    h_tsarga = int(final_front_h - 60)
                    
                    new_items.extend([
                        add_item(name, tip, f"Чело {idx+1}", 1, final_front_h, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                        add_item(name, tip, f"Царги чекм. {idx+1}", 2, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, f"Страници чекм. {idx+1}", 2, runner_len - 10, h_tsarga, "2д", mat_chekm, val_fl_chekm)
                    ])
                
                new_items.append(add_item(name, tip, "Дъно чекмедже", len(ch_heights), duno_l, duno_w, "Без", mat_fazer, "Няма"))

        st.session_state.order_list.extend(new_items)
        st.session_state.hardware_list.extend(new_hw)
        st.success(f"Модул {name} е добавен!")
        st.rerun()
with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    
    # --- НОВО: БУТОН ЗА ВРЪЩАНЕ НАЗАД (UNDO) ---
    if st.session_state.get("history"):
        if st.button("↩️ Върни една стъпка назад"):
            # Взимаме последната "снимка" от историята
            last_state = st.session_state.history.pop()
            
            # Възстановяваме списъците към това състояние
            st.session_state.order_list = last_state["order"]
            st.session_state.hardware_list = last_state["hw"]
            st.session_state.modules_meta = last_state["meta"]
            
            # Презареждаме, за да се види промяната веднага
            st.rerun()
    
    # --- УПРАВЛЕНИЕ НА МОДУЛИ ---
    if st.session_state.order_list:
        unique_modules = list(dict.fromkeys([str(item["№"]) for item in st.session_state.order_list]))
        with st.expander("⚙️ Управление на добавени модули (Изтриване)"):
            for m_num in unique_modules:
                col_m1, col_m2 = st.columns([4, 1])
                col_m1.write(f"📦 Модул: **{m_num}**")
                if col_m2.button("🗑️ Изтрий", key=f"del_{m_num}"):
                    st.session_state.order_list = [item for item in st.session_state.order_list if str(item["№"]) != m_num]
                    st.session_state.hardware_list = [item for item in st.session_state.hardware_list if str(item.get("№", "")) != m_num]
                    st.session_state.modules_meta = [item for item in st.session_state.modules_meta if str(item.get("№", "")) != m_num]
                    st.rerun()
        st.markdown("---")
        
        # --- ТАБЛИЦА (Сортирана и напълно редактируема) ---
        df = pd.DataFrame(st.session_state.order_list)
        cols_order = ["Плоскост", "№", "Тип", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[[c for c in cols_order if c in df.columns]]
        
        # Автоматично сортиране по номер на модул, за да са групирани перфектно
        df = df.sort_values(by="№")
        
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=600, key="editor")
        st.session_state.order_list = edited_df.to_dict('records')
        
        if st.session_state.hardware_list:
            st.markdown("#### 🔩 Количествена сметка: Обков")
            hw_df = pd.DataFrame(st.session_state.hardware_list)
            hw_summary = hw_df.groupby("Артикул")["Брой"].sum().reset_index()
            hw_summary["Брой"] = hw_summary["Брой"].apply(lambda x: f"{x:.1f}" if isinstance(x, float) and not x.is_integer() else f"{int(x)}")
            st.table(hw_summary)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Разкрой')
            if st.session_state.hardware_list:
                pd.DataFrame(st.session_state.hardware_list).groupby("Артикул")["Брой"].sum().reset_index().to_excel(writer, index=False, sheet_name='Обков')
        st.download_button(label="📊 Свали в Excel (.xlsx)", data=output.getvalue(), file_name="razkroi_vitya_kuhni.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Списъкът е празен. Добави първия си модул отляво!")

# --- ГЕНЕРИРАНЕ НА PDF С ЧЕРТЕЖИ (ЧЕРНО-БЯЛО) ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: 
        font_title = ImageFont.truetype(font_path, 80)
        font_text = ImageFont.truetype(font_path, 50) 
        font_dim = ImageFont.truetype(font_path, 60)
        font_bold = ImageFont.truetype(font_path, 55)
    except: 
        font_title = font_text = font_dim = font_bold = ImageFont.load_default()

    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white')
        draw = ImageDraw.Draw(img)
        
        draw.text((150, 150), f"МОДУЛ: {mod['№']} - {mod['Тип']}", fill="black", font=font_title)
        draw.line([(150, 250), (2330, 250)], fill="black", width=5)
        
        W, H, D = float(mod['W']), float(mod['H']), float(mod['D'])
        max_dim = max(W, H, D)
        if max_dim == 0: max_dim = 1
        scale = 1000.0 / max_dim
        
        w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
        offset_x, offset_y = d_px * 0.866, d_px * 0.5
        
        start_x = 1240 - (w_px + offset_x)/2
        start_y = 1000 - (h_px + offset_y)/2
        
        f_tl, f_tr = (start_x, start_y), (start_x + w_px, start_y)
        f_bl, f_br = (start_x, start_y + h_px), (start_x + w_px, start_y + h_px)
        r_tl, r_tr = (start_x + offset_x, start_y - offset_y), (start_x + w_px + offset_x, start_y - offset_y)
        r_bl, r_br = (start_x + offset_x, start_y + h_px - offset_y), (start_x + w_px + offset_x, start_y + h_px - offset_y)
        
        draw.polygon([f_tl, r_tl, r_tr, f_tr], fill="#e0e0e0", outline="black", width=5) 
        draw.polygon([f_tr, r_tr, r_br, f_br], fill="#d0d0d0", outline="black", width=5) 
        draw.polygon([f_tl, f_tr, f_br, f_bl], fill="#f5f5f5", outline="black", width=5) 
        
        tip = mod['Тип']
        lower_types = ["Долен", "Мивка", "чекмеджета", "Фурна", "Бутилки", "Колона"]
        
        leg_h_px = 0
        if any(t.lower() in tip.lower() for t in lower_types):
            kraka_px = kraka_height * scale
            leg_h_px = kraka_px
            plinth_y = start_y + h_px - kraka_px
            draw.line([(start_x, plinth_y), (start_x + w_px, plinth_y)], fill="#555555", width=4)
            draw.line([(start_x + w_px, plinth_y), (start_x + w_px + offset_x, plinth_y - offset_y)], fill="#555555", width=4)
            
            leg_w = 40 * scale
            offset = 50 * scale
            draw.rectangle([start_x+offset, start_y+h_px-kraka_px, start_x+offset+leg_w, start_y+h_px], outline="black", width=3)
            draw.rectangle([start_x+w_px-offset-leg_w, start_y+h_px-kraka_px, start_x+w_px-offset, start_y+h_px], outline="black", width=3)
            draw.rectangle([start_x+offset+offset_x, start_y+h_px-kraka_px-offset_y, start_x+offset+leg_w+offset_x, start_y+h_px-offset_y], outline="black", width=2)
            draw.rectangle([start_x+w_px-offset-leg_w+offset_x, start_y+h_px-kraka_px-offset_y, start_x+w_px-offset+offset_x, start_y+h_px-offset_y], outline="black", width=2)

        parts = [p for p in order_list if str(p.get("№", "")) == str(mod["№"])]
        vrati_count = 1
        has_split = False
        ld_h = mod.get("ld_h", 0)

        for p in parts:
            if "врата" in str(p['Детайл']).lower():
                vrati_count = int(p['Бр'])
            if "врата долна" in str(p['Детайл']).lower() or "чело долно" in str(p['Детайл']).lower():
                has_split = True
                
        if tip == "Шкаф Колона":
            if ld_h > 0:
                split_y_1 = start_y + h_px - leg_h_px - (ld_h * scale)
                draw.line([(start_x, split_y_1), (start_x + w_px, split_y_1)], fill="black", width=4)
                
                app_type = mod.get("app_type", "Без уреди")
                if app_type != "Без уреди":
                    split_y_2 = split_y_1 - (595 * scale)
                    draw.line([(start_x, split_y_2), (start_x + w_px, split_y_2)], fill="black", width=4)
                    draw.text((start_x + w_px/2, split_y_1 - (297 * scale)), "ФУРНА\n595", fill="#555555", font=font_dim, anchor="mm", align="center")
                    
                    if app_type == "Фурна + Микровълнова":
                        split_y_3 = split_y_2 - (380 * scale)
                        draw.line([(start_x, split_y_3), (start_x + w_px, split_y_3)], fill="black", width=4)
                        draw.text((start_x + w_px/2, split_y_2 - (190 * scale)), "М.В.\n380", fill="#555555", font=font_dim, anchor="mm", align="center")
                
                lower_type = mod.get("lower_type", "Врата")
                if "Чекмеджета" in lower_type:
                    if lower_type == "2 Чекмеджета":
                        mid_y = start_y + h_px - leg_h_px - ((ld_h/2) * scale)
                        draw.line([(start_x, mid_y), (start_x + w_px, mid_y)], fill="#333333", width=6)
                    elif lower_type == "3 Чекмеджета":
                        y1 = start_y + h_px - leg_h_px - ((ld_h - 180) * scale)
                        y2 = y1 + (250 * scale)
                        draw.line([(start_x, y1), (start_x + w_px, y1)], fill="#333333", width=6)
                        draw.line([(start_x, y2), (start_x + w_px, y2)], fill="#333333", width=6)
                        
        if "чекмеджета" in tip.lower() and tip != "Шкаф Колона":
            d1_y = start_y + (180 * scale)
            draw.line([(start_x, d1_y), (start_x + w_px, d1_y)], fill="#333333", width=6)
            d2_y = d1_y + (250 * scale)
            draw.line([(start_x, d2_y), (start_x + w_px, d2_y)], fill="#333333", width=6)
            
        elif "Фурна" in tip and tip != "Шкаф Колона":
            d_y = start_y + h_px - leg_h_px - (157 * scale)
            draw.line([(start_x, d_y), (start_x + w_px, d_y)], fill="#333333", width=6)

        if vrati_count == 2 and tip != "Шкаф Колона":
            draw.line([(start_x + w_px/2, start_y), (start_x + w_px/2, start_y + h_px - leg_h_px)], fill="black", width=3)
        elif vrati_count == 2 and tip == "Шкаф Колона":
            draw.line([(start_x + w_px/2, start_y), (start_x + w_px/2, start_y + h_px - leg_h_px)], fill="black", width=3)

        draw.text((start_x + w_px/2 - 100, start_y + h_px + 30), f"W: {int(W)}", fill="black", font=font_dim)
        draw.text((start_x - 250, start_y + h_px/2 - 30), f"H: {int(H)}", fill="black", font=font_dim)
        draw.text((start_x + w_px + offset_x/2 + 30, start_y + h_px - offset_y/2 - 30), f"D: {int(D)}", fill="black", font=font_dim)

        draw.text((150, 1800), "СПЕЦИФИКАЦИЯ НА ДЕТАЙЛИТЕ:", fill="black", font=font_title)
        cols_x = [170, 850, 1150, 1400, 1600, 2000]
        lines_x = [150, 830, 1130, 1380, 1580, 1980, 2350]
        y_offset = 1950
        start_y_table = y_offset - 20 
        
        headers = ["ДЕТАЙЛ", "ДЪЛЖ.", "ШИР.", "БР.", "КАНТ", "ПЛОСКОСТ"]
        for i, h_text in enumerate(headers):
            draw.text((cols_x[i], y_offset), h_text, fill="black", font=font_bold)
            
        y_offset += 80
        draw.line([(150, y_offset), (2350, y_offset)], fill="black", width=4) 
        y_offset += 20
        
        for p in parts:
            kant_str = ""
            if p.get('Д1'): kant_str += f"Д1({get_edge_label_text(p['Д1'])}) "
            if p.get('Д2'): kant_str += f"Д2({get_edge_label_text(p['Д2'])}) "
            if p.get('Ш1'): kant_str += f"Ш1({get_edge_label_text(p['Ш1'])}) "
            if p.get('Ш2'): kant_str += f"Ш2({get_edge_label_text(p['Ш2'])}) "
            
            row_data = [
                str(p['Детайл'])[:18], str(int(p['Дължина'])), str(int(p['Ширина'])),
                str(int(p['Бр'])), kant_str[:15], str(p['Плоскост'])[:15]
            ]
            for i, text in enumerate(row_data):
                draw.text((cols_x[i], y_offset), text, fill="#222222", font=font_text)
                
            y_offset += 75
            draw.line([(150, y_offset), (2350, y_offset)], fill="#aaaaaa", width=2) 
            y_offset += 20
            if y_offset > 3300: break 
            
        for lx in lines_x:
            draw.line([(lx, start_y_table), (lx, y_offset)], fill="black", width=3)
        draw.line([(150, start_y_table), (2350, start_y_table)], fill="black", width=4) 
        draw.line([(150, y_offset), (2350, y_offset)], fill="black", width=4) 
                
        pages.append(img)
        
    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_bytes.getvalue()
    return None

# --- ПОМОЩНА ФУНКЦИЯ ЗА ЧЕРТАНЕ НА ЛИНИИТЕ НА КАНТА ВЪРХУ ЕТИКЕТА ---
def draw_edge_marking(draw, x, y, w, h, side, text, font):
    if not text or text == "": return
    line_w = 4
    inset_x = 40  # Скъсява линията в краищата
    inset_y = 50  # Мести линията НАВЪТРЕ към центъра (около 4.2 мм)
    
    if side == 'top':
        draw.line([x + inset_x, y + inset_y, x + w - inset_x, y + inset_y], fill="black", width=line_w)
        draw.text((x + w/2, y + inset_y + 8), text, fill="black", font=font, anchor="mt")
    elif side == 'bottom':
        draw.line([x + inset_x, y + h - inset_y, x + w - inset_x, y + h - inset_y], fill="black", width=line_w)
        draw.text((x + w/2, y + h - inset_y - 8), text, fill="black", font=font, anchor="mb")
    elif side == 'left':
        draw.line([x + inset_y, y + inset_x, x + inset_y, y + h - inset_x], fill="black", width=line_w)
        draw.text((x + inset_y + 8, y + h/2), text, fill="black", font=font, anchor="lm")
    elif side == 'right':
        draw.line([x + w - inset_y, y + inset_x, x + w - inset_y, y + h - inset_x], fill="black", width=line_w)
        draw.text((x + w - inset_y - 8, y + h/2), text, fill="black", font=font, anchor="rm")
# --- ОПТИМИЗАЦИЯ НА РАЗКРОЯ (ИСТИНСКИ НЕСТИНГ ЗА ФОРМАТЕН ЦИРКУЛЯР + ЕТИКЕТИ) ---
def get_optimized_boards(list_for_cutting):
    kerf, trim, board_l, board_w = 8, 8, 2800, 2070
    use_l, use_w = board_l - 2*trim, board_w - 2*trim
    materials_dict = {}
    
    for item in list_for_cutting:
        mat = item.get('Плоскост', 'Неизвестен')
        if mat not in materials_dict: materials_dict[mat] = []
        try:
            for _ in range(int(item['Бр'])):
                flader_val = str(item.get('Фладер', 'Да')).strip().lower()
                can_rotate = (flader_val == "не" or flader_val == "няма")
                
                # ПАЗИМ ВСИЧКИ ДАННИ ЗА ЕТИКЕТИТЕ!
                part_dict = item.copy() 
                part_dict.update({
                    'name': f"{item.get('№', '')} {get_abbrev(item.get('Детайл', ''))}", 
                    'l': float(item['Дължина']), 'w': float(item['Ширина']),
                    'd1': str(item.get('Д1', '')).strip(), 'd2': str(item.get('Д2', '')).strip(),
                    'sh1': str(item.get('Ш1', '')).strip(), 'sh2': str(item.get('Ш2', '')).strip(),
                    'can_rotate': can_rotate,
                    # Подсигуряване, ако ключът липсва:
                    'mod_tip': item.get('mod_tip', item.get('Детайл', 'Детайл'))
                })
                materials_dict[mat].append(part_dict)
        except: pass
    
    boards_per_material = {}
    
    for mat_name, parts in materials_dict.items():
        mat_can_rotate = all(p['can_rotate'] for p in parts)
        
        packer = newPacker(
            mode=PackingMode.Offline, 
            bin_algo=PackingBin.BFF, 
            pack_algo=GuillotineBssfMaxas, 
            rotation=mat_can_rotate
        )
        
        for i, p in enumerate(parts):
            rect_l = int(p['l'] + kerf)
            rect_w = int(p['w'] + kerf)
            packer.add_rect(rect_l, rect_w, rid=i)
            
        for _ in range(20): 
            packer.add_bin(int(use_l), int(use_w))
            
        packer.pack()
        
        all_boards = []
        for abin in packer:
            current_board_parts = []
            for rect in abin:
                idx = rect.rid
                orig = parts[idx]
                
                res_x, res_y, res_w, res_h = rect.x, rect.y, rect.width, rect.height
                
                p_copy = orig.copy()
                p_copy['x'] = res_x
                p_copy['y'] = res_y
                
                final_l = res_w - kerf
                final_w = res_h - kerf
                
                if abs(final_l - orig['w']) < 2:
                    p_copy['l'] = final_l
                    p_copy['w'] = final_w
                    p_copy['d1'], p_copy['d2'], p_copy['sh1'], p_copy['sh2'] = orig['sh1'], orig['sh2'], orig['d1'], orig['d2']
                else:
                    p_copy['l'] = final_l
                    p_copy['w'] = final_w
                
                current_board_parts.append(p_copy)
            
            if current_board_parts:
                all_boards.append(current_board_parts)
                
        boards_per_material[mat_name] = all_boards
        
    return boards_per_material, board_l, board_w, trim

# --- ГЕНЕРИРАНЕ НА РАЗКРОЙ В А4 PDF ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    pass

def generate_cutting_plan_pdf(boards_per_mat, board_l, board_w, trim):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
        
    page_w, page_h = 3508, 2480 
    margin = 80 
    pages = []
    
    for mat_name, boards in boards_per_mat.items():
        total_08 = 0
        total_20 = 0
        for b in boards:
            for p in b:
                for side in ['d1', 'd2', 'sh1', 'sh2']:
                    val = p.get(side, '')
                    if val:
                        thick = get_edge_label_text(val)
                        length = p['l'] if side.startswith('d') else p['w']
                        if thick == "0.8": total_08 += length
                        elif thick == "2": total_20 += length
        
        total_08_m = (total_08 / 1000.0) * 1.10
        total_20_m = (total_20 / 1000.0) * 1.10

        for idx, b_parts in enumerate(boards):
            img = Image.new('RGB', (page_w, page_h), 'white')
            draw = ImageDraw.Draw(img)
            
            kant_08_sum = 0
            kant_20_sum = 0
            max_x = 0 
            
            for p in b_parts:
                if (p['x'] + p['l']) > max_x: max_x = p['x'] + p['l']
                for side in ['d1', 'd2', 'sh1', 'sh2']:
                    val = p.get(side, '')
                    if val:
                        thick = get_edge_label_text(val)
                        length = p['l'] if side.startswith('d') else p['w']
                        if thick == "0.8": kant_08_sum += length
                        elif thick == "2": kant_20_sum += length
            
            k08_board_m = (kant_08_sum / 1000.0) * 1.10
            k20_board_m = (kant_20_sum / 1000.0) * 1.10
            kant_text = f"Кант за плочата (+10%): 0.8мм ≈ {k08_board_m:.1f}м | 2.0мм ≈ {k20_board_m:.1f}м"
            
            rem_l = max(0, board_l - max_x - (2 * trim))
            rem_w = board_w - (2 * trim)
            ost_text = f"Най-голям остатък: ≈ {int(rem_l)} x {int(rem_w)} мм"

            try: f_logo = ImageFont.truetype(font_path, 70)
            except: f_logo = ImageFont.load_default()
            draw.text((margin, 40), "OPTI", fill="black", font=f_logo)
            bbox_opti = draw.textbbox((margin, 40), "OPTI", font=f_logo)
            draw.text((bbox_opti[2], 40), "VIK", fill="red", font=f_logo)
            draw.line([(margin, 120), (page_w - margin, 120)], fill="#eeeeee", width=3)

            try:
                f_title = ImageFont.truetype(font_path, 50)
                f_info = ImageFont.truetype(font_path, 40)
            except: f_title = f_info = ImageFont.load_default()

            y_offset = 140
            draw.text((margin, y_offset), f"МАТЕРИАЛ: {mat_name} [2800x2070 мм]", fill="black", font=f_title)
            y_offset += 60
            
            if idx == 0:
                total_text = f"ОБЩО ЗА ДЕКОРА (+10% фира): 0.8мм ≈ {total_08_m:.1f}м | 2.0мм ≈ {total_20_m:.1f}м"
                draw.text((margin, y_offset), total_text, fill="#FF0000", font=f_info)
                y_offset += 50
            
            draw.text((margin, y_offset), f"ПЛОЧА {idx+1} от {len(boards)} | {kant_text}", fill="#008080", font=f_info)
            y_offset += 50
            draw.text((margin, y_offset), ost_text, fill="#555555", font=f_info)
            y_offset += 60 
            
            draw_w = page_w - 2 * margin
            draw_h = page_h - margin - y_offset 
            scale = min(draw_w / board_l, draw_h / board_w)
            
            act_w = board_l * scale
            act_h = board_w * scale
            sx = margin + (draw_w - act_w) / 2
            sy = y_offset + (draw_h - act_h) / 2 
            
            draw.rectangle([sx, sy, sx+act_w, sy+act_h], outline="black", width=4)
            t_px = trim * scale
            draw.rectangle([sx+t_px, sy+t_px, sx+act_w-t_px, sy+act_h-t_px], outline="#aaaaaa", width=2)
            
            for p in b_parts:
                px = sx + (p['x'] + trim) * scale
                py = sy + (p['y'] + trim) * scale
                pw = p['l'] * scale
                ph = p['w'] * scale
                draw.rectangle([px, py, px+pw, py+ph], outline="black", width=3)
                
                for side, width in [('d1', 8 if get_edge_label_text(p['d1'])=="2" else 3), 
                                    ('d2', 8 if get_edge_label_text(p['d2'])=="2" else 3),
                                    ('sh1', 8 if get_edge_label_text(p['sh1'])=="2" else 3),
                                    ('sh2', 8 if get_edge_label_text(p['sh2'])=="2" else 3)]:
                    if p.get(side) and width > 0:
                        if side == 'd1': draw.line([(px, py+ph), (px+pw, py+ph)], fill="black", width=width)
                        if side == 'd2': draw.line([(px, py), (px+pw, py)], fill="black", width=width)
                        if side == 'sh1': draw.line([(px, py), (px, py+ph)], fill="black", width=width)
                        if side == 'sh2': draw.line([(px+pw, py), (px+pw, py+ph)], fill="black", width=width)

                should_rotate = ph > pw
                avail_w = ph if should_rotate else pw
                avail_h = pw if should_rotate else ph
                
                dim_str = f"{int(p['l'])} / {int(p['w'])}"
                
                # --- ВИЗУАЛНО ИЗЧИСТВАНЕ: Скриваме името при малки детайли ---
                if avail_w < 180 * scale or avail_h < 90 * scale:
                    name_str = ""
                else:
                    name_str = p['name'][:12] + ".." if len(p['name']) > 12 else p['name']
                
                len_dim_str = max(len(dim_str), 1)
                size_dim = int(min(avail_w * 0.8 / len_dim_str * 1.5, avail_h * 0.45))
                size_dim = max(18, min(size_dim, 80)) 
                
                try:
                    f_d = ImageFont.truetype(font_path, size_dim)
                    f_n = ImageFont.truetype(font_path, int(size_dim * 0.7))
                except: f_d = f_n = ImageFont.load_default()

                txt_layer = Image.new('RGBA', (int(avail_w), int(avail_h)), (255,255,255,0))
                d_layer = ImageDraw.Draw(txt_layer)
                
                if name_str:
                    d_layer.text((avail_w/2, avail_h/2 + size_dim/4), dim_str, fill="black", font=f_d, anchor="mm")
                    d_layer.text((avail_w/2, avail_h/2 - size_dim/2), name_str, fill="#333333", font=f_n, anchor="mm")
                else:
                    # Ако няма място за име, центрираме размерите идеално в средата
                    d_layer.text((avail_w/2, avail_h/2), dim_str, fill="black", font=f_d, anchor="mm")
                
                if should_rotate:
                    txt_layer = txt_layer.rotate(90, expand=True)
                
                img.paste(txt_layer, (int(px), int(py)), txt_layer)
                    
            pages.append(img)
            
    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_bytes.getvalue()
    return None

    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_bytes.getvalue()
    return None

# ==============================================================
# ==============================================================
# ТУК СА ЛИПСВАЩИТЕ БУТОНИ ЗА ИЗТЕГЛЯНЕ И РАЗКРОЙ НА ЕКРАНА
# ==============================================================

# --- 1. ПОМОЩНА ФУНКЦИЯ ЗА ЧЕРТАНЕ НА ЛИНИИТЕ (НАПОЛОВИНА ОТСТЪП) ---
def draw_edge_marking(draw, x, y, w, h, side, text, font):
    if not text or text == "": return
    line_w = 4
    inset_x = 20  
    inset_y = 25  

    # Изчисляваме колко място заема текстът, за да "скъсаме" линията точно там
    bbox = draw.textbbox((0, 0), text, font=font)
    t_w = bbox[2] - bbox[0]
    t_h = bbox[3] - bbox[1]
    
    gap_w = (t_w / 2) + 8  # Половината от дупката по ширина
    gap_h = (t_h / 2) + 8  # Половината от дупката по височина

    mid_x = x + w / 2
    mid_y = y + h / 2

    if side == 'top':
        y_pos = y + inset_y
        draw.line([x + inset_x, y_pos, mid_x - gap_w, y_pos], fill="black", width=line_w)
        draw.line([mid_x + gap_w, y_pos, x + w - inset_x, y_pos], fill="black", width=line_w)
        draw.text((mid_x, y_pos), text, fill="black", font=font, anchor="mm")
        
    elif side == 'bottom':
        y_pos = y + h - inset_y
        draw.line([x + inset_x, y_pos, mid_x - gap_w, y_pos], fill="black", width=line_w)
        draw.line([mid_x + gap_w, y_pos, x + w - inset_x, y_pos], fill="black", width=line_w)
        draw.text((mid_x, y_pos), text, fill="black", font=font, anchor="mm")
        
    elif side == 'left':
        x_pos = x + inset_y
        draw.line([x_pos, y + inset_x, x_pos, mid_y - gap_h], fill="black", width=line_w)
        draw.line([x_pos, mid_y + gap_h, x_pos, y + h - inset_x], fill="black", width=line_w)
        draw.text((x_pos, mid_y), text, fill="black", font=font, anchor="mm")
        
    elif side == 'right':
        x_pos = x + w - inset_y
        draw.line([x_pos, y + inset_x, x_pos, mid_y - gap_h], fill="black", width=line_w)
        draw.line([x_pos, mid_y + gap_h, x_pos, y + h - inset_x], fill="black", width=line_w)
        draw.text((x_pos, mid_y), text, fill="black", font=font, anchor="mm")


# --- 2. ГЕНЕРИРАНЕ НА ТЕХНИЧЕСКИ PDF ЧЕРТЕЖИ (3D С ДЕБЕЛИНА 18ММ, РАФТОВЕ И ПРЕКЪСНАТИ ЛИНИИ) ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: 
        f_title = ImageFont.truetype(font_path, 50)
        f_dim = ImageFont.truetype(font_path, 42) # Увеличен с 5%
    except: 
        f_title = f_dim = ImageFont.load_default()

    def get_val(item, keys, default):
        for k in keys:
            if k in item and item[k] is not None and str(item[k]).strip() != "":
                return item[k]
        return default

    # Подобрена функция за оразмерителни линии (текстът "къса" линията)
    def draw_dim(img, draw, x1, y1, x2, y2, text, font, color, rotate=False):
        import math
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        dist = math.hypot(x2-x1, y2-y1)
        if dist < 1: return
        ux, uy = (x2-x1)/dist, (y2-y1)/dist
        
        # Взимаме реалния размер на текста
        txt_img_temp = Image.new('RGBA', (10, 10), (255,255,255,0))
        temp_draw = ImageDraw.Draw(txt_img_temp)
        bbox = temp_draw.textbbox((0,0), text, font=font)
        tw = bbox[2] - bbox[0]
        
        gap = (tw / 2) + 12 # Място за текста + малък отстъп
        
        # Прекъсване на линията
        if dist > gap * 2:
            draw.line([(x1, y1), (mid_x - ux*gap, mid_y - uy*gap)], fill=color, width=3)
            draw.line([(mid_x + ux*gap, mid_y + uy*gap), (x2, y2)], fill=color, width=3)
        else:
            draw.line([(x1, y1), (x2, y2)], fill=color, width=3)
            
        # Засечки в краищата
        tick_len = 15
        if abs(x2-x1) > abs(y2-y1):
            draw.line([(x1, y1-tick_len), (x1, y1+tick_len)], fill=color, width=4)
            draw.line([(x2, y2-tick_len), (x2, y2+tick_len)], fill=color, width=4)
        elif abs(y2-y1) > abs(x2-x1):
            draw.line([(x1-tick_len, y1), (x1+tick_len, y1)], fill=color, width=4)
            draw.line([(x2-tick_len, y2), (x2+tick_len, y2)], fill=color, width=4)
        else:
            draw.line([(x1-tick_len, y1+tick_len), (x1+tick_len, y1-tick_len)], fill=color, width=4)
            draw.line([(x2-tick_len, y2+tick_len), (x2+tick_len, y2-tick_len)], fill=color, width=4)
            
        # Поставяне на центриран текст в дупката
        txt_img = Image.new('RGBA', (400, 100), (255,255,255,0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((200, 50), text, fill=color, font=font, anchor="mm")
        
        if rotate:
            txt_img = txt_img.rotate(90, expand=True)
            rot_w, rot_h = txt_img.size
            img.paste(txt_img, (int(mid_x - rot_w/2), int(mid_y - rot_h/2)), txt_img)
        else:
            img.paste(txt_img, (int(mid_x - 200), int(mid_y - 50)), txt_img)

    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white')
        draw = ImageDraw.Draw(img)

        m_num = get_val(mod, ['mod_num', '№', 'Номер', 'id', 'num'], '?')
        m_tip = get_val(mod, ['mod_tip', 'Модул', 'Вид', 'Име', 'name', 'Детайл'], 'Неизвестен Модул')
        
        try: w = float(get_val(mod, ['w', 'W', 'Ширина', 'width'], 600))
        except: w = 600
        try: h = float(get_val(mod, ['h_box', 'h', 'H', 'Височина', 'height'], 860))
        except: h = 860
        try: d = float(get_val(mod, ['d', 'D', 'Дълбочина', 'depth'], 550))
        except: d = 550

        try: kr = int(kraka_height)
        except: kr = 0
        
        is_upper = "Горен" in m_tip or "горен" in m_tip or "Горни" in m_tip
        if is_upper:
            kr = 0
            box_h = h
        else:
            box_h = h - kr if h > kr and h >= 800 else h

        title = f"Шкаф [{m_num}] | {m_tip}"
        draw.text((150, 150), title, fill="black", font=f_title)
        draw.line([(150, 220), (2330, 220)], fill="black", width=5)
        
        actual_total_h = box_h + kr
        draw.text((150, 250), f"Габаритни размери: Ширина {int(w)} мм | Височина {int(actual_total_h)} мм | Дълбочина {int(d)} мм", fill="#555555", font=f_dim)

        center_x, center_y = 1240, 1800
        max_dim = max(w, box_h + kr, d)
        scale = 1100 / max_dim if max_dim > 0 else 1
        
        w_px = w * scale
        h_px = box_h * scale
        d_px = d * scale * 0.5  
        
        dx = d_px * 0.707
        dy = d_px * 0.707

        x0 = center_x - (w_px + dx) / 2
        y0 = center_y - (h_px + kr*scale - dy) / 2
        
        c_front = "black"
        c_back = "#aaaaaa"
        c_shelf = "#3c8dbc" 
        t_mm = 18
        t = t_mm * scale # 18mm дебелина в пиксели
        
        # ЗАДНИ ЛИНИИ (Вътрешна и външна рамка за дебелина)
        draw.rectangle([x0+dx, y0-dy, x0+w_px+dx, y0+h_px-dy], outline=c_back, width=2)
        draw.rectangle([x0+t+dx, y0+t-dy, x0+w_px-t+dx, y0+h_px-t-dy], outline=c_back, width=2)
        
        # СВЪРЗВАЩИ ДЪЛБОЧИННИ ЛИНИИ
        draw.line([(x0, y0), (x0+dx, y0-dy)], fill=c_back, width=2)
        draw.line([(x0+w_px, y0), (x0+w_px+dx, y0-dy)], fill=c_front, width=3) # Видима
        draw.line([(x0, y0+h_px), (x0+dx, y0-dy+h_px)], fill=c_back, width=2)
        draw.line([(x0+w_px, y0+h_px), (x0+w_px+dx, y0-dy+h_px)], fill=c_front, width=3) # Видима
        
        draw.line([(x0+t, y0+t), (x0+t+dx, y0+t-dy)], fill=c_back, width=2)
        draw.line([(x0+w_px-t, y0+t), (x0+w_px-t+dx, y0+t-dy)], fill=c_back, width=2)
        draw.line([(x0+t, y0+h_px-t), (x0+t+dx, y0+h_px-t-dy)], fill=c_back, width=2)
        draw.line([(x0+w_px-t, y0+h_px-t), (x0+w_px-t+dx, y0+h_px-t-dy)], fill=c_back, width=2)
        
        # ПРЕДНИ ЛИЦА (С ЯСНО ЗАСТЪПВАНЕ НА 18ММ)
        # Лява страница (до долу)
        draw.rectangle([x0, y0, x0+t, y0+h_px], outline=c_front, width=3)
        # Дясна страница (до долу)
        draw.rectangle([x0+w_px-t, y0, x0+w_px, y0+h_px], outline=c_front, width=3)
        # Таван (между страниците)
        draw.rectangle([x0+t, y0, x0+w_px-t, y0+t], outline=c_front, width=3)
        # Дъно (между страниците)
        draw.rectangle([x0+t, y0+h_px-t, x0+w_px-t, y0+h_px], outline=c_front, width=3)
        
        # РАФТОВЕ (3D с дебелина 18мм)
        num_shelves = get_val(mod, ['рафтове', 'Рафтове', 'raftove', 'Брой рафтове', 'бр. рафтове'], None)
        if num_shelves is None:
            if box_h <= 500: num_shelves = 0
            elif box_h <= 1000: num_shelves = 1
            elif box_h <= 1600: num_shelves = 2
            elif box_h <= 2000: num_shelves = 3
            else: num_shelves = 4
        else:
            num_shelves = int(num_shelves)

        dim_color = "#D32F2F"
        shelf_color_dim = "#2196F3"
        
        inner_h = box_h - 2*t_mm
        gap = (inner_h - num_shelves * t_mm) / (num_shelves + 1) if num_shelves > 0 else inner_h

        for i in range(1, num_shelves + 1):
            # Точна математика: от долния ръб на страницата -> дъно 18мм -> светъл отвор -> център на рафт (9мм)
            center_h_mm = t_mm + i * gap + (i - 1) * t_mm + (t_mm / 2)
            sy = y0 + h_px - (center_h_mm * scale)
            
            # Предна част на рафта
            draw.rectangle([x0+t, sy-t/2, x0+w_px-t, sy+t/2], outline=c_shelf, width=2)
            # Горна повърхност в дълбочина
            draw.line([(x0+t, sy-t/2), (x0+t+dx, sy-t/2-dy)], fill=c_shelf, width=2)
            draw.line([(x0+w_px-t, sy-t/2), (x0+w_px-t+dx, sy-t/2-dy)], fill=c_shelf, width=2)
            draw.line([(x0+t+dx, sy-t/2-dy), (x0+w_px-t+dx, sy-t/2-dy)], fill=c_shelf, width=2)
            
            # Оразмеряване до центъра на рафта (Отдясно)
            dim_x = x0 + w_px + 80 + (i * 75) 
            draw_dim(img, draw, dim_x, y0 + h_px, dim_x, sy, f"{int(center_h_mm)}", f_dim, shelf_color_dim, rotate=True)
            draw.line([(x0+w_px, sy), (dim_x, sy)], fill="#bbbbbb", width=2)
            draw.line([(x0+w_px, y0+h_px), (dim_x, y0+h_px)], fill="#bbbbbb", width=2)

        # ОРАЗМЕРИТЕЛНИ ЛИНИИ (ОСНОВНИ)
        dim_y = y0 + h_px + (kr * scale) + 80
        draw_dim(img, draw, x0, dim_y, x0+w_px, dim_y, f"{int(w)}", f_dim, dim_color)
        
        d_sx, d_sy = x0 + w_px + 40, y0 + h_px
        d_ex, d_ey = x0 + w_px + dx + 40, y0 + h_px - dy
        draw_dim(img, draw, d_sx, d_sy, d_ex, d_ey, f"{int(d)}", f_dim, dim_color)

        # ВИСОЧИНА НА КУТИЯТА (Отляво)
        dim_x_left = x0 - 80
        draw_dim(img, draw, dim_x_left, y0, dim_x_left, y0+h_px, f"{int(box_h)}", f_dim, dim_color, rotate=True)
        
        # КРАКА
        if kr > 0:
            kr_px = kr * scale
            draw.rectangle([x0+40, y0+h_px, x0+80, y0+h_px+kr_px], fill="#333333")
            draw.rectangle([x0+w_px-80, y0+h_px, x0+w_px-40, y0+h_px+kr_px], fill="#333333")
            draw.line([(x0-150, y0+h_px+kr_px), (x0+w_px+150, y0+h_px+kr_px)], fill="#999999", width=2)
            draw_dim(img, draw, dim_x_left, y0+h_px, dim_x_left, y0+h_px+kr_px, f"{int(kr)}", f_dim, dim_color, rotate=True)

        pages.append(img)

    if pages:
        import io
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_bytes.getvalue()
    return None
# --- 3. ГЕНЕРИРАНЕ НА ЕТИКЕТИ С 44 БРОЯ НА А4 ---
def generate_labels_pdf(boards_per_mat):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try:
        font_small = ImageFont.truetype(font_path, 20)
        font_text = ImageFont.truetype(font_path, 24)
        font_huge = ImageFont.truetype(font_path, 45)
        # УВЕЛИЧЕН ШРИФТ ЗА КАНТОВЕТЕ
        font_edge = ImageFont.truetype(font_path, 24) 
    except:
        font_small = font_text = font_huge = font_edge = ImageFont.load_default()

    labels = []
    for mat_name, boards in boards_per_mat.items():
        for board in boards:
            for p in board:
                p_copy = p.copy()
                p_copy['mat_label'] = mat_name
                labels.append(p_copy)

    if not labels: return None

    px_per_mm = 11.811
    page_w, page_h = 2480, 3508
    cols, rows = 4, 11

    label_w = int(44 * px_per_mm)
    label_h = int(20 * px_per_mm)
    margin_x = int(10 * px_per_mm)
    margin_y = int(12 * px_per_mm)
    gap_x = int(6 * px_per_mm)
    gap_y = int(7 * px_per_mm)
    padding = int(3 * px_per_mm)

    pages = []
    current_page = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(current_page)

    for i, lbl in enumerate(labels):
        if i > 0 and i % (cols * rows) == 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (page_w, page_h), 'white')
            draw = ImageDraw.Draw(current_page)

        col = (i % (cols * rows)) % cols
        row = (i % (cols * rows)) // cols
        x = margin_x + col * (label_w + gap_x)
        y = margin_y + row * (label_h + gap_y)

        draw.rectangle([x, y, x+label_w, y+label_h], outline="#dddddd", width=1)

        d1_t = get_edge_label_text(lbl.get('d1', ''))
        d2_t = get_edge_label_text(lbl.get('d2', ''))
        sh1_t = get_edge_label_text(lbl.get('sh1', ''))
        sh2_t = get_edge_label_text(lbl.get('sh2', ''))

        draw_edge_marking(draw, x, y, label_w, label_h, 'top', d1_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'bottom', d2_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'left', sh1_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'right', sh2_t, font_edge)

        m_num = str(lbl.get('mod_num', lbl.get('№', '0')))
        m_tip = str(lbl.get('mod_tip', ''))
        p_name = str(lbl.get('part_name', lbl.get('Детайл', '')))
        mat_text = str(lbl.get('mat_label', lbl.get('Плоскост', '')))
        
        if '|' in p_name:
            p_name = p_name.split('|')[0].strip()

        try: mod_abbr = get_module_abbrev(m_tip)
        except: mod_abbr = m_tip
        
        if mod_abbr.strip().lower() == p_name.strip().lower() or not mod_abbr.strip():
            top_text = f"[{m_num}] {p_name}"
        else:
            top_text = f"[{m_num}] {mod_abbr} | {p_name}"
            
        top_text = top_text.replace("Стандартен", "Ст.").replace("Долен", "Дол.").replace("Горен", "Гор.")

        dim_text = f"{int(lbl.get('l', 0))} x {int(lbl.get('w', 0))}"
        bot_text = f"{mat_text[:22]}"

        # СВАЛЯМЕ ГОРНИЯ ТЕКСТ ПО-НАДОЛУ (+20 пиксела), за да не пречи на канта
        draw.text((x + label_w/2, y + padding + 20), top_text, fill="black", font=font_text, anchor="mt")
        draw.text((x + label_w/2, y + label_h/2), dim_text, fill="black", font=font_huge, anchor="mm")
        draw.text((x + label_w/2, y + label_h - padding), bot_text, fill="black", font=font_small, anchor="mb")

    pages.append(current_page)

    pdf_bytes = io.BytesIO()
    pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_bytes.getvalue()
# --- 4. ПОТРЕБИТЕЛСКИ ИНТЕРФЕЙС (БУТОНИ) ---
st.markdown("---")
col_visuals, col_pdf = st.columns(2)

with col_pdf:
    st.subheader("📐 Технически PDF и Етикети")
    st.info("Генерира 3D чертежи за цеха и самозалепващи се етикети (44 бр. на А4).")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("📄 Свали PDF Чертежи"):
            if not st.session_state.modules_meta:
                st.warning("Няма добавени модули за чертане!")
            else:
                with st.spinner("Генериране..."):
                    kraka_val = kraka if 'kraka' in locals() or 'kraka' in globals() else 100
                    pdf_data = generate_technical_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka_val)
                    if pdf_data:
                        st.download_button(label="📥 ИЗТЕГЛИ PDF", data=pdf_data, file_name="OPTIVIK_Чертежи.pdf", mime="application/pdf")
                        
    with col_b2:
        if st.button("🏷️ Свали ЕТИКЕТИ (А4)"):
            if not st.session_state.order_list:
                st.warning("Добави детайли за етикетите!")
            else:
                with st.spinner("Генериране на етикети..."):
                    boards_per_mat, _, _, _ = get_optimized_boards(st.session_state.order_list)
                    try:
                        labels_pdf = generate_labels_pdf(boards_per_mat) 
                        if labels_pdf:
                            st.download_button(label="📥 ИЗТЕГЛИ ЕТИКЕТИ", data=labels_pdf, file_name="OPTIVIK_Етикети.pdf", mime="application/pdf")
                    except NameError:
                        st.error("Функцията за етикети липсва или не е заредена правилно.")

with col_visuals:
    st.subheader("✂️ Схема на разкроя (Плочи)")
    
    if st.button("📄 Свали Разкрой (A4 PDF)"):
        if not st.session_state.order_list:
            st.warning("Добави детайли за разкроя!")
        else:
            with st.spinner("Генериране на PDF..."):
                boards_per_mat, board_l, board_w, trim = get_optimized_boards(st.session_state.order_list)
                cut_pdf = generate_cutting_plan_pdf(boards_per_mat, board_l, board_w, trim)
                if cut_pdf:
                    st.download_button(label="📥 ИЗТЕГЛИ РАЗКРОЙ", data=cut_pdf, file_name="OPTIVIK_Разкрой.pdf", mime="application/pdf")
                    
    if st.button("Генерирай 2D разкрой на екрана"):
        if not st.session_state.order_list: 
            st.warning("Добави детайли, за да генерираш разкрой!")
        else:
            boards_per_mat, board_l, board_w, trim = get_optimized_boards(st.session_state.order_list)
            for mat_name, boards in boards_per_mat.items():
                st.markdown(f"#### 🪵 {mat_name} [2800x2070 мм] (Нужни: {len(boards)} бр.)")
                for idx, b_parts in enumerate(boards):
                    svg = f'<svg viewBox="0 0 {board_l} {board_w}" style="background-color:#ffffff; border:2px solid #333; margin-bottom: 20px; width: 100%; max-width: 900px;">'
                    svg += f'<rect x="{trim}" y="{trim}" width="{board_l - 2*trim}" height="{board_w - 2*trim}" fill="none" stroke="black" stroke-width="4" stroke-dasharray="20,20"/>'
                    for p in b_parts:
                        px, py, pl, pw = p['x'] + trim, p['y'] + trim, p['l'], p['w']
                        svg += f'<rect x="{px}" y="{py}" width="{pl}" height="{pw}" fill="#ffffff" stroke="#000000" stroke-width="2"/>'
                        
                        name_str = p["name"][:10] + '..' if len(p["name"]) > 10 and pl < 300 else p["name"][:18]
                        dim_str = f"{int(p['l'])}/{int(p['w'])}"
                        
                        if pl < 120 or pw < 120:
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2}" font-size="25" fill="black" text-anchor="middle" dominant-baseline="middle" font-weight="bold">{dim_str}</text>'
                        else:
                            f_size_name = min(45, max(15, int(pl / len(name_str) * 1.2)))
                            f_size_dim = min(50, max(20, int(pl / 5)))
                            shift = min(30, pw * 0.2)
                            
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2 - shift}" font-size="{f_size_name}" fill="black" text-anchor="middle" dominant-baseline="middle" font-weight="bold">{name_str}</text>'
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2 + shift}" font-size="{f_size_dim}" fill="black" text-anchor="middle" dominant-baseline="middle">{dim_str}</text>'
                    svg += '</svg>'
                    st.markdown(svg, unsafe_allow_html=True)

# --- ФИНАНСОВ КАЛКУЛАТОР (ОСТАВА НА ЕКРАНА!) ---
st.markdown("---")
st.subheader("💰 Финанси и Оферта (Само за екрана)")

if st.session_state.order_list:
    try:
        if 'edited_df' in locals():
            df_to_calc = edited_df
        else:
            df_to_calc = pd.DataFrame(st.session_state.order_list)
            
        df_to_calc['Area'] = (pd.to_numeric(df_to_calc['Дължина']) * pd.to_numeric(df_to_calc['Ширина']) * pd.to_numeric(df_to_calc['Бр'])) / 1000000
        summary = df_to_calc.groupby('Плоскост')['Area'].sum()
        
        boards_per_mat, _, _, _ = get_optimized_boards(st.session_state.order_list)
        total_boards_final = sum(len(boards) for boards in boards_per_mat.values())
        
        st.markdown("##### 1. Материали и Разкрой")
        col_mats, col_prices = st.columns([1, 1])
        
        total_material_cost = 0.0
        with col_mats:
            for mat_name, area in summary.items(): st.write(f"- **{mat_name}:** {area:.2f} м²")
            st.write(f"- **Брой плочи за разкрой:** {total_boards_final} бр.")
            
        with col_prices:
            for mat_name, area in summary.items():
                price = st.number_input(f"€/м² {mat_name}", value=25.0, key=f"p_{mat_name}")
                total_material_cost += area * price
            price_cut = st.number_input("€/бр. Разкрой", value=18.0)
            total_cut_cost = total_boards_final * price_cut
            
        st.markdown("##### 2. Кантове (+10% фира)")
        edge_dict = {}
        for _, row in df_to_calc.iterrows():
            try:
                l, w, count = float(row['Дължина']), float(row['Ширина']), int(row['Бр'])
                mat = row['Плоскост']
                for col, dim in [('Д1', l), ('Д2', l), ('Ш1', w), ('Ш2', w)]:
                    val = str(row[col]).strip()
                    if val and val.lower() != "без кант":
                        if val in ['1', '1.0']: edge_key = f"{mat} 0.8мм"
                        elif val in ['2', '2.0']: edge_key = f"{mat} 2мм"
                        else: edge_key = val 
                        
                        meters = (dim * count) / 1000.0
                        if meters > 0:
                            edge_dict[edge_key] = edge_dict.get(edge_key, 0) + meters
            except: pass
        
        total_edge_cost = 0.0
        if edge_dict:
            col_e1, col_e2 = st.columns([1, 1])
            with col_e1:
                for edge_name, meters in edge_dict.items():
                    meters_with_margin = meters * 1.10
                    st.write(f"- **{edge_name}:** {meters_with_margin:.1f} л.м.")
                    
            with col_e2:
                for edge_name, meters in edge_dict.items():
                    meters_with_margin = meters * 1.10
                    price = st.number_input(f"€/л.м. за {edge_name}", value=1.0, key=f"edge_pr_{edge_name}")
                    cost = meters_with_margin * price
                    total_edge_cost += cost
        else: st.write("Няма детайли за кантиране.")

        st.markdown("##### 3. Обков (Автоматично изчисление по проект)")
        total_hw_cost = 0.0
        if st.session_state.hardware_list:
            hw_df_calc = pd.DataFrame(st.session_state.hardware_list)
            hw_summary_calc = hw_df_calc.groupby("Артикул")["Брой"].sum().reset_index()
            col_h1, col_h2 = st.columns(2)
            
            for idx_h, row_h in hw_summary_calc.iterrows():
                item_name = row_h["Артикул"]
                item_qty = row_h["Брой"]
                def_val = 1.0
                if "Панти" in item_name: def_val = 1.5
                elif "водачи" in item_name: def_val = 18.0
                elif "Крака" in item_name: def_val = 0.4
                elif "Окачвачи" in item_name: def_val = 1.5
                elif "Рафтоносачи" in item_name: def_val = 0.1
                elif "LED" in item_name: def_val = 12.0
                elif "Механизъм" in item_name: def_val = 45.0
                elif "Дръжки" in item_name: def_val = 4.0

                with (col_h1 if idx_h % 2 == 0 else col_h2):
                    qty_str = f"{item_qty:.1f}" if isinstance(item_qty, float) and not item_qty.is_integer() else f"{int(item_qty)}"
                    u_price = st.number_input(f"€/ед. {item_name} ({qty_str})", value=def_val, key=f"hw_{item_name}")
                    total_hw_cost += item_qty * u_price
            st.info(f"Обща стойност на обкова: **{total_hw_cost:.2f} €**")

        st.markdown("##### 4. Плот и Гръб")
        col_ext1, col_ext2 = st.columns(2)
        with col_ext1: plot_cost = st.number_input("Плот (Общо) €", value=0.0)
        with col_ext2: grub_cost = st.number_input("Гръб (Общо) €", value=0.0)
        total_extra_mats = total_hw_cost + plot_cost + grub_cost

        st.markdown("##### 5. Труд, Услуги и Режийни разходи")
        col_labor, col_services = st.columns(2)
        
        with col_labor:
            project_days = st.number_input("Дни за този проект:", value=1, min_value=1)
            nadnici = st.number_input("Надници (общо/ден) €", value=225)
            
        with col_services:
            transport = st.number_input("Транспорт €", value=0)
            komandirovachni = st.number_input("Командировъчни €", value=0)
            hamal = st.number_input("Хамалски услуги €", value=0)

        # АВТОМАТИЧНИ МЕСЕЧНИ РАЗХОДИ (50€ на ден)
        fixed_daily_rate = 50.0
        total_fixed_project = project_days * fixed_daily_rate
        
        st.info(f"🏢 **Режийни разходи:** Автоматично добавени **{total_fixed_project:.2f} €** *(по {fixed_daily_rate:.0f} € на ден за наем, ток, осигуровки, бус и счетоводство)*")

        st.markdown("##### 6. Буфери и Печалба")
        col_buf1, col_buf2 = st.columns(2)
        with col_buf1: nepredvideni_pct = st.number_input("Непредвидени разходи (%)", value=15)
        with col_buf2: pechalba_pct = st.number_input("Печалба (%)", value=25)

        # Финални калкулации
        total_labor_cost = nadnici * project_days
        total_services = transport + komandirovachni + hamal
        
        total_materials_all = total_material_cost + total_cut_cost + total_edge_cost + total_extra_mats
        base_cost = total_materials_all + total_fixed_project + total_labor_cost + total_services
        
        unforeseen_cost = base_cost * (nepredvideni_pct / 100.0)
        sebestoinost = base_cost + unforeseen_cost
        profit_val = sebestoinost * (pechalba_pct / 100.0)
        final_offer = sebestoinost + profit_val
        
        st.markdown("### 📊 Оферта и Калкулация:")
        st.write(f"Материали/разкрой/обков: **{total_materials_all:.2f} €** | Труд: **{total_labor_cost:.2f} €** | Разходи: **{(total_fixed_project + total_services):.2f} €**")
        st.info(f"Вътрешна себестойност: **{sebestoinost:.2f} €**")
        st.success(f"ОФЕРТА КЪМ КЛИЕНТ: **{final_offer:.2f} €**")
        st.write(f"🌟 **Чиста печалба:** {profit_val:.2f} €")
        
    except Exception as e: 
        st.warning(f"Въведи валидни числа. Грешка: {e}")
        
