import streamlit as st
import pandas as pd
import os
import io
import json  # За работа със запис/зареждане на файлове
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA, GuillotineBssfMaxas

# Настройки на страницата (ТОВА ВИНАГИ ТРЯБВА ДА Е ПЪРВО)
st.set_page_config(page_title="OPTIVIK: Витя-М", layout="wide")

# --- ДИЗАЙН ЗА ГЛОБАЛНИТЕ НАСТРОЙКИ ---
st.markdown("""
<style>
/* Оцветяваме фона и слагаме рамка на падащото меню */
[data-testid="stExpander"] summary {
    background-color: #e6f2ff; 
    border: 2px solid #1c83e1; 
    border-radius: 8px;
    padding: 10px;
}
/* Увеличаваме и удебеляваме текста */
[data-testid="stExpander"] summary p {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #004085 !important;
}
/* Правим самата стрелкичка много по-голяма и синя */
[data-testid="stExpander"] summary svg {
    width: 28px !important;
    height: 28px !important;
    color: #1c83e1 !important;
}
</style>
""", unsafe_allow_html=True)

# --- CSS ЗА СБИТ ДИЗАЙН (БЕЗ ЗАСТЪПВАНЕ) ---
st.markdown("""
<style>
html { zoom: 0.95; } /* Връщаме оригиналния размер за добра четимост */
.stApp { background-color: #dce1e6 !important; } 
.opti-text { color: #000000; font-weight: bold; }
.vik-text { color: #FF0000; font-weight: bold; font-style: italic; }
div[data-baseweb="select"] {
    border: 2px solid #008080 !important;
    border-radius: 6px !important;
}
hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; border-color: #a3b0bd !important; }

/* Бутони - прибрани, но не прекалено смачкани */
.stButton>button { 
    background-color: #008080 !important; 
    color: white !important; 
    font-weight: bold !important; 
    border-radius: 6px !important; 
    border: none !important; 
    padding: 0.3rem 0.8rem !important; 
    width: 100%; 
}
.stButton>button:hover { background-color: #005959 !important; }

/* Отстояния - свиваме ги внимателно по вертикала */
[data-testid="stSidebar"] { background-color: #cdd4db !important; border-right: 2px solid #a3b0bd !important; } 
[data-testid="stDataFrame"] { filter: brightness(0.90) contrast(0.95); border-radius: 8px; overflow: hidden; }
.stTextInput, .stNumberInput, .stSelectbox, .stRadio { margin-bottom: -5px !important; }
div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; } /* Обира въздуха между редовете */
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

# --- НОВА ФУНКЦИЯ ЗА ЖИВА 3D СКИЦА (КАТО В PDF-А) ---
def draw_3d_preview(meta, kraka_height):
    from PIL import Image, ImageDraw, ImageFont
    import io
    import math
    
    # Опитваме да заредим хубавия шрифт за размерите
    try: f_dim = ImageFont.truetype("Roboto-Regular.ttf", 16)
    except: f_dim = ImageFont.load_default()
        
    # Вътрешна помощна функция за чертане на червени размери
    def draw_dim(img, draw, x1, y1, x2, y2, text, font, color, rotate=False):
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        dist = math.hypot(x2-x1, y2-y1)
        if dist < 1: return
        ux, uy = (x2-x1)/dist, (y2-y1)/dist
        
        txt_img_temp = Image.new('RGBA', (10, 10), (255,255,255,0))
        temp_draw = ImageDraw.Draw(txt_img_temp)
        bbox = temp_draw.textbbox((0,0), text, font=font)
        tw = bbox[2] - bbox[0]
        gap = (tw / 2) + 4
        
        if dist > gap * 2:
            draw.line([(x1, y1), (mid_x - ux*gap, mid_y - uy*gap)], fill=color, width=2)
            draw.line([(mid_x + ux*gap, mid_y + uy*gap), (x2, y2)], fill=color, width=2)
        else:
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
            
        tick_len = 5
        if abs(x2-x1) > abs(y2-y1):
            draw.line([(x1, y1-tick_len), (x1, y1+tick_len)], fill=color, width=2)
            draw.line([(x2, y2-tick_len), (x2, y2+tick_len)], fill=color, width=2)
        else:
            draw.line([(x1-tick_len, y1), (x1+tick_len, y1)], fill=color, width=2)
            draw.line([(x2-tick_len, y2), (x2+tick_len, y2)], fill=color, width=2)
            
        txt_img = Image.new('RGBA', (100, 40), (255,255,255,0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((50, 20), text, fill=color, font=font, anchor="mm")
        
        if rotate:
            txt_img = txt_img.rotate(90, expand=True)
            rot_w, rot_h = txt_img.size
            img.paste(txt_img, (int(mid_x - rot_w/2), int(mid_y - rot_h/2)), txt_img)
        else:
            img.paste(txt_img, (int(mid_x - 50), int(mid_y - 20)), txt_img)

    # Вземаме данните от менюто
    tip = meta.get("Тип", "Стандартен")
    w = max(float(meta.get("W", 600)), 60)
    h_total = max(float(meta.get("H", 760)), 60)
    d = max(float(meta.get("D", 520)), 60)
    
    is_upper = "горен" in tip.lower() or "надстройка" in tip.lower()
    is_col = "колона" in tip.lower()
    has_legs = not is_upper and tip != "Трети ред (Надстройка)"
    kr = int(kraka_height) if has_legs else 0
    box_h = h_total - kr if has_legs else h_total
    
    canvas_w, canvas_h = 600, 600
    
    # ТУК Е ПРОМЯНАТА: Създаваме прозрачен фон (RGBA), за да се слее със сивия интерфейс!
    img = Image.new('RGBA', (canvas_w, canvas_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    center_x, center_y = canvas_w / 2, canvas_h / 2
    max_dim = max(w, box_h + kr, d)
    scale = (canvas_w * 0.45) / max_dim if max_dim > 0 else 1
    
    w_px = w * scale
    h_px = box_h * scale
    d_px = d * scale * 0.5  
    
    dx, dy = d_px * 0.707, d_px * 0.707
    x0 = center_x - (w_px + dx) / 2
    y0 = center_y - (h_px + kr*scale - dy) / 2
    
    c_front, c_back, c_shelf = "black", "#aaaaaa", "#3c8dbc"
    t_mm = 18
    t = t_mm * scale 
    
    bottom_under_sides = not is_upper
    
    # 1. Чертаем Корпуса
    boards = []
    if bottom_under_sides:
        boards.extend([(x0, y0, t, h_px - t), (x0 + w_px - t, y0, t, h_px - t), (x0 + t, y0, w_px - 2*t, t), (x0, y0 + h_px - t, w_px, t)])
    else:
        boards.extend([(x0, y0, t, h_px), (x0 + w_px - t, y0, t, h_px), (x0 + t, y0, w_px - 2*t, t), (x0 + t, y0 + h_px - t, w_px - 2*t, t)])
        
    num_dividers = int(meta.get("num_dividers", 0))
    if num_dividers > 0:
        inner_w_px = (w_px - (2 + num_dividers) * t) / (num_dividers + 1)
        for i in range(1, num_dividers + 1):
            boards.append((x0 + t + i * inner_w_px + (i - 1) * t, y0 + t, t, h_px - 2*t))

    for bx, by, bw, bh in boards:
        draw.rectangle([bx+dx, by-dy, bx+bw+dx, by+bh-dy], outline=c_back, width=2)
        draw.line([(bx, by), (bx+dx, by-dy)], fill=c_back, width=2)
        draw.line([(bx+bw, by), (bx+bw+dx, by-dy)], fill=c_back, width=2)
        draw.line([(bx, by+bh), (bx+dx, by+bh-dy)], fill=c_back, width=2)
        draw.line([(bx+bw, by+bh), (bx+bw+dx, by+bh-dy)], fill=c_back, width=2)

    draw.line([(x0, y0), (x0+dx, y0-dy)], fill=c_front, width=3)
    draw.line([(x0+w_px, y0), (x0+w_px+dx, y0-dy)], fill=c_front, width=3)
    draw.line([(x0+w_px, y0+h_px), (x0+w_px+dx, y0+h_px-dy)], fill=c_front, width=3)

    for bx, by, bw, bh in boards:
        draw.rectangle([bx, by, bx+bw, by+bh], outline=c_front, width=2)

    # 2. Чертаем размерите (като в PDF)
    dim_color = "#D32F2F"
    
    dim_y = y0 + h_px + (kr * scale) + 40
    draw_dim(img, draw, x0, dim_y, x0+w_px, dim_y, f"{int(w)}", f_dim, dim_color)
    
    d_sx, d_sy = x0 + w_px + 20, y0 + h_px
    d_ex, d_ey = x0 + w_px + dx + 20, y0 + h_px - dy
    draw_dim(img, draw, d_sx, d_sy, d_ex, d_ey, f"{int(d)}", f_dim, dim_color)
    
    dim_x_left = x0 - 40
    draw_dim(img, draw, dim_x_left, y0, dim_x_left, y0+h_px, f"{int(box_h)}", f_dim, dim_color, rotate=True)

    if kr > 0:
        kr_px = kr * scale
        draw.rectangle([x0+w_px*0.1, y0+h_px, x0+w_px*0.1+t*2, y0+h_px+kr_px], fill="#333333")
        draw.rectangle([x0+w_px*0.9-t*2, y0+h_px, x0+w_px*0.9, y0+h_px+kr_px], fill="#333333")
        draw_dim(img, draw, dim_x_left, y0+h_px, dim_x_left, y0+h_px+kr_px, f"{int(kr)}", f_dim, dim_color, rotate=True)

    # 3. Чертаем лица, фурни и чекмеджета
    num_ch = int(meta.get("num_ch", 0))
    vr_cnt = int(meta.get("vr_cnt", 0))
    lower_door_h = float(meta.get("lower_door_h", 718))
    appliances_type = meta.get("appliances_type", "Без уреди")
    
    if "фурна" in tip.lower():
        sy = y0 + h_px - t - (157 * scale)
        draw.rectangle([x0+dx+t, sy-t/2-dy, x0+w_px-t+dx, sy+t/2-dy], outline=c_shelf, width=2)
        draw.rectangle([x0+t, sy-t/2, x0+w_px-t, sy+t/2], outline=c_shelf, width=2)
        draw.rectangle([x0+t, y0+t, x0+w_px-t, sy-t/2], fill="#3a3a3a")
        draw.rectangle([x0, sy+t/2, x0+w_px, y0+h_px], outline=c_front, width=3)
        dim_x_dr = x0 - 80
        draw_dim(img, draw, dim_x_dr, sy+t/2, dim_x_dr, y0+h_px, "157", f_dim, dim_color, rotate=True)
        draw.line([(x0, sy+t/2), (dim_x_dr, sy+t/2)], fill="#bbbbbb", width=1)
        draw.line([(x0, y0+h_px), (dim_x_dr, y0+h_px)], fill="#bbbbbb", width=1)
        
    elif "чекмеджета" in tip.lower() or num_ch > 0:
        nc = num_ch if num_ch > 0 else 3
        ch_h = h_px / nc
        for i in range(nc):
            draw.rectangle([x0, y0+i*ch_h, x0+w_px, y0+(i+1)*ch_h], outline=c_front, width=3)
            draw.line([(x0+w_px/2-15, y0+i*ch_h+ch_h/2), (x0+w_px/2+15, y0+i*ch_h+ch_h/2)], fill="#888888", width=3)
            dim_x_dr = x0 - 80
            draw_dim(img, draw, dim_x_dr, y0+i*ch_h, dim_x_dr, y0+(i+1)*ch_h, f"{int(box_h/nc)}", f_dim, dim_color, rotate=True)
            draw.line([(x0, y0+i*ch_h), (dim_x_dr, y0+i*ch_h)], fill="#bbbbbb", width=1)
        draw.line([(x0, y0+h_px), (x0-80, y0+h_px)], fill="#bbbbbb", width=1)
        
    elif is_col and appliances_type != "Без уреди":
        ld_h_px = lower_door_h * scale
        f_h_px = 595 * scale
        draw.rectangle([x0, y0+h_px-ld_h_px, x0+w_px, y0+h_px], outline=c_front, width=3)
        draw.rectangle([x0+t, y0+h_px-ld_h_px-f_h_px, x0+w_px-t, y0+h_px-ld_h_px], fill="#3a3a3a")
        draw.rectangle([x0, y0, x0+w_px, y0+h_px-ld_h_px-f_h_px], outline=c_front, width=3)
        dim_x_dr = x0 - 80
        draw_dim(img, draw, dim_x_dr, y0+h_px-ld_h_px, dim_x_dr, y0+h_px, f"{int(lower_door_h)}", f_dim, dim_color, rotate=True)
        draw.line([(x0, y0+h_px-ld_h_px), (dim_x_dr, y0+h_px-ld_h_px)], fill="#bbbbbb", width=1)
        
    elif vr_cnt > 0:
        vr_w = w_px / vr_cnt
        for i in range(vr_cnt):
            draw.rectangle([x0+i*vr_w, y0, x0+(i+1)*vr_w, y0+h_px], outline=c_front, width=3)
            hx = x0 + i*vr_w + 15 if i == 0 else x0 + (i+1)*vr_w - 15
            hy = y0 + h_px/2 if not is_upper else y0 + h_px*0.8
            draw.ellipse([hx-2, hy-2, hx+2, hy+2], fill="#888888")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

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
col1, col2 = st.columns([1, 4])

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
                "Шкаф Колона": "🏢", 
                "Шкаф с меж. стр.": "🚪",  
                
                "ДОБАВИ ДЕТАЙЛ": "🧩"
            }

        tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
        name = st.text_input("Име/№ на модула", value=tip)
        
        # ---- НОВО: ДОБАВЕНО ИЗБИРАНЕ НА ПОСОКА НА ФЛАДЕРА ----
        st.markdown("---")
        flader_posoka = st.radio("🔄 Посока на фладера (за лица и чекмеджета):", ["Вертикален", "Хоризонтален"], horizontal=True)
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
        
        if tip == "Дублираща страница долен":
            h = st.number_input("Височина (H) мм", value=860)
            d = st.number_input("Дълбочина (D) мм", value=580)
            w = deb
        elif tip == "Трети ред (Надстройка)":
            w = st.number_input("Ширина (W) на корпуса (мм)", value=600, key="w_tret")
            h = st.number_input("Височина (H) в мм", value=350, key="h_tret")
            d = st.number_input("Дълбочина (D) в мм", value=500, key="d_tret")
            vrati_broi = st.radio("Брой врати:", [1, 2], index=0, horizontal=True, key="vr_tret")
        elif tip == "ДОБАВИ ДЕТАЙЛ":
            custom_detail = st.text_input("Име на детайла (напр. Рафт, Цокъл, Страница)", value="Допълнителен детайл")
            
            colA, colB, colC = st.columns(3)
            custom_l = colA.number_input("Дължина (L) мм", value=600)
            custom_w = colB.number_input("Ширина (W) мм", value=300)
            custom_count = colC.number_input("Брой", value=1, min_value=1)
            
            colE, colF = st.columns(2)
            custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер", "Специфичен"])
            custom_flader = colF.radio("Спазва фладер?", ["Да", "Не"], index=0, horizontal=True)
            
            # Автоматично определяне на декора според материала на проекта
            if custom_mat_type == "Корпус": current_mat = mat_korpus
            elif custom_mat_type == "Лице": current_mat = mat_lice
            elif custom_mat_type == "Чекмеджета": current_mat = mat_chekm
            elif custom_mat_type == "Фазер": current_mat = mat_fazer
            else: current_mat = "Специфичен"

            st.markdown(f"##### 📏 Кантиране (Декор: **{current_mat}**)")
            
            # Вътрешна функция за кратко име на канта
            def get_edge_val(c_08, c_2, mat_name):
                if c_2: return f"{mat_name} 2"
                if c_08: return f"{mat_name} 0.8"
                return "Без"

            # 4 колони за 4-те страни на детайла
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.write("**Д1 (Горе)**")
                d1_08 = st.checkbox("0.8", key="d1_08")
                d1_2 = st.checkbox("2", key="d1_2")
            
            with c2:
                st.write("**Д2 (Долу)**")
                d2_08 = st.checkbox("0.8", key="d2_08")
                d2_2 = st.checkbox("2", key="d2_2")
                
            with c3:
                st.write("**Ш1 (Ляво)**")
                sh1_08 = st.checkbox("0.8", key="sh1_08")
                sh1_2 = st.checkbox("2", key="sh1_2")
                
            with c4:
                st.write("**Ш2 (Дясно)**")
                sh2_08 = st.checkbox("0.8", key="sh2_08")
                sh2_2 = st.checkbox("2", key="sh2_2")

            # Речник с резултатите (без "мм")
            custom_edges_dict = {
                "Д1": get_edge_val(d1_08, d1_2, current_mat),
                "Д2": get_edge_val(d2_08, d2_2, current_mat),
                "Ш1": get_edge_val(sh1_08, sh1_2, current_mat),
                "Ш2": get_edge_val(sh2_08, sh2_2, current_mat)
            }
            
            # Напасване на променливите за системата
            h, d, w = custom_l, custom_w, deb
            
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

        elif tip == "Шкаф с меж. стр.":
            st.info("Модул с вертикални делители")
            mod_podtip = st.radio("Избери вид шкаф:", ["Долен с делител", "Горен с делител"], horizontal=True)
            
            colA, colB, colC = st.columns(3)
            w = colA.number_input("Ширина (W) мм", value=1200)
            h_box = colB.number_input("Височина на корпуса (H) мм", value=760 if "Долен" in mod_podtip else 720)
            d = colC.number_input("Дълбочина (D) мм", value=520 if "Долен" in mod_podtip else 300)
            
            num_dividers = st.slider("Брой междинни страници (делители):", 1, 6, 1)
            num_sections = num_dividers + 1 
            
            st.markdown("##### 📚 Рафтове по секции (отляво надясно)")
            cols_shelves = st.columns(num_sections)
            section_shelves = []
            
            for i in range(num_sections):
                with cols_shelves[i]:
                    val = st.number_input(f"Секция {i+1}", min_value=0, value=2, key=f"shelf_sec_{i}")
                    section_shelves.append(val)
            
            # --- НОВО: Добавена е 0 и е оправен индексът ---
            vrati_broi = st.radio("Брой врати (0 = без врати):", [0, 1, 2, 3, 4, 5, 6, 7], index=num_sections if num_sections <= 7 else 0, horizontal=True)
            h = h_box + (kraka if "Долен" in mod_podtip else 0)

        elif tip == "Шкаф с чекмеджета":
            w = st.number_input("Ширина (W) мм", value=600, key="w_ch")
            h_box = st.number_input("Височина на корпуса без крака (мм)", value=760, key="h_box_ch")
            num_ch = st.slider("Брой чекмеджета:", 1, 6, 3, key="n_ch")
            
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

        elif "Глух" in tip:
            # Специфична ширина за Глух ъгъл
            w = st.number_input("Обща Ширина (W) мм", value=1000, key="w_std_gluh")
            
            # Добавяме кутийките за вратата и глухото чело
            col_g1, col_g2 = st.columns(2)
            w_vrata_input = col_g1.number_input("Ширина Врата (мм)", value=400, key="w_vr_g")
            w_gluha_input = col_g2.number_input("Ширина Глуха част (мм)", value=int(w - w_vrata_input - 20), key="w_gl_g")
            
            if "Горен" in tip:
                h = st.number_input("Височина (H) мм", value=720, key="h_up_gl")
                d = st.number_input("Дълбочина (D) мм", value=300, key="d_up_gl")
            else:
                h_box = st.number_input("Височина на корпуса без крака (мм)", value=760, key="h_box_gl")
                d = st.number_input("Дълбочина (D) мм", value=520, key="d_low_gl")
                h = h_box + kraka
            vrati_broi = 1

        else:
            # Тук влизат Стандартен долен, Фурна, Мивка, Бутилки
            if tip == "Шкаф Бутилки 15см":
                default_w = 150
            elif tip == "Шкаф за Фурна":
                default_w = 600
            else:
                default_w = 600
                
            w = st.number_input("Ширина (W) мм", value=default_w, key="w_std")
            
            if "Горен" in tip:
                h = st.number_input("Височина (H) мм", value=720, key="h_up")
                d = st.number_input("Дълбочина (D) мм", value=300, key="d_up")
                vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_up")
            else:
                h_box = st.number_input("Височина на корпуса без крака (мм)", value=760, key="h_box_low")
                d = st.number_input("Дълбочина (D) мм", value=(550 if tip == "Шкаф Мивка" else 520), key="d_low")
                h = h_box + kraka 
                
                if tip == "Шкаф за Фурна":
                    vrati_broi = 0
                    st.info("ℹ️ Този модул е с чекмедже (без врати).")
                else:
                    vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_low")

        st.markdown("---")
        temp_meta = {
            "Тип": tip, "W": w, "H": h, "D": d, 
            "vr_cnt": locals().get('vrati_broi', 0), 
            "num_dividers": locals().get('num_dividers', 0),
            "num_ch": locals().get('num_ch', 0),
            "lower_door_h": locals().get('lower_door_h', 0),
            "appliances_type": locals().get('appliances_type', "Без уреди"),
            "fl_posoka": flader_posoka
        }
        if st.button("➕ Добави към списъка"):
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

            # --- УМНА ФУНКЦИЯ ЗА ЗАВЪРТАНЕ НА ФЛАДЕРА ---
            def get_front_dims(h_front, w_front, has_flader=val_fl_lice):
                if has_flader in ["Не", "Няма"]:
                    return h_front, w_front, ""
                if flader_posoka == "Хоризонтален":
                    return w_front, h_front, "В БЛОК Х"
                return h_front, w_front, "В БЛОК"
            # --------------------------------------------

            if tip in ["Стандартен Долен", "Шкаф Мивка", "Шкаф Бутилки 15см", "Глух Ъгъл (Долен)", "Шкаф за Фурна", "Шкаф с чекмеджета", "Шкаф Колона"] or (tip == "Шкаф с меж. стр." and "Долен" in mod_podtip):
                hw_legs = 5 if w > 900 else 4
                new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": hw_legs})

            if tip in ["Стандартен Долен", "Шкаф Мивка", "Горен Шкаф", "Шкаф с меж. стр."]:
                # --- ТУК Е ЗАЩИТАТА ЗА ОБКОВА ---
                if vrati_broi > 0:
                    h_door_hw = h_vrata_standart if "Горен" not in tip else (h - fuga_obshto if 'vrati_orientacia' not in locals() or vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto)))
                    hw_hinges = calculate_hinges(h_door_hw) * vrati_broi
                    new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
                    new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})

            # ЛОГИКА ЗА РАЗКРОЙ 
            if tip == "Шкаф с меж. стр.":
                inner_w = (w - (2 + num_dividers) * deb) / num_sections
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
                
                # --- ТУК Е ЗАЩИТАТА ЗА ВРАТИТЕ И ДЕЛЕНЕТО НА НУЛА ---
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

            elif tip in ["Глух Ъгъл (Долен)", "Глух Ъгъл (Горен)"]:
                if "Долен" in tip:
                    lf, wf, nf = get_front_dims(h_vrata_standart, int(w_vrata_input - fuga_obshto))
                    lf_g, wf_g, nf_g = get_front_dims(h_vrata_standart, int(w_gluha_input - fuga_obshto))
                    new_items.extend([
                        add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                        add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), 
                        add_item(name, tip, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Врата", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                        add_item(name, tip, "Глуха част (Чело)", 1, lf_g, wf_g, "4 страни", mat_lice, val_fl_lice, nf_g),
                        add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                    ])
                else:
                    shelves_count = 2 if h > 800 else 1
                    lf, wf, nf = get_front_dims(h - fuga_obshto, int(w_vrata_input - fuga_obshto))
                    lf_g, wf_g, nf_g = get_front_dims(h - fuga_obshto, int(w_gluha_input - fuga_obshto))
                    new_items.extend([
                        add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Рафт", shelves_count, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus),
                        add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                        add_item(name, tip, "Врата", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                        add_item(name, tip, "Глуха част (Чело)", 1, lf_g, wf_g, "4 страни", mat_lice, val_fl_lice, nf_g)
                    ])

            elif tip == "Шкаф за Фурна":
                cargi_w = w - (2*deb) - 49
                duno_w = cargi_w + 12
                duno_l = runner_len - 13
                h_stranica_chekm = 157 - 45
                h_tsarga_furna = h_stranica_chekm - 15
                lf, wf, nf = get_front_dims(157, w - fuga_obshto)
                
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), 
                    add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    # ТУК БЕШЕ БЛЕНДАТА - ВЕЧЕ Е ИЗТРИТА
                    add_item(name, tip, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Чело чекмедже", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf), 
                    add_item(name, tip, "Царги чекм.", 2, cargi_w, h_tsarga_furna, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Страници чекм.", 2, runner_len - 10, h_stranica_chekm, "2д", mat_chekm, val_fl_chekm),
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
                    h_stranica_chekm = int(final_front_h - 45)
                    h_tsarga = h_stranica_chekm - 15
                    lf, wf, nf = get_front_dims(final_front_h, w - fuga_obshto)
                    
                    new_items.extend([
                        add_item(name, tip, f"Чело {idx+1}", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                        add_item(name, tip, f"Царги чекм. {idx+1}", 2, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, f"Страници чекм. {idx+1}", 2, runner_len - 10, h_stranica_chekm, "2д", mat_chekm, val_fl_chekm)
                    ])
                new_items.append(add_item(name, tip, "Дъно чекмедже", len(ch_heights), duno_l, duno_w, "Без", mat_fazer, "Няма"))

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
                        num_c = 2 if lower_type == "2 Чекмеджета" else 3
                        chelo_h = lower_door_h / num_c
                        h_stranica_chekm = int(chelo_h - 45)
                        h_tsarga = h_stranica_chekm - 15
                        for idx in range(num_c):
                            lf, wf, nf = get_front_dims(chelo_h - fuga_obshto, w - fuga_obshto)
                            new_items.extend([
                                add_item(name, tip, f"Чело долно {idx+1}", 1, lf, wf, "4 страни", mat_lice, val_fl_lice, nf),
                                add_item(name, tip, f"Царги чекм.", 2, w - (2*deb) - 49, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                                add_item(name, tip, f"Страници чекм.", 2, runner_len - 10, h_stranica_chekm, "2д", mat_chekm, val_fl_chekm)
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

            elif tip == "Гардероб чекм+врати":
                w_in = w - 2 * deb
                new_items.extend([
                    add_item(name, tip, "Страница лява", 1, h_korpus, d, "1д 2к", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница дясна", 1, h_korpus, d, "1д 2к", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Дъно", 1, w_in, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Таван", 1, w_in, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Твърд рафт", 1, w_in, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - 2, w - 2, "Без", mat_fazer, "Няма")
                ])
                h_front = int((h_drawers - 3 * fuga_obshto) / 2)
                lf_c, wf_c, nf_c = get_front_dims(h_front, w - 2 * fuga_obshto)
                new_items.append(add_item(name, tip, "Чело", 2, lf_c, wf_c, "4", mat_lice, val_fl_lice, nf_c))
                
                h_stranica_chekm = int(h_front - 45)
                h_tsarga = h_stranica_chekm - 15
                cargi_w = w_in - 49
                duno_w = cargi_w + 12
                duno_l = runner_len - 13
                
                new_items.extend([
                    add_item(name, tip, "Царги", 4, cargi_w, h_tsarga, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Страници чекм.", 4, runner_len - 10, h_stranica_chekm, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Дъно чекм.", 2, duno_l, duno_w, "Без", mat_fazer, "Няма")
                ])
                lf_u, wf_u, nf_u = get_front_dims(h_korpus - h_drawers - int(1.5 * fuga_obshto), int((w - 3 * fuga_obshto) / 2))
                new_items.append(add_item(name, tip, "Врата горна", 2, lf_u, wf_u, "4", mat_lice, val_fl_lice, nf_u))

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

            elif tip == "ДОБАВИ ДЕТАЙЛ":
                # Избор на материал според селекцията в менюто
                if custom_mat_type == "Лице": 
                    m_choice = mat_lice
                elif custom_mat_type == "Чекмеджета": 
                    m_choice = mat_chekm
                elif custom_mat_type == "Фазер": 
                    m_choice = mat_fazer
                elif custom_mat_type == "Специфичен": 
                    m_choice = "Специфичен"
                else: 
                    m_choice = mat_korpus
                
                f_choice = custom_flader 
                
                # Добавяне в списъка с новите кантове (custom_edges_dict)
                new_items.append(
                    add_item(
                        name, 
                        tip, 
                        custom_detail, 
                        int(custom_count), 
                        custom_l, 
                        custom_w, 
                        "Спец.", 
                        m_choice, 
                        f_choice, 
                        custom_edges=custom_edges_dict
                    )
                )

            elif tip == "Дублираща страница долен":
                lf, wf, _ = get_front_dims(h, d) 
                new_items.append(add_item(name, tip, "Дублираща страница", 1, lf, wf, "4 страни", mat_lice, val_fl_lice))

# --- Слагаме новите детайли НАЙ-ОТГОРЕ (пред старите) ---
            st.session_state.order_list = new_items + st.session_state.order_list
            st.session_state.hardware_list = new_hw + st.session_state.hardware_list
            st.success(f"Модул {name} е добавен!")
            st.rerun()

with col2:
    # --- ЗАГЛАВИЕ И 3D СКИЦА НА ЕДИН РЕД ---
    header_col, img_col = st.columns([4, 1.5]) # 4 части за заглавието, 1.5 за дясната зона
    
    with header_col:
        st.subheader("📋 Списък за разкрой (Редактируем)")
        
        # --- БУТОН ЗА ВРЪЩАНЕ НАЗАД ---
        if st.session_state.get("history"):
            c_undo, _ = st.columns([1.5, 4]) # Свиваме бутона, за да не е дълъг
            with c_undo:
                if st.button("↩️ Върни една стъпка назад"):
                    last_state = st.session_state.history.pop()
                    st.session_state.order_list = last_state["order"]
                    st.session_state.hardware_list = last_state["hw"]
                    st.session_state.modules_meta = last_state["meta"]
                    st.rerun()
                    
    with img_col:
        st.markdown("<div style='text-align: center; color: #008080; font-weight: bold; margin-bottom: 0px;'>👀 3D Изглед</div>", unsafe_allow_html=True)
        try:
            # ТРИКЪТ: Разделяме пространството на картинката -> 25% празно, 50% картинка, 25% празно
            _, inner_img_col, _ = st.columns([1, 2, 1])
            with inner_img_col:
                st.image(draw_3d_preview(temp_meta, kraka), use_container_width=True)
        except Exception:
            pass # Ако няма скица, остава празно
    
    # --- УПРАВЛЕНИЕ НА МОДУЛИ И ТАБЛИЦА ---
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
        
# --- ТАБЛИЦА (С визуални разделители между модулите) ---
        df = pd.DataFrame(st.session_state.order_list)
        
        cols_order = ["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[[c for c in cols_order if c in df.columns]]
        
        # --- ДОБАВЯНЕ НА ПРАЗНИ РЕДОВЕ (РАЗДЕЛИТЕЛИ) ---
        if not df.empty:
            df['№'] = df['№'].astype(str)
            records = df.to_dict('records')
            visual_records = []
            last_mod = None
            
            for row in records:
                current_mod = row['№']
                # Ако това не е първият ред и номерът на модула се е сменил
                if last_mod is not None and current_mod != last_mod:
                    # Създаваме "мним" разделителен ред
                    empty_row = {col: None for col in cols_order}
                    empty_row["№"] = "---" # Слагаме маркер, за да си го познаем после
                    visual_records.append(empty_row)
                
                visual_records.append(row)
                last_mod = current_mod
                
            display_df = pd.DataFrame(visual_records)
        else:
            display_df = df
        
        # Подаваме таблицата на екрана (с разделителите)
        edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, height=600, key="editor")
        
        # --- ФИЛТРИРАНЕ И ЗАПАЗВАНЕ ---
        # Важно: Махаме разделителните редове, преди да запазим реалните данни в паметта!
        clean_records = []
        for row in edited_df.to_dict('records'):
            # Запазваме само редовете, които НЕ са нашите разделители
            if str(row.get("№")) != "---":
                clean_records.append(row)
                
        st.session_state.order_list = clean_records
        
        # --- ОБКОВ И ЕКСПОРТ КЪМ ЕКСЕЛ (Връщаме ги, защото липсваха) ---
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

    # ЕТО ГО ЛИПСВАЩОТО ELSE, КОЕТО ОПРАВЯ ПРОБЛЕМА:
    else:
        st.info("Списъкът е празен. Добави първия си модул отляво!")
# --- 2. ГЕНЕРИРАНЕ НА ТЕХНИЧЕСКИ PDF ЧЕРТЕЖИ (СЕКЦИИ И ГАРДЕРОБИ) ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    import math
    import re
    import os
    import urllib.request
    import io
    from PIL import Image, ImageDraw, ImageFont
    
    font_path = "Roboto-Regular.ttf"
    font_path_it = "Roboto-Italic.ttf"
    
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    if not os.path.exists(font_path_it):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Italic.ttf", font_path_it)
        except: pass
        
    try: 
        f_title = ImageFont.truetype(font_path, 50)
        f_dim = ImageFont.truetype(font_path, 42) 
        f_tab_h = ImageFont.truetype(font_path, 36) 
        f_tab_r = ImageFont.truetype(font_path_it, 34) 
    except: 
        f_title = f_dim = f_tab_h = f_tab_r = ImageFont.load_default()

    def get_val(item, keys, default):
        for k in keys:
            if k in item and item[k] is not None and str(item[k]).strip() != "":
                return item[k]
        return default

    def draw_dim(img, draw, x1, y1, x2, y2, text, font, color, rotate=False):
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        dist = math.hypot(x2-x1, y2-y1)
        if dist < 1: return
        ux, uy = (x2-x1)/dist, (y2-y1)/dist
        
        txt_img_temp = Image.new('RGBA', (10, 10), (255,255,255,0))
        temp_draw = ImageDraw.Draw(txt_img_temp)
        bbox = temp_draw.textbbox((0,0), text, font=font)
        tw = bbox[2] - bbox[0]
        
        gap = (tw / 2) + 12 
        
        if dist > gap * 2:
            draw.line([(x1, y1), (mid_x - ux*gap, mid_y - uy*gap)], fill=color, width=3)
            draw.line([(mid_x + ux*gap, mid_y + uy*gap), (x2, y2)], fill=color, width=3)
        else:
            draw.line([(x1, y1), (x2, y2)], fill=color, width=3)
            
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

        m_num = get_val(mod, ['mod_num', '№', 'Номер'], '?')
        m_tip = get_val(mod, ['mod_tip', 'Модул', 'Вид', 'Тип'], 'Неизвестен Модул')
        
        try: w = max(float(get_val(mod, ['w', 'W', 'Ширина'], 600)), 60)
        except: w = 600
        try: h = max(float(get_val(mod, ['h_box', 'h', 'H', 'Височина'], 860)), 60)
        except: h = 860
        try: d = max(float(get_val(mod, ['d', 'D', 'Дълбочина'], 550)), 60)
        except: d = 550
        try: kr = int(kraka_height)
        except: kr = 0
        
        m_num_str = str(m_num).strip().lower()
        m_tip_str = str(m_tip).strip().lower()
        full_name_str = f"{m_num_str} {m_tip_str}"
        
        cabinet_count = sum(1 for m in modules_meta if str(get_val(m, ['mod_num', '№', 'Номер'], '?')).strip().lower() == m_num_str)
        if cabinet_count < 1: cabinet_count = 1
        
        parts_for_this_mod = []
        if order_list:
            seen = set()
            for p in order_list:
                p_num = str(p.get('mod_num', p.get('№', ''))).strip().lower()
                p_tip = str(p.get('mod_tip', p.get('Детайл', ''))).strip().lower()
                
                matches_num = (p_num == m_num_str and m_num_str not in ['', '?'])
                matches_name = (m_num_str in ['', '?'] and p_tip == m_tip_str)
                
                if matches_num or matches_name:
                    p_sig = f"{p.get('Детайл')}_{p.get('Дължина')}_{p.get('Ширина')}_{p.get('Плоскост')}"
                    if p_sig not in seen:
                        seen.add(p_sig)
                        parts_for_this_mod.append(p)
        
        # --- СКАНИРАНЕ ЗА ДЕЛИТЕЛИ И СЕКЦИИ ---
        has_divider = False
        num_dividers = int(get_val(mod, ['num_dividers'], 0))
        section_shelves = []
        
        if "делител" in m_tip_str or "меж." in m_num_str or "междинна" in m_tip_str:
            has_divider = True
            ss_raw = get_val(mod, ['section_shelves'], [])
            if isinstance(ss_raw, list): section_shelves = ss_raw
            elif isinstance(ss_raw, str):
                try: section_shelves = eval(ss_raw)
                except: pass

        fronts_with_names = []
        real_shelves = 0

        for p in parts_for_this_mod:
            d_name = str(p.get('Детайл', '')).lower()
            raw_qty = int(p.get('Бр', 1))
            qty_per_cab = max(1, round(raw_qty / cabinet_count))
            
            if 'чело' in d_name:
                try:
                    fh = min(float(p.get('Дължина', 0)), float(p.get('Ширина', 0)))
                    match = re.search(r'\d+', d_name)
                    sort_idx = int(match.group()) if match else 999
                    for _ in range(qty_per_cab):
                        fronts_with_names.append((sort_idx, fh))
                except: pass
                
            elif 'рафт' in d_name and 'твърд' not in d_name and 'тв.' not in d_name:
                real_shelves += qty_per_cab
                    
            if not has_divider and ('междинна' in d_name or 'делител' in d_name):
                has_divider = True
                
        if has_divider and num_dividers == 0:
            div_qty = sum(max(1, round(int(p.get('Бр', 1)) / cabinet_count)) for p in parts_for_this_mod if 'междинна' in str(p.get('Детайл', '')).lower() or 'делител' in str(p.get('Детайл', '')).lower())
            num_dividers = div_qty if div_qty > 0 else 1
            
        num_sections = num_dividers + 1

        if has_divider and not section_shelves:
            section_shelves = [2] * num_sections

        fronts_with_names.sort(key=lambda x: x[0])
        real_front_heights = [f[1] for f in fronts_with_names]
        real_drawers = len(real_front_heights)
        
        lower_type = str(mod.get('lower_type', '')).lower()
        if 'чекмедж' in lower_type:
            match = re.search(r'(\d+)', lower_type)
            num_drawers = int(match.group(1)) if match else 2
        elif 'врата' in lower_type:
            num_drawers = 0 
        else:
            match_dr = re.search(r'(\d+)\s*чекмедж', full_name_str)
            if match_dr: num_drawers = int(match_dr.group(1))
            elif "чекмедже" in full_name_str: num_drawers = real_drawers if real_drawers > 0 else 3
            else: num_drawers = 0

        # --- КЛЮЧОВА ПРОМЯНА: РАЗПОЗНАВАНЕ НА "ДОБАВИ ДЕТАЙЛ" ---
        is_detail = "детайл" in m_tip_str
        is_upper = "горен" in full_name_str or "горни" in full_name_str
        is_col = "колона" in full_name_str
        is_lower = "долен" in full_name_str or "долни" in full_name_str

        if is_detail:
            # Ако е детайл, анулираме крака, чекмеджета и делители
            is_lower = False
            is_upper = False
            is_col = False
            num_drawers = 0
            has_divider = False
            kr = 0
            
            # Завъртаме размерите: Дължината (h) става Ширина на чертежа, Ширината (d) става Височина
            draw_w = h 
            draw_h = d 
            draw_d = w 
            box_h = d
        else:
            if not is_upper and not is_lower and not is_col and num_drawers == 0:
                is_lower = True 

            if is_upper:
                kr = 0
                box_h = h
            else:
                box_h = h - kr if h > kr and h >= 800 else h
                
            draw_w = w
            draw_h = box_h
            draw_d = d

        bottom_under_sides = is_lower or is_col or num_drawers > 0

        # --- ЗАГЛАВИЯ И ТЕКСТ ---
        title = f"Детайл [{m_num}] | {m_tip}" if is_detail else f"Шкаф [{m_num}] | {m_tip}"
        draw.text((150, 100), title, fill="black", font=f_title)
        draw.line([(150, 170), (2330, 170)], fill="black", width=5)
        
        if is_detail:
            draw.text((150, 200), f"Параметри: Дължина {int(h)} мм | Ширина {int(d)} мм | Дебелина {int(w)} мм", fill="#555555", font=f_dim)
        else:
            actual_total_h = box_h + kr
            draw.text((150, 200), f"Габаритни размери: Ширина {int(w)} мм | Височина {int(actual_total_h)} мм | Дълбочина {int(d)} мм", fill="#555555", font=f_dim)

        # --- ИЗЧИСЛЯВАНЕ НА МАЩАБА И КООРДИНАТИТЕ ---
        center_x, center_y = 1240, 1250
        max_dim = max(draw_w, draw_h, draw_d)
        scale = 1000 / max_dim if max_dim > 0 else 1
        
        w_px = draw_w * scale
        h_px = draw_h * scale
        d_px = draw_d * scale * 0.5  
        
        dx = d_px * 0.707
        dy = d_px * 0.707

        x0 = center_x - (w_px + dx) / 2
        y0 = center_y - (h_px + (kr*scale if not is_detail else 0) - dy) / 2
        
        c_front = "black"
        c_back = "#aaaaaa"
        c_shelf = "#3c8dbc" 
        t_mm = 18
        t = t_mm * scale 
        
        boards = []
        if is_detail:
            # Чертае само една единствена плоскост (детайла)
            boards.append((x0, y0, w_px, h_px))
        else:
            # Сглобява корпус за шкафове
            if bottom_under_sides:
                boards.append( (x0, y0, t, h_px - t) ) 
                boards.append( (x0 + w_px - t, y0, t, h_px - t) ) 
                boards.append( (x0 + t, y0, w_px - 2*t, t) ) 
                boards.append( (x0, y0 + h_px - t, w_px, t) ) 
            else:
                boards.append( (x0, y0, t, h_px) ) 
                boards.append( (x0 + w_px - t, y0, t, h_px) ) 
                boards.append( (x0 + t, y0, w_px - 2*t, t) ) 
                boards.append( (x0 + t, y0 + h_px - t, w_px - 2*t, t) ) 
                
            if has_divider:
                inner_w_px = (w_px - (2 + num_dividers) * t) / num_sections
                for i in range(1, num_dividers + 1):
                    div_x = x0 + t + i * inner_w_px + (i - 1) * t
                    div_y = y0 + t
                    div_h = h_px - 2*t
                    boards.append( (div_x, div_y, t, div_h) )

        # --- 3D РЕНДЕРИРАНЕ НА БЛОКОВЕТЕ ---
        for bx, by, bw, bh in boards:
            draw.rectangle([bx+dx, by-dy, bx+bw+dx, by+bh-dy], outline=c_back, width=2)
            draw.line([(bx, by), (bx+dx, by-dy)], fill=c_back, width=2)
            draw.line([(bx+bw, by), (bx+bw+dx, by-dy)], fill=c_back, width=2)
            draw.line([(bx, by+bh), (bx+dx, by+bh-dy)], fill=c_back, width=2)
            draw.line([(bx+bw, by+bh), (bx+bw+dx, by+bh-dy)], fill=c_back, width=2)

        draw.line([(x0, y0), (x0+dx, y0-dy)], fill=c_front, width=3)
        draw.line([(x0+w_px, y0), (x0+w_px+dx, y0-dy)], fill=c_front, width=3)
        draw.line([(x0+w_px, y0+h_px), (x0+w_px+dx, y0+h_px-dy)], fill=c_front, width=3)

        for bx, by, bw, bh in boards:
            draw.rectangle([bx, by, bx+bw, by+bh], outline=c_front, width=3)
            
        dim_color = "#D32F2F"
        shelf_color_dim = "#2196F3"
        
        drawer_section_h = 0
        if num_drawers > 0:
            if is_col: drawer_section_h = 760 
            else: drawer_section_h = box_h
                
        if real_front_heights and sum(real_front_heights) > drawer_section_h + 50:
            real_front_heights = []
            
        # --- ПОДГОТОВКА НА РАФТОВЕТЕ ПО СЕКЦИИ ---
        if is_detail:
            columns_data = [] # Предотвратява чертането на рафтове
        elif has_divider:
            columns_data = []
            inner_w_px = (w_px - (2 + num_dividers) * t) / num_sections
            for s in range(num_sections):
                ns = int(section_shelves[s]) if s < len(section_shelves) else 0
                s_left = x0 + t + s * (inner_w_px + t)
                dim_side = 'left' if s < num_sections / 2 else 'right'
                dim_offset = s if dim_side == 'left' else (num_sections - 1 - s)
                columns_data.append({
                    's_left': s_left, 's_width': inner_w_px, 'ns': ns, 
                    'dim_side': dim_side, 'dim_offset': dim_offset
                })
        else:
            ns = real_shelves if parts_for_this_mod else -1 
            columns_data = [{'s_left': x0 + t, 's_width': w_px - 2*t, 'ns': ns, 'dim_side': 'right', 'dim_offset': 0}]

        # --- ЧЕРТАЕНЕ НА РАФТОВЕТЕ И ОРАЗМЕРЯВАНЕ ---
        for col_idx, col in enumerate(columns_data):
            ns = col['ns']
            col_shelves = []
            
            if is_col and not has_divider and num_drawers == 0:
                c1 = 760 - t_mm - (t_mm / 2) 
                c2 = c1 + 609                
                y_start = y0 + h_px - t
                col_shelves.append((y_start - (c1 * scale), c1))
                col_shelves.append((y_start - (c2 * scale), c2))
                if box_h > 1800:
                    c3 = c2 + 390            
                    col_shelves.append((y_start - (c3 * scale), c3))
            else:
                space_for_shelves = box_h - drawer_section_h
                if space_for_shelves > 200:
                    if ns == -1: 
                        if space_for_shelves <= 500: ns = 0
                        elif space_for_shelves <= 1000: ns = 1
                        elif space_for_shelves <= 1600: ns = 2
                        else: ns = 3
                    
                    if ns > 0:
                        gap = (space_for_shelves - ns * t_mm) / (ns + 1)
                        for i in range(1, ns + 1):
                            h_from_bottom = drawer_section_h + i * gap + (i - 1) * t_mm + (t_mm / 2)
                            if bottom_under_sides:
                                dim_val = h_from_bottom 
                                y_start = y0 + h_px - t
                            else:
                                dim_val = h_from_bottom + t_mm 
                                y_start = y0 + h_px
                                
                            sy = y_start - (dim_val * scale)
                            col_shelves.append((sy, dim_val))

            for idx, (sy, dim_val) in enumerate(col_shelves):
                s_left = col['s_left']
                s_width = col['s_width']
                
                draw.rectangle([s_left+dx, sy-t/2-dy, s_left+s_width+dx, sy+t/2-dy], outline=c_shelf, width=2)
                draw.line([(s_left, sy-t/2), (s_left+dx, sy-t/2-dy)], fill=c_shelf, width=2)
                draw.line([(s_left+s_width, sy-t/2), (s_left+s_width+dx, sy-t/2-dy)], fill=c_shelf, width=2)
                draw.line([(s_left, sy+t/2), (s_left+dx, sy+t/2-dy)], fill=c_shelf, width=2)
                draw.line([(s_left+s_width, sy+t/2), (s_left+s_width+dx, sy+t/2-dy)], fill=c_shelf, width=2)
                draw.rectangle([s_left, sy-t/2, s_left+s_width, sy+t/2], outline=c_shelf, width=2)
                
                y_baseline = (y0 + h_px - t) if bottom_under_sides else (y0 + h_px)
                
                if col['dim_side'] == 'right':
                    dim_x = x0 + w_px + 80 + (col['dim_offset'] * 120) + ((idx+1) * 65)
                    draw_dim(img, draw, dim_x, y_baseline, dim_x, sy, f"{int(dim_val)}", f_dim, shelf_color_dim, rotate=True)
                    draw.line([(x0+w_px, sy), (dim_x, sy)], fill="#bbbbbb", width=2)
                    draw.line([(x0+w_px, y_baseline), (dim_x, y_baseline)], fill="#bbbbbb", width=2)
                else:
                    dim_x = x0 - 200 - (col['dim_offset'] * 120) - ((idx+1) * 65)
                    draw_dim(img, draw, dim_x, y_baseline, dim_x, sy, f"{int(dim_val)}", f_dim, shelf_color_dim, rotate=True)
                    draw.line([(x0, sy), (dim_x, sy)], fill="#bbbbbb", width=2)
                    draw.line([(x0, y_baseline), (dim_x, y_baseline)], fill="#bbbbbb", width=2)

        # --- ЧЕРТАЕНЕ НА ЧЕКМЕДЖЕТА ---
        if num_drawers > 0:
            curr_y = y0 if not is_col else y0 + h_px - (drawer_section_h * scale)
            if is_col: draw.line([(x0, curr_y), (x0+w_px, curr_y)], fill=c_front, width=4) 
                
            if real_front_heights:
                total_fh = sum(real_front_heights)
                scale_f = drawer_section_h / total_fh if total_fh > 0 else 1
                for idx, fh in enumerate(real_front_heights):
                    fh_visual_px = fh * scale_f * scale 
                    if idx > 0: draw.line([(x0, curr_y), (x0+w_px, curr_y)], fill=c_front, width=4)
                    dim_x_dr = x0 - 140
                    draw_dim(img, draw, dim_x_dr, curr_y, dim_x_dr, curr_y+fh_visual_px, f"{int(fh)}", f_dim, dim_color, rotate=True)
                    curr_y += fh_visual_px
            else:
                if num_drawers == 1: fronts = [drawer_section_h]
                elif num_drawers == 2: fronts = [drawer_section_h / 2] * 2
                elif num_drawers == 3:
                    h1 = 160 if drawer_section_h > 500 else drawer_section_h * 0.25
                    h2 = (drawer_section_h - h1) / 2
                    fronts = [h1, h2, h2]
                elif num_drawers == 4:
                    h1 = 160 if drawer_section_h > 600 else drawer_section_h * 0.2
                    h2 = (drawer_section_h - h1) / 3
                    fronts = [h1, h2, h2, h2]
                else: fronts = [drawer_section_h / num_drawers] * num_drawers
                    
                for idx, fh in enumerate(fronts):
                    fh_px = fh * scale
                    if idx > 0: draw.line([(x0, curr_y), (x0+w_px, curr_y)], fill=c_front, width=4)
                    dim_x_dr = x0 - 140
                    draw_dim(img, draw, dim_x_dr, curr_y, dim_x_dr, curr_y+fh_px, f"{int(fh)}", f_dim, dim_color, rotate=True)
                    curr_y += fh_px

        # --- ОСНОВНИ ГАБАРИТНИ РАЗМЕРИ ---
        dim_y = y0 + h_px + (kr * scale) + 80
        d_sx, d_sy = x0 + w_px + 40, y0 + h_px
        d_ex, d_ey = x0 + w_px + dx + 40, y0 + h_px - dy
        dim_x_left = x0 - 80

        if is_detail:
            # Чертае размерите специфично за плосък детайл
            draw_dim(img, draw, x0, dim_y, x0+w_px, dim_y, f"{int(h)}", f_dim, dim_color)
            draw_dim(img, draw, d_sx, d_sy, d_ex, d_ey, f"{int(w)}", f_dim, dim_color)
            draw_dim(img, draw, dim_x_left, y0, dim_x_left, y0+h_px, f"{int(d)}", f_dim, dim_color, rotate=True)
        else:
            # Стандартни размери за шкаф
            draw_dim(img, draw, x0, dim_y, x0+w_px, dim_y, f"{int(w)}", f_dim, dim_color)
            draw_dim(img, draw, d_sx, d_sy, d_ex, d_ey, f"{int(d)}", f_dim, dim_color)
            draw_dim(img, draw, dim_x_left, y0, dim_x_left, y0+h_px, f"{int(box_h)}", f_dim, dim_color, rotate=True)
            
            if kr > 0:
                kr_px = kr * scale
                draw.rectangle([x0+40, y0+h_px, x0+80, y0+h_px+kr_px], fill="#333333")
                draw.rectangle([x0+w_px-80, y0+h_px, x0+w_px-40, y0+h_px+kr_px], fill="#333333")
                draw.line([(x0-150, y0+h_px+kr_px), (x0+w_px+150, y0+h_px+kr_px)], fill="#999999", width=2)
                draw_dim(img, draw, dim_x_left, y0+h_px, dim_x_left, y0+h_px+kr_px, f"{int(kr)}", f_dim, dim_color, rotate=True)

        # --- ТАБЛИЦА С ДЕТАЙЛИ ---
        tab_y = 2350
        draw.text((150, tab_y - 60), f"Списък с детайли:", fill="black", font=f_title)
        
        draw.line([(150, tab_y), (2330, tab_y)], fill="black", width=4)
        draw.text((160, tab_y + 10), "Детайл", font=f_tab_h, fill="black")
        draw.text((900, tab_y + 10), "Размер (L x W)", font=f_tab_h, fill="black")
        draw.text((1300, tab_y + 10), "Бр.", font=f_tab_h, fill="black")
        draw.text((1450, tab_y + 10), "Кантове", font=f_tab_h, fill="black")
        draw.text((1900, tab_y + 10), "Материал", font=f_tab_h, fill="black")
        tab_y += 60
        draw.line([(150, tab_y), (2330, tab_y)], fill="black", width=4)
        
        if not parts_for_this_mod:
            draw.text((160, tab_y + 20), "Няма генерирани детайли в разкроя за този модул.", font=f_tab_r, fill="#777777")
        else:
            for p in parts_for_this_mod:
                d_name = str(p.get('Детайл', ''))[:35]
                try: d_dim = f"{int(float(p.get('Дължина', 0)))} x {int(float(p.get('Ширина', 0)))}"
                except: d_dim = "-"
                
                raw_qty = int(p.get('Бр', 1))
                display_qty = str(max(1, round(raw_qty / cabinet_count)))
                
                edges = []
                for k, lbl in [('Д1', 'Д1'), ('Д2', 'Д2'), ('Ш1', 'Ш1'), ('Ш2', 'Ш2')]:
                    val = str(p.get(k, '')).strip()
                    if val and val.lower() not in ['няма', '0', 'none', 'false', '']:
                        edges.append(f"{lbl}:{val}")
                d_edge = " ".join(edges) if edges else "Няма"
                d_mat = str(p.get('Плоскост', ''))[:20]
                
                draw.text((160, tab_y + 15), d_name, font=f_tab_r, fill="#333333")
                draw.text((900, tab_y + 15), d_dim, font=f_tab_r, fill="#333333")
                draw.text((1300, tab_y + 15), display_qty, font=f_tab_r, fill="#333333")
                draw.text((1450, tab_y + 15), d_edge, font=f_tab_r, fill="#333333")
                draw.text((1900, tab_y + 15), d_mat, font=f_tab_r, fill="#333333")
                
                tab_y += 60
                draw.line([(150, tab_y), (2330, tab_y)], fill="#dddddd", width=2)
                
                if tab_y > 3350:
                    draw.text((160, tab_y + 10), "... (Списъкът продължава на следваща страница)", font=f_tab_r, fill="#777777")
                    break

        pages.append(img)

    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_bytes.getvalue()
    return None 

# --- ПОМОЩНА ФУНКЦИЯ ЗА ЧЕРТАНЕ НА ЛИНИИТЕ НА КАНТА ВЪРХУ ЕТИКЕТА ---
def draw_edge_marking(draw, x, y, w, h, side, text, font):
    if not text or str(text).strip() == "" or str(text).strip().lower() in ["без", "none", "няма"]: return
    
    display_text = str(text).strip()
    
    line_w = 4
    inset_x = 20  # Скъсява линията в краищата
    inset_y = 27  # ОТДАЛЕЧЕНО: Премества линията на около 1 мм навътре от ръба
    
    # Вземаме размерите на текста, за да прекъснем линията
    try:
        bbox = draw.textbbox((0, 0), display_text, font=font)
        tw = bbox[2] - bbox[0]
    except:
        tw = len(display_text) * 15 
        
    gap = (tw / 2) + 15  # Малко повече празно пространство около самата цифра
    
    if side == 'top':
        cx, cy = x + w / 2, y + inset_y
        if cx - gap > x + inset_x: draw.line([x + inset_x, cy, cx - gap, cy], fill="black", width=line_w)
        if cx + gap < x + w - inset_x: draw.line([cx + gap, cy, x + w - inset_x, cy], fill="black", width=line_w)
        draw.text((cx, cy), display_text, fill="black", font=font, anchor="mm")
        
    elif side == 'bottom':
        cx, cy = x + w / 2, y + h - inset_y
        if cx - gap > x + inset_x: draw.line([x + inset_x, cy, cx - gap, cy], fill="black", width=line_w)
        if cx + gap < x + w - inset_x: draw.line([cx + gap, cy, x + w - inset_x, cy], fill="black", width=line_w)
        draw.text((cx, cy), display_text, fill="black", font=font, anchor="mm")
        
    elif side == 'left':
        cx, cy = x + inset_y, y + h / 2
        if cy - gap > y + inset_x: draw.line([cx, y + inset_x, cx, cy - gap], fill="black", width=line_w)
        if cy + gap < y + h - inset_x: draw.line([cx, cy + gap, cx, y + h - inset_x], fill="black", width=line_w)
        draw.text((cx, cy), display_text, fill="black", font=font, anchor="mm")
        
    elif side == 'right':
        cx, cy = x + w - inset_y, y + h / 2
        if cy - gap > y + inset_x: draw.line([cx, y + inset_x, cx, cy - gap], fill="black", width=line_w)
        if cy + gap < y + h - inset_x: draw.line([cx, cy + gap, cx, y + h - inset_x], fill="black", width=line_w)
        draw.text((cx, cy), display_text, fill="black", font=font, anchor="mm")
        
# --- ОПТИМИЗАЦИЯ НА РАЗКРОЯ (ИСТИНСКИ НЕСТИНГ С БЛОКОВЕ 1, 2, 3...) ---
def get_optimized_boards(list_for_cutting):
    kerf, trim, board_l, board_w = 8, 8, 2800, 2070
    use_l, use_w = board_l - 2*trim, board_w - 2*trim
    
    local_blocks = {} # local_blocks[mat][mod_num_door/drawer] = [детайли]
    global_blocks = {} # global_blocks[mat][group_name][row_num] = [детайли]
    standard_parts_by_mat = {}
    
    import re
    for item in list_for_cutting:
        mat = item.get('Плоскост', 'Неизвестен')
        mod_num = str(item.get('№', '0'))
        note = str(item.get('Забележка', '')).strip().upper()
        is_door = "ВРАТА" in str(item.get('Детайл', '')).upper()
        
        if mat not in standard_parts_by_mat: standard_parts_by_mat[mat] = []
        if mat not in local_blocks: local_blocks[mat] = {}
        if mat not in global_blocks: global_blocks[mat] = {}
        
        is_local_block = (note == "В БЛОК")
        global_match = None
        if not is_local_block:
            # Търси "БЛОК" (и думи след него), последвано от число (1, 2, 3...)
            global_match = re.search(r'(БЛОК[^\d]*)(\d+)', note)
            
        try:
            for _ in range(int(item.get('Бр', 1))):
                flader_val = str(item.get('Фладер', 'Да')).strip().lower()
                can_rotate = (flader_val == "не" or flader_val == "няма")
                
                part_dict = item.copy()
                part_dict.update({
                    'name': f"{item.get('№', '')} {get_abbrev(item.get('Детайл', ''))}", 
                    'l': float(item.get('Дължина', 0)), 'w': float(item.get('Ширина', 0)),
                    'd1': str(item.get('Д1', '')).strip(), 'd2': str(item.get('Д2', '')).strip(),
                    'sh1': str(item.get('Ш1', '')).strip(), 'sh2': str(item.get('Ш2', '')).strip(),
                    'can_rotate': can_rotate,
                    'mod_tip': item.get('mod_tip', item.get('Детайл', 'Детайл'))
                })
                
                if is_local_block:
                    b_key = f"{mod_num}_door" if is_door else f"{mod_num}_drawer"
                    if b_key not in local_blocks[mat]: local_blocks[mat][b_key] = []
                    local_blocks[mat][b_key].append(part_dict)
                    
                elif global_match:
                    g_name = global_match.group(1).strip() # Напр. "БЛОК" или "БЛОК ОСТРОВ"
                    row_num = int(global_match.group(2))
                    
                    if g_name not in global_blocks[mat]: global_blocks[mat][g_name] = {}
                    if row_num not in global_blocks[mat][g_name]: global_blocks[mat][g_name][row_num] = []
                    global_blocks[mat][g_name][row_num].append(part_dict)
                    
                else:
                    standard_parts_by_mat[mat].append(part_dict)
        except: pass

    boards_per_material = {}
    all_materials = set(list(standard_parts_by_mat.keys()) + list(local_blocks.keys()) + list(global_blocks.keys()))
    
    for mat_name in all_materials:
        std_parts = standard_parts_by_mat.get(mat_name, [])
        l_blocks = local_blocks.get(mat_name, {})
        g_blocks = global_blocks.get(mat_name, {})
        
        all_mat_parts = list(std_parts)
        for b_parts in l_blocks.values(): all_mat_parts.extend(b_parts)
        for grp in g_blocks.values():
            for row_parts in grp.values():
                all_mat_parts.extend(row_parts)
                
        if not all_mat_parts: continue
        
        mat_can_rotate = all(p['can_rotate'] for p in all_mat_parts)
        
        packer = newPacker(
            mode=PackingMode.Offline, 
            bin_algo=PackingBin.BFF, 
            pack_algo=GuillotineBssfMaxas, 
            rotation=mat_can_rotate
        )
        
        items_to_pack = []
        pack_idx = 0
        
        # 1. Стандартни детайли
        for p in std_parts:
            items_to_pack.append({'type': 'single', 'part': p})
            packer.add_rect(int(p['l'] + kerf), int(p['w'] + kerf), rid=pack_idx)
            pack_idx += 1
            
        # 2. Локални Блокове ("В БЛОК" - за конкретен шкаф)
        for b_key, b_parts in l_blocks.items():
            if not b_parts: continue
            b_parts.sort(key=lambda x: x['name']) # Сортиране по име (напр. Чело 1, Чело 2)
            
            is_door_block = "door" in b_key
            curr_offset = 0
            
            if is_door_block: # Вратите се редят една до друга (по ширина)
                block_w = sum(p['w'] for p in b_parts) + (len(b_parts) - 1) * kerf
                block_l = max(p['l'] for p in b_parts)
                for p in b_parts:
                    p['rel_x'] = 0
                    p['rel_y'] = curr_offset
                    curr_offset += p['w'] + kerf
            else: # Чекмеджетата се редят едно над друго (по дължина)
                block_w = max(p['w'] for p in b_parts)
                block_l = sum(p['l'] for p in b_parts) + (len(b_parts) - 1) * kerf
                for p in b_parts:
                    p['rel_x'] = curr_offset
                    p['rel_y'] = 0
                    curr_offset += p['l'] + kerf
                    
            items_to_pack.append({
                'type': 'super_block',
                'parts': b_parts,
                'l': block_l,
                'w': block_w
            })
            packer.add_rect(int(block_l + kerf), int(block_w + kerf), rid=pack_idx)
            pack_idx += 1
            
        # 3. Глобални Блокове ("БЛОК 1", "БЛОК 2" - през различни шкафове)
        for g_name, g_groups in g_blocks.items():
            if not g_groups: continue
            
            sorted_nums = sorted(list(g_groups.keys()))
            packed_parts_info = []
            
            current_l_offset = 0
            max_super_w = 0
            
            for num in sorted_nums:
                sub_parts = g_groups[num]
                current_w_offset = 0
                max_sub_l = 0
                
                for p in sub_parts:
                    p['rel_x'] = current_l_offset
                    p['rel_y'] = current_w_offset
                    packed_parts_info.append(p)
                    
                    current_w_offset += p['w'] + kerf
                    if p['l'] > max_sub_l:
                        max_sub_l = p['l']
                        
                sub_total_w = current_w_offset - kerf
                if sub_total_w > max_super_w:
                    max_super_w = sub_total_w
                    
                current_l_offset += max_sub_l + kerf
                
            super_l = current_l_offset - kerf
            super_w = max_super_w
            
            items_to_pack.append({
                'type': 'super_block',
                'parts': packed_parts_info,
                'l': super_l,
                'w': super_w
            })
            packer.add_rect(int(super_l + kerf), int(super_w + kerf), rid=pack_idx)
            pack_idx += 1
            
        for _ in range(20): packer.add_bin(int(use_l), int(use_w))
        packer.pack()
        
        # 4. Разпакетиране
        all_boards = []
        for abin in packer:
            current_board_parts = []
            for rect in abin:
                idx = rect.rid
                pack_item = items_to_pack[idx]
                res_x, res_y, res_w, res_h = rect.x, rect.y, rect.width, rect.height
                
                if pack_item['type'] == 'single':
                    orig = pack_item['part']
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
                    
                elif pack_item['type'] == 'super_block':
                    super_l = pack_item['l']
                    super_w = pack_item['w']
                    
                    is_rotated = False
                    if abs((res_w - kerf) - super_w) < 2:
                        is_rotated = True
                        
                    for p in pack_item['parts']:
                        p_copy = p.copy()
                        if is_rotated:
                            p_copy['x'] = res_x + p['rel_y']
                            p_copy['y'] = res_y + p['rel_x']
                            p_copy['l'] = p['w']
                            p_copy['w'] = p['l']
                            p_copy['d1'], p_copy['d2'], p_copy['sh1'], p_copy['sh2'] = p['sh1'], p['sh2'], p['d1'], p['d2']
                        else:
                            p_copy['x'] = res_x + p['rel_x']
                            p_copy['y'] = res_y + p['rel_y']
                            p_copy['l'] = p['l']
                            p_copy['w'] = p['w']
                            
                        current_board_parts.append(p_copy)

            if current_board_parts:
                all_boards.append(current_board_parts)
        
        boards_per_material[mat_name] = all_boards
        
    return boards_per_material, board_l, board_w, trim

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

# --- 3. ГЕНЕРИРАНЕ НА ЕТИКЕТИ С 44 БРОЯ НА А4 ---
def generate_labels_pdf(boards_per_mat):
    import os
    import urllib.request
    import io
    from PIL import Image, ImageDraw, ImageFont

    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try:
        font_small = ImageFont.truetype(font_path, 20)
        font_text = ImageFont.truetype(font_path, 26)  # Леко увеличен шрифт за името на детайла
        font_huge = ImageFont.truetype(font_path, 45)
        
        # УВЕЛИЧЕН ШРИФТ ЗА КАНТОВЕТЕ (от 24 на 38)
        font_edge = ImageFont.truetype(font_path, 38) 
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
        p_name = str(lbl.get('part_name', lbl.get('Детайл', '')))
        mat_text = str(lbl.get('mat_label', lbl.get('Плоскост', '')))
        
        # --- ИЗЧИСТВАНЕ НА ИМЕТО ---
        # 1. Ако името съдържа скоба "]", махаме всичко до нея (чистим "[Шкаф Колона]")
        if ']' in p_name:
            p_name = p_name.split(']')[-1].strip()
            
        # 2. Ако има вертикална черта (напр. "Рафт тв. | Рафт тв."), вземаме само чистото име
        if '|' in p_name:
            p_name = p_name.split('|')[-1].strip()

        # Сглобяваме финалния текст: само Номер на шкафа и Име на детайла
        top_text = f"[{m_num}] {p_name}"

        dim_text = f"{int(lbl.get('l', 0))} x {int(lbl.get('w', 0))}"
        bot_text = f"{mat_text[:22]}"

        # СВАЛЯМЕ ГОРНИЯ ТЕКСТ ПО-НАДОЛУ (+24 пиксела), за да не се засича с големия кант
        draw.text((x + label_w/2, y + padding + 24), top_text, fill="black", font=font_text, anchor="mt")
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
