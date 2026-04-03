Кодът е твърде дълъг за един изглед. Ето го като файл за сваляне:
Action: $ cat /app/backend/app.py | head -1850
Observation: import streamlit as st
import pandas as pd
import os
import io
import json
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA, GuillotineBssfMaxas

# Настройки на страницата
st.set_page_config(page_title="OPTIVIK: Витя-М", layout="wide")

# --- CSS ЗА СБИТ ДИЗАЙН (ПО-КОМПАКТЕН) ---
st.markdown("""
<style>
html { zoom: 0.90; }
.stApp { background-color: #dce1e6 !important; } 
.opti-text { color: #000000; font-weight: bold; }
.vik-text { color: #FF0000; font-weight: bold; font-style: italic; }
div[data-baseweb="select"] {
    border: 2px solid #008080 !important;
    border-radius: 6px !important;
}
hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; border-color: #a3b0bd !important; }
/* ПО-МАЛКИ БУТОНИ */
.stButton>button { 
    background-color: #008080 !important; 
    color: white !important; 
    font-weight: bold !important; 
    border-radius: 5px !important; 
    border: none !important; 
    padding: 0.3rem 0.6rem !important; 
    font-size: 0.85rem !important;
    width: 100%; 
}
.stButton>button:hover { background-color: #005959 !important; }
[data-testid="stSidebar"] { background-color: #cdd4db !important; border-right: 2px solid #a3b0bd !important; } 
[data-testid="stDataFrame"] { filter: brightness(0.90) contrast(0.95); border-radius: 8px; overflow: hidden; }
.stTextInput, .stNumberInput, .stSelectbox, .stRadio { margin-bottom: -0.6rem !important; }
/* ПО-МАЛКА 3D ВИЗУАЛИЗАЦИЯ */
.preview-container img {
    max-height: 280px !important;
    width: auto !important;
}
.stSubheader { font-size: 1rem !important; margin-bottom: 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

# ГЛАВНОТО ЗАГЛАВИЕ
st.markdown("""
<h1 style='font-size: 28px; margin-top: 5px; margin-bottom: 5px;'>
    <span class='opti-text'>OPTI</span><span class='vik-text'>VIK</span>
</h1>
<p style='font-size: 14px; color: gray; margin-top: -5px; margin-bottom: 10px;'><i>оптимизирай умно</i></p>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ НА STATE ---
if 'order_list' not in st.session_state: 
    st.session_state.order_list = []
if 'hardware_list' not in st.session_state: 
    st.session_state.hardware_list = []
if 'modules_meta' not in st.session_state: 
    st.session_state.modules_meta = [] 
if 'history' not in st.session_state: 
    st.session_state.history = []

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

# --- СИНХРОНИЗИРАНА 3D ВИЗУАЛИЗАЦИЯ (СЪЩАТА ЛОГИКА КАТО PDF) ---
def draw_3d_preview(meta, kraka_height):
    """Рисува 3D изглед на шкафа - синхронизиран с PDF генератора"""
    from PIL import Image, ImageDraw
    import io
    import re
    
    tip = meta.get("Тип", "Стандартен")
    w = max(float(meta.get("W", 600)), 60)
    h_total = max(float(meta.get("H", 760)), 60)
    d = max(float(meta.get("D", 520)), 60)
    
    # Определяне дали е горен шкаф
    tip_lower = tip.lower()
    is_upper = "горен" in tip_lower or "надстройка" in tip_lower or tip == "Трети ред (Надстройка)"
    is_col = "колона" in tip_lower
    is_drawers = "чекмедже" in tip_lower
    
    # Крака само за долни шкафове
    has_legs = not is_upper
    kr = int(kraka_height) if has_legs else 0
    box_h = h_total - kr if has_legs and h_total > kr else h_total
    
    # Параметри от мета
    num_dividers = int(meta.get("num_dividers", 0))
    num_ch = int(meta.get("num_ch", 0))
    vr_cnt = int(meta.get("vr_cnt", 1))
    lower_door_h = float(meta.get("lower_door_h", 0))
    appliances_type = meta.get("appliances_type", "Без уреди")
    
    # Размер на платното - ПО-МАЛКО
    canvas_w, canvas_h = 400, 350
    img = Image.new('RGB', (canvas_w, canvas_h), '#ffffff')
    draw = ImageDraw.Draw(img)
    
    # Мащабиране
    center_x, center_y = canvas_w / 2, canvas_h / 2 - 10
    max_dim = max(w, box_h + kr, d)
    scale = (canvas_w * 0.50) / max_dim if max_dim > 0 else 1
    
    w_px = w * scale
    h_px = box_h * scale
    d_px = d * scale * 0.5
    
    dx = d_px * 0.707
    dy = d_px * 0.707
    
    x0 = center_x - (w_px + dx) / 2
    y0 = center_y - (h_px + kr*scale - dy) / 2 + (10 if kr > 0 else 0)
    
    c_front = "black"
    c_back = "#aaaaaa"
    c_shelf = "#3c8dbc"
    t_mm = 18
    t = t_mm * scale
    
    # Определяне на конструкцията
    bottom_under_sides = not is_upper
    
    # Основни дъски
    boards = []
    if bottom_under_sides:
        boards.append((x0, y0, t, h_px - t))  # лява страница
        boards.append((x0 + w_px - t, y0, t, h_px - t))  # дясна страница
        boards.append((x0 + t, y0, w_px - 2*t, t))  # таван
        boards.append((x0, y0 + h_px - t, w_px, t))  # дъно
    else:
        boards.append((x0, y0, t, h_px))  # лява страница
        boards.append((x0 + w_px - t, y0, t, h_px))  # дясна страница
        boards.append((x0 + t, y0, w_px - 2*t, t))  # таван
        boards.append((x0 + t, y0 + h_px - t, w_px - 2*t, t))  # дъно
    
    # Вертикални делители
    if num_dividers > 0:
        num_sections = num_dividers + 1
        inner_w_px = (w_px - (2 + num_dividers) * t) / num_sections
        for i in range(1, num_dividers + 1):
            div_x = x0 + t + i * inner_w_px + (i - 1) * t
            div_y = y0 + t
            div_h = h_px - 2*t
            boards.append((div_x, div_y, t, div_h))
    
    # Рисуване на 3D дъски (задна част)
    for bx, by, bw, bh in boards:
        draw.rectangle([bx+dx, by-dy, bx+bw+dx, by+bh-dy], outline=c_back, width=1)
        draw.line([(bx, by), (bx+dx, by-dy)], fill=c_back, width=1)
        draw.line([(bx+bw, by), (bx+bw+dx, by-dy)], fill=c_back, width=1)
        draw.line([(bx, by+bh), (bx+dx, by+bh-dy)], fill=c_back, width=1)
        draw.line([(bx+bw, by+bh), (bx+bw+dx, by+bh-dy)], fill=c_back, width=1)
    
    # 3D линии към зрителя
    draw.line([(x0, y0), (x0+dx, y0-dy)], fill=c_front, width=2)
    draw.line([(x0+w_px, y0), (x0+w_px+dx, y0-dy)], fill=c_front, width=2)
    draw.line([(x0+w_px, y0+h_px), (x0+w_px+dx, y0+h_px-dy)], fill=c_front, width=2)
    
    # Рисуване на предната част
    for bx, by, bw, bh in boards:
        draw.rectangle([bx, by, bx+bw, by+bh], outline=c_front, width=2)
    
    # Рафтове (ако няма чекмеджета)
    if num_ch == 0 and not is_drawers:
        num_shelves = 1 if box_h <= 800 else 2
        if is_col:
            num_shelves = 3
        
        space = box_h - 2*t_mm
        gap = space / (num_shelves + 1)
        
        for i in range(1, num_shelves + 1):
            shelf_y_mm = i * gap
            sy = y0 + t + (shelf_y_mm * scale)
            shelf_left = x0 + t
            shelf_width = w_px - 2*t
            
            # 3D рафт
            draw.rectangle([shelf_left+dx, sy-t/2-dy, shelf_left+shelf_width+dx, sy+t/2-dy], outline=c_shelf, width=1)
            draw.line([(shelf_left, sy-t/2), (shelf_left+dx, sy-t/2-dy)], fill=c_shelf, width=1)
            draw.line([(shelf_left+shelf_width, sy-t/2), (shelf_left+shelf_width+dx, sy-t/2-dy)], fill=c_shelf, width=1)
            draw.rectangle([shelf_left, sy-t/2, shelf_left+shelf_width, sy+t/2], outline=c_shelf, width=1)
    
    # Чекмеджета (хоризонтални линии)
    if num_ch > 0 or is_drawers:
        actual_drawers = num_ch if num_ch > 0 else 3
        drawer_h = (h_px - t) / actual_drawers
        
        for i in range(1, actual_drawers):
            line_y = y0 + i * drawer_h
            draw.line([(x0, line_y), (x0 + w_px, line_y)], fill=c_front, width=2)
    
    # Крака
    if kr > 0:
        kr_px = kr * scale
        leg_w = t * 2
        draw.rectangle([x0 + w_px*0.1, y0+h_px, x0 + w_px*0.1 + leg_w, y0+h_px+kr_px], fill="#333333")
        draw.rectangle([x0 + w_px*0.9 - leg_w, y0+h_px, x0 + w_px*0.9, y0+h_px+kr_px], fill="#333333")
        # Линия на пода
        draw.line([(x0, y0+h_px+kr_px), (x0+w_px, y0+h_px+kr_px)], fill="#999999", width=1)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.markdown("### ⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    deduct_edge = st.checkbox("Приспадай дебелината на канта", value=False, key="deduct_edge")
    gola_profile = st.checkbox("Профил Gola (-30мм)", value=False, key="gola_profile")
    
    st.markdown("---")
    st.markdown("### 🎨 Материали")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло гладко 18мм")
    val_fl_korpus = "Да" if st.checkbox("Фладер - Корпус", value=False) else "Няма"
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    val_fl_lice = "Да" if st.checkbox("Фладер - Лице", value=True) else "Няма"
    mat_chekm = st.text_input("Декор Чекмеджета:", value="Бяло гладко 18мм")
    val_fl_chekm = "Да" if st.checkbox("Фладер - Чекмеджета", value=False) else "Няма"
    mat_fazer = st.text_input("Декор Фазер:", value="Бял фазер 3мм")
    
    st.markdown("---")
    st.markdown("### 🪚 Кантове")
    edges_input = st.text_area("Налични кантове:", value="Без кант\n0.8мм\n2мм\nБяло 0.8мм\nБяло 2мм\nДъб Вотан 0.8мм\nДъб Вотан 2мм", height=120)
    available_edges = [e.strip() for e in edges_input.split('\n') if e.strip()]
    if "Без кант" not in available_edges:
        available_edges.insert(0, "Без кант")
        
    st.markdown("---")
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []
        st.session_state.hardware_list = []
        st.session_state.modules_meta = []
        st.rerun()

    # --- ЗАПИС И ЗАРЕЖДАНЕ ---
    st.markdown("---")
    st.markdown("### 💾 Проект")
    
    if st.session_state.order_list:
        export_data = {
            "order": st.session_state.order_list,
            "hw": st.session_state.hardware_list,
            "meta": st.session_state.modules_meta
        }
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Запази",
            data=json_data,
            file_name=f"proekt_kuhnya.json",
            mime="application/json"
        )
    
    uploaded_file = st.file_uploader("📂 Зареди", type="json", key="uploader")
    
    if uploaded_file is not None:
        try:
            file_content = json.load(uploaded_file)
            if st.button("🔄 ВЪЗСТАНОВИ"):
                st.session_state.order_list = file_content.get("order", [])
                st.session_state.hardware_list = file_content.get("hw", [])
                st.session_state.modules_meta = file_content.get("meta", [])
                st.session_state.history = []
                st.success("✅ Заредено!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Грешка: {e}")

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.8])

with col1:
    st.markdown("#### 📝 Добави Модул")
    
    cat_choice = st.radio("Категория:", ["🍳 Кухненски", "🏢 Колони"], horizontal=True)

    if cat_choice == "🍳 Кухненски":
        icons = {
            "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", 
            "Шкаф Мивка": "🚰", "Шкаф с чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", 
            "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"
        }
    else:
        icons = {
            "Шкаф Колона": "🏢", 
            "Шкаф с меж. стр.": "🚪",  
            "Дублираща страница долен": "🗂️", 
            "Нестандартен": "🧩"
        }

    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    name = st.text_input("Име/№ на модула", value=tip)
    
    st.markdown("---")
    flader_posoka = st.radio("🔄 Фладер:", ["Вертикален", "Хоризонтален"], horizontal=True)
    st.markdown("---")
    
    appliances_type = "Без уреди"
    split_doors = False
    lower_door_h = 0
    lower_type = "Врата"
    vrati_broi = 1
    ch_heights = []
    runner_len = 500
    custom_mat_name = "ПДЧ 18мм (Друго)"
    custom_edges_dict = {}
    num_dividers = 0
    section_shelves = []
    mod_podtip = ""
    h_box = 760
    
    if tip == "Дублираща страница долен":
        h = st.number_input("Височина (H) мм", value=860)
        d = st.number_input("Дълбочина (D) мм", value=580)
        w = deb
    elif tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина (W) мм", value=600, key="w_tret")
        h = st.number_input("Височина (H) мм", value=350, key="h_tret")
        d = st.number_input("Дълбочина (D) мм", value=500, key="d_tret")
        vrati_broi = st.radio("Брой врати:", [1, 2], index=0, horizontal=True, key="vr_tret")
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Нестандартен детайл")
        colA, colB, colC = st.columns(3)
        h = custom_l = colA.number_input("Дължина (L) мм", value=600)
        d = custom_w = colB.number_input("Ширина (W) мм", value=300)
        w = deb
        custom_count = colC.number_input("Брой", value=1, min_value=1)
        
        colE, colF = st.columns(2)
        custom_mat_type = colE.selectbox("Материал", ["Корпус", "Лице", "Чекмеджета", "Фазер", "Специфичен"])
        custom_flader = colF.radio("Фладер?", ["Да", "Не"], index=0, horizontal=True)
        if custom_mat_type == "Специфичен":
            custom_mat_name = st.text_input("Име материал:", value="ПДЧ 18мм")
            
        st.markdown("##### 📏 Кантове")
        colD1, colD2, colSh1, colSh2 = st.columns(4)
        c_d1 = colD1.selectbox("Д1", available_edges, index=0)
        c_d2 = colD2.selectbox("Д2", available_edges, index=0)
        c_sh1 = colSh1.selectbox("Ш1", available_edges, index=0)
        c_sh2 = colSh2.selectbox("Ш2", available_edges, index=0)
        custom_edges_dict = {"Д1": c_d1, "Д2": c_d2, "Ш1": c_sh1, "Ш2": c_sh2}
        
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600, key="w_col")
        h_korpus = st.number_input("Височина корпус (H) мм", value=2040, key="h_col")
        d = st.number_input("Дълбочина (D) мм", value=550, key="d_col")
        appliances_type = st.radio("Уреди:", ["Без уреди", "Само Фурна", "Фурна + МВ"], horizontal=True)
        if appliances_type != "Без уреди":
            lower_door_h = st.number_input("Долна част мм", value=718)
            lower_type = st.radio("Тип долна:", ["Врата", "2 Чекм.", "3 Чекм."], horizontal=True)
            if "Чекм" in lower_type: runner_len = st.number_input("Водач (мм)", value=500, step=50, key="run_col")
        else:
            split_doors = st.checkbox("Две врати?", value=True)
            if split_doors: lower_door_h = st.number_input("Долна врата (мм)", value=718)
        vrati_broi = st.radio("Врати на ред:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_col")
        h = h_korpus + kraka 

    elif tip == "Шкаф с меж. стр.":
        st.info("Модул с делители")
        mod_podtip = st.radio("Вид:", ["Долен с делител", "Горен с делител"], horizontal=True)
        
        colA, colB, colC = st.columns(3)
        w = colA.number_input("W мм", value=1200)
        h_box = colB.number_input("H мм", value=760 if "Долен" in mod_podtip else 720)
        d = colC.number_input("D мм", value=520 if "Долен" in mod_podtip else 300)
        
        num_dividers = st.slider("Брой делители:", 1, 6, 1)
        num_sections = num_dividers + 1 
        
        st.markdown("##### 📚 Рафтове по секции")
        cols_shelves = st.columns(num_sections)
        section_shelves = []
        
        for i in range(num_sections):
            with cols_shelves[i]:
                val = st.number_input(f"С{i+1}", min_value=0, value=2, key=f"shelf_sec_{i}")
                section_shelves.append(val)
        
        vrati_broi = st.radio("Врати:", list(range(8)), index=num_sections if num_sections <= 7 else 0, horizontal=True)
        h = h_box + (kraka if "Долен" in mod_podtip else 0)

    elif tip == "Шкаф с чекмеджета":
        w = st.number_input("Ширина (W) мм", value=600, key="w_ch")
        h_box = st.number_input("Корпус без крака (мм)", value=760, key="h_box_ch")
        num_ch = st.slider("Брой чекмеджета:", 1, 6, 3, key="n_ch")
        
        total_front_h = h_box
        st.markdown(f"##### ↕️ Разпределение ({total_front_h} мм):")
        
        cols_ch = st.columns(num_ch)
        ch_heights = []
        accumulated_h = 0
        
        for i in range(num_ch - 1):
            with cols_ch[i]:
                rem_drawers = num_ch - i
                default_h = int((total_front_h - accumulated_h) / rem_drawers)
                val_h = st.number_input(f"Ч{i+1}", value=default_h, min_value=50, key=f"ch_h_inp_{i}")
                ch_heights.append(val_h)
                accumulated_h += val_h
                
        last_ch_h = total_front_h - accumulated_h
        ch_heights.append(last_ch_h)
        
        with cols_ch[-1]:
            st.info(f"Ч{num_ch}: {last_ch_h} мм")
                
        runner_len = st.number_input("Водач (мм)", value=500, step=50, key="run_ch")
        d = st.number_input("Дълбочина (D) мм", value=520, key="d_ch")
        h = h_box + kraka

    else:
        default_w = 150 if tip == "Шкаф Бутилки 15см" else (1000 if "Глух" in tip else 600)
        w = st.number_input("Ширина (W) мм", value=default_w, key="w_std")
        if "Горен" in tip:
            h = st.number_input("Височина (H) мм", value=720, key="h_up")
            d = st.number_input("Дълбочина (D) мм", value=300, key="d_up")
            vrati_broi = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_up")
            vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални"], horizontal=True) if tip == "Горен Шкаф" else "Вертикални"
        else:
            h_box = st.number_input("Корпус без крака (мм)", value=760, key="h_box_low")
            d = st.number_input("Дълбочина (D) мм", value=(550 if tip == "Шкаф Мивка" else 520), key="d_low")
            h = h_box + kraka 
            vrati_broi = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_low")

    st.markdown("---")
    
    # Мета данни за визуализацията
    temp_meta = {
        "Тип": tip, "W": w, "H": h, "D": d, 
        "vr_cnt": locals().get('vrati_broi', 0), 
        "num_dividers": locals().get('num_dividers', 0),
        "num_ch": locals().get('num_ch', 0) if 'num_ch' in dir() else len(ch_heights) if ch_heights else 0,
        "lower_door_h": locals().get('lower_door_h', 0),
        "appliances_type": locals().get('appliances_type', "Без уреди"),
        "fl_posoka": flader_posoka
    }

    if st.button("➕ Добави"):
        current_snap = {
            "order": json.loads(json.dumps(st.session_state.order_list)),
            "hw": json.loads(json.dumps(st.session_state.hardware_list)),
            "meta": json.loads(json.dumps(st.session_state.modules_meta))
        }
        st.session_state.history.append(current_snap)
        
        if len(st.session_state.history) > 15:
            st.session_state.history.pop(0)

        new_items = []
        new_hw = []
        otstyp_fazer = 4
        
        if "Долен" in tip or tip in ["Шкаф Мивка", "Шкаф Бутилки 15см", "Шкаф за Фурна", "Шкаф с чекмеджета"] or (tip == "Шкаф с меж. стр." and "Долен" in mod_podtip):
            h_stranica = int(h - kraka - deb)
        else:
            h_stranica = 742 
            
        h_shkaf_korpus = h_stranica + deb
        gola_offset = 30 if st.session_state.get("gola_profile", False) else 0
        h_vrata_standart = h_shkaf_korpus - fuga_obshto - gola_offset
        
        meta_dict = {"№": name, "Тип": tip, "W": w, "H": h, "D": d}
        if tip == "Шкаф Колона":
            meta_dict.update({"app_type": appliances_type, "ld_h": lower_door_h, "lower_type": lower_type})
        elif tip == "Шкаф с меж. стр.":
            meta_dict.update({"mod_tip": mod_podtip, "section_shelves": section_shelves, "num_dividers": num_dividers})
        
        st.session_state.modules_meta.append(meta_dict)

        def get_front_dims(h_front, w_front):
            if flader_posoka == "Хоризонтален":
                return w_front, h_front, "В БЛОК Х"
            return h_front, w_front, "В БЛОК"

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Шкаф Бутилки 15см", "Глух Ъгъл (Долен)", "Шкаф за Фурна", "Шкаф с чекмеджета", "Шкаф Колона"] or (tip == "Шкаф с меж. стр." and "Долен" in mod_podtip):
            hw_legs = 5 if w > 900 else 4
            new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": hw_legs})

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Горен Шкаф", "Шкаф с меж. стр."]:
            if vrati_broi > 0:
                h_door_hw = h_vrata_standart if "Горен" not in tip else (h - fuga_obshto if 'vrati_orientacia' not in locals() or vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto)))
                hw_hinges = calculate_hinges(h_door_hw) * vrati_broi
                new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
                new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})

        # ЛОГИКА ЗА РАЗКРОЙ (ЗАПАЗЕНА ОТ ОРИГИНАЛА)
        if tip == "Шкаф с меж. стр.":
            inner_w = (w - (2 + num_dividers) * deb) / (num_dividers + 1)
            h_k = h_box
            
            if "Долен" in mod_podtip:
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница лява", 1, h_k - deb, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница дясна", 1, h_k - deb, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Таван", 1, w - 2*deb, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Междинна страница", num_dividers, h_k - 2*deb, d, "1д", mat_korpus, val_fl_korpus)
                ])
                h_vrata = h_k - fuga_obshto - gola_offset
            else: 
                new_items.extend([
                    add_item(name, tip, "Страница лява", 1, h_k, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница дясна", 1, h_k, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Таван", 1, w - 2*deb, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Дъно", 1, w - 2*deb, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Междинна страница", num_dividers, h_k - 2*deb, d, "1д", mat_korpus, val_fl_korpus)
                ])
                h_vrata = h_k - fuga_obshto
                
            for i, sh_count in enumerate(section_shelves):
                if sh_count > 0:
                    new_items.append(add_item(name, tip, f"Рафт подв. Секция {i+1}", sh_count, inner_w - 1, d, "1д", mat_korpus, val_fl_korpus))
            
            if vrati_broi > 0:
                w_vrata = (w - (vrati_broi + 1) * fuga_obshto) / vrati_broi
                lf, wf, nf = get_front_dims(h_vrata, w_vrata)
                new_items.append(add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf))
            
            new_items.append(add_item(name, tip, "Гръб (Фазер)", 1, h_k - 4, w - 4, "Без", mat_fazer, "Няма"))

        elif tip == "Трети ред (Надстройка)":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else int(w - fuga_obshto)
            lf, wf, nf = get_front_dims(h - fuga_obshto, w_izbrana)
            
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница (вътрешна)", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf)
            ])

        elif tip == "Шкаф Мивка":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else w - fuga_obshto
            lf, wf, nf = get_front_dims(h_vrata_standart, w_izbrana)
            
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, 480, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Бленда", 3, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf)
            ])

        elif tip == "Стандартен Долен":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else w - fuga_obshto
            new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 4})
            lf, wf, nf = get_front_dims(h_vrata_standart, w_izbrana)
            
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf), 
                add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])

        elif tip == "Шкаф Бутилки 15см":
            lf, wf, nf = get_front_dims(h_vrata_standart, w - fuga_obshto)
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Врата", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])

        elif tip == "Шкаф за Фурна":
            cargi_w = w - (2*deb) - 49
            duno_w = cargi_w + 12
            duno_l = runner_len - 13
            h_tsarga_furna = 157 - 60
            lf, wf, nf = get_front_dims(157, w - fuga_obshto)
            
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                add_item(name, tip, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Чело чекмедже", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf), 
                add_item(name, tip, "Царги чекм.", 2, cargi_w, h_tsarga_furna, "1д", mat_chekm, val_fl_chekm),
                add_item(name, tip, "Страници чекм.", 2, runner_len - 10, h_tsarga_furna, "2д", mat_chekm, val_fl_chekm),
                add_item(name, tip, "Дъно чекмедже", 1, duno_l, duno_w, "Без", mat_fazer, "Няма")
            ])

        elif tip == "Шкаф с чекмеджета":
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
                final_front_h = ch_h - fuga_obshto - gola_offset
                h_tsarga = int(final_front_h - 60)
                lf, wf, nf = get_front_dims(final_front_h, w - fuga_obshto)
                
                new_items.extend([
                    add_item(name, tip, f"Чело {idx+1}", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                    add_item(name, tip, f"Царги чекм. {idx+1}", 2, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, f"Страници чекм. {idx+1}", 2, runner_len - 10, h_tsarga, "2д", mat_chekm, val_fl_chekm)
                ])
            new_items.append(add_item(name, tip, "Дъно чекмедже", len(ch_heights), duno_l, duno_w, "Без", mat_fazer, "Няма"))

        elif tip == "Шкаф Колона":
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else int(w - fuga_obshto)
            h_korpus = h - kraka
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h_korpus - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            if appliances_type != "Без уреди":
                h_furn = 595
                h_mw = 380 if appliances_type == "Фурна + МВ" else 0
                h_door_upper = h_korpus - lower_door_h - h_furn - h_mw - (fuga_obshto * 2) 
                
                if appliances_type == "Фурна + МВ":
                    new_items.extend([
                        add_item(name, tip, "Рафт тв. (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (под МВ)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (над МВ)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт подвижен", 2, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                    ])
                elif appliances_type == "Само Фурна":
                    new_items.extend([
                        add_item(name, tip, "Рафт тв. (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт тв. (над фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт подвижен", 2, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                    ])
            
                if lower_type == "Врата":
                    lf, wf, nf = get_front_dims(lower_door_h, w_izbrana)
                    new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf))
                else: 
                    num_c = 2 if lower_type == "2 Чекм." else 3
                    chelo_h = lower_door_h / num_c
                    h_tsarga = int(chelo_h - 60)
                    for idx in range(num_c):
                        lf, wf, nf = get_front_dims(chelo_h - fuga_obshto, w - fuga_obshto)
                        new_items.extend([
                            add_item(name, tip, f"Чело долно {idx+1}", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                            add_item(name, tip, f"Царги чекм.", 2, w - (2*deb) - 49, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                            add_item(name, tip, f"Страници чекм.", 2, runner_len - 10, h_tsarga, "2д", mat_chekm, val_fl_chekm)
                        ])
                    new_items.append(add_item(name, tip, "Дъно чекмедже", num_c, runner_len - 13, w - (2*deb) - 49 + 12, "Без", mat_fazer, "Няма"))
                
                lf_up, wf_up, nf_up = get_front_dims(h_door_upper, w_izbrana)
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, lf_up, wf_up, "4 страни", mat_lice, val_fl_lice, nf_up))
            else: 
                new_items.extend([
                    add_item(name, tip, "Рафт твърд", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Рафт подвижен", 3, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus)
                ])
                if split_doors:
                    lf_d, wf_d, nf_d = get_front_dims(lower_door_h, w_izbrana)
                    lf_u, wf_u, nf_u = get_front_dims(h_korpus - lower_door_h - fuga_obshto, w_izbrana)
                    new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lf_d, wf_d, "4 страни", mat_lice, val_fl_lice, nf_d))
                    new_items.append(add_item(name, tip, "Врата горна", vrati_broi, lf_u, wf_u, "4 страни", mat_lice, val_fl_lice, nf_u))
                else:
                    lf, wf, nf = get_front_dims(h_korpus - fuga_obshto, w_izbrana)
                    new_items.append(add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf))

        elif tip == "Горен Шкаф":
            shelves_count = 2 if h > 800 else 1
            new_items.extend([
                add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Рафт", shelves_count, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            lf, wf, nf = get_front_dims(h - fuga_obshto, int(w/vrati_broi - fuga_obshto))
            new_items.append(add_item(name, tip, "Врата", vrati_broi, lf, wf, "4 страни", mat_lice, val_fl_lice, nf))

        elif tip == "Нестандартен":
            if custom_mat_type == "Лице": m_choice = mat_lice
            elif custom_mat_type == "Чекмеджета": m_choice = mat_chekm
            elif custom_mat_type == "Фазер": m_choice = mat_fazer
            elif custom_mat_type == "Специфичен": m_choice = custom_mat_name
            else: m_choice = mat_korpus
            f_choice = custom_flader 
            new_items.append(add_item(name, tip, custom_detail, custom_count, custom_l, custom_w, "", m_choice, f_choice, custom_edges=custom_edges_dict))

        elif tip == "Дублираща страница долен":
   
... [stdout truncated]
Exit code: 0
