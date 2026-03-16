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
hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
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

# --- ЛОГИКА ЗА ЗАПИС ---
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
    if "рафт" in d: return "Рфт"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело" in d: return "Чело"
    if "царги" in d: return "Цч"
    if "страници чекм" in d: return "Сч"
    return detail_name[:5].capitalize()

def get_module_abbrev(tip):
    t = str(tip).lower()
    if "3 чекмеджета" in t: return "Шк 3 ч-та"
    if "стандартен долен" in t: return "Долен шк"
    if "горен шкаф" in t: return "Горен шк"
    if "шкаф мивка" in t: return "Шк мивка"
    if "шкаф за фурна" in t: return "Шк фурна"
    if "шкаф колона" in t: return "Колона"
    if "трети ред" in t: return "3-ти ред"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- ФУНКЦИЯ ЗА ЧЕРТАНЕ (ПРЕВЮ И PDF) ---
def draw_cabinet(mod_meta, kraka_height, preview=False):
    canvas_w = 400 if preview else 2480 # Намалено превю с 25%+
    canvas_h = 500 if preview else 3508
    img = Image.new('RGB', (canvas_w, canvas_h), 'white')
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try:
        f_dim = ImageFont.truetype(font_path, 18 if preview else 60)
        f_title = ImageFont.truetype(font_path, 22 if preview else 80)
    except:
        f_dim = f_title = ImageFont.load_default()

    W, H, D = float(mod_meta['W']), float(mod_meta['H']), float(mod_meta['D'])
    scale = (300.0 / max(W, H, D)) if preview else (1200.0 / max(W, H, D))
    
    w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
    ox, oy = d_px * 0.866, d_px * 0.5
    sx = (canvas_w - (w_px + ox)) / 2
    sy = (canvas_h / 2) - (h_px / 2)
    
    # Кутия
    is_3rd = "Трети ред" in mod_meta['Тип']
    if is_3rd:
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=2)
        draw.polygon([(sx, sy+h_px), (sx+ox, sy+h_px-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#e0e0e0", outline="black", width=2)
    else:
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=2)
        draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black", width=2)
    
    draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=3)

    # Крака
    is_lower = any(t in mod_meta['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"])
    leg_h_px = (kraka_height * scale) if is_lower else 0
    if is_lower:
        draw.line([(sx, sy+h_px-leg_h_px), (sx+w_px, sy+h_px-leg_h_px)], fill="gray", width=2)

    # Деления (врати/чекмеджета/уреди)
    tip = mod_meta['Тип']
    if "3 Чекмеджета" in tip:
        draw.line([(sx, sy+180*scale), (sx+w_px, sy+180*scale)], fill="black", width=2)
        draw.line([(sx, sy+(180+250)*scale), (sx+w_px, sy+(180+250)*scale)], fill="black", width=2)
    elif "Колона" in tip:
        ld_h, md_h = mod_meta.get('ld_h', 0), mod_meta.get('md_h', 0)
        curr_y = sy + h_px - leg_h_px
        if ld_h > 0: draw.line([(sx, curr_y - ld_h*scale), (sx+w_px, curr_y - ld_h*scale)], fill="black", width=2)
        if md_h > 0: draw.line([(sx, curr_y - (ld_h+md_h)*scale), (sx+w_px, curr_y - (ld_h+md_h)*scale)], fill="black", width=2)
        if mod_meta.get('app_type') != "Без уреди":
            draw.text((sx+w_px/2, sy+h_px/3), "УРЕДИ", anchor="mm", font=f_dim, fill="#999")

    if mod_meta.get('vr_cnt', 1) == 2 and "Чекмеджета" not in tip:
        draw.line([(sx+w_px/2, sy), (sx+w_px/2, sy+h_px-leg_h_px)], fill="black", width=2)

    # Заглавие само за PDF
    if not preview:
        draw.text((150, 150), f"МОДУЛ: {mod_meta['№']} - {mod_meta['Тип']}", fill="black", font=f_title)
    return img

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    st.markdown("---")
    st.header("🎨 Материали")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло гладко 18мм")
    val_fl_korpus = "Да" if st.checkbox("Има фладер - Корпус", value=False) else "Няма"
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    val_fl_lice = "Да" if st.checkbox("Има фладер - Лице", value=True) else "Няма"
    mat_chekm = st.text_input("Декор Чекмеджета:", value="Бяло гладко 18мм")
    val_fl_chekm = "Да" if st.checkbox("Има фладер - Чекмеджета", value=False) else "Няма"
    mat_fazer = st.text_input("Декор Фазер:", value="Бял фазер 3мм")
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []; st.session_state.hardware_list = []; st.session_state.modules_meta = []; st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    cat_choice = st.radio("Избери категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)

    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {"Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", "Шкаф Мивка": "🚰", "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"}
    else:
        icons = {"Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"}

    tip = st.selectbox("Тип модул", options=list(icons.keys()))
    name = st.text_input("Име/№ на модула", value="1")
    
    w = 600; h = 720; d = 520; app_type = "Без уреди"; ld_h = 0; md_h = 0; vrati_broi = 1

    if tip == "Дублираща страница долен":
        h = st.number_input("Височина (H) мм", value=860); d = st.number_input("Дълбочина (D) мм", value=580); w = deb
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Детайл"); colA, colB = st.columns(2)
        h = colA.number_input("Дължина мм", value=600); d = colB.number_input("Ширина мм", value=300)
    elif tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина (W) мм", value=600); h = st.number_input("Височина (H) мм", value=350); d = st.number_input("Дълбочина (D) мм", value=500)
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600); h_korp = st.number_input("Височина корпус мм", value=2040); d = st.number_input("Дълбочина мм", value=550)
        app_type = st.radio("Уреди:", ["Без уреди", "Само Фурна", "Фурна + Микровълнова"], horizontal=True)
        vr_mode = st.selectbox("Врати по височина:", ["1 цяла", "2 врати", "3 врати"])
        if vr_mode == "2 врати": ld_h = st.number_input("Височина долна врата мм", value=718)
        elif vr_mode == "3 врати":
            ld_h = st.number_input("Височина долна врата 1 мм", value=718)
            md_h = st.number_input("Височина средна врата 2 мм", value=718)
        vrati_broi = st.radio("Врати на ред:", [1, 2], index=1 if w > 500 else 0)
        h = h_korp + kraka
    else:
        w = st.number_input("Ширина (W) мм", value=600)
        if "Горен" in tip: h = 720; d = 300; vrati_broi = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0)
        else: h = 742 + kraka + 38; d = 520; vrati_broi = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0)

    # ПРЕВЮ НА ЖИВО
    curr_meta = {"№": name, "Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi, "ld_h": ld_h, "md_h": md_h, "app_type": app_type}
    st.image(draw_cabinet(curr_meta, kraka, preview=True), width=350)

    if st.button("➕ ДОБАВИ КЪМ СПИСЪКА"):
        st.session_state.modules_meta.append(curr_meta)
        new_items = []
        new_hw = []
        
        # Логика за добавяне на детайли (запазена от твоя код)
        if tip == "Шкаф Колона":
            new_items.extend([add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Страница", 2, h - kraka - deb, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus)])
            w_v = (w/vrati_broi) - fuga_obshto
            if ld_h > 0 and md_h > 0: # 3 врати
                new_items.append(add_item(name, tip, "Врата долна", vrati_broi, ld_h, w_v, "4 стр", mat_lice, val_fl_lice))
                new_items.append(add_item(name, tip, "Врата средна", vrati_broi, md_h, w_v, "4 стр", mat_lice, val_fl_lice))
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h-kraka-ld_h-md_h-fuga_obshto*2, w_v, "4 стр", mat_lice, val_fl_lice))
            elif ld_h > 0: # 2 врати
                new_items.append(add_item(name, tip, "Врата долна", vrati_broi, ld_h, w_v, "4 стр", mat_lice, val_fl_lice))
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h-kraka-ld_h-fuga_obshto, w_v, "4 стр", mat_lice, val_fl_lice))
            else:
                new_items.append(add_item(name, tip, "Врата", vrati_broi, h-kraka-fuga_obshto, w_v, "4 стр", mat_lice, val_fl_lice))
        elif tip == "Трети ред (Надстройка)":
            new_items.extend([add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Страница", 2, h-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Врата", 1, h-fuga_obshto, w-fuga_obshto, "4 стр", mat_lice, val_fl_lice)])
        else:
             new_items.append(add_item(name, tip, "Страница", 2, h-kraka if is_lower else h, d, "1д", mat_korpus, val_fl_korpus))

        st.session_state.order_list.extend(new_items); st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        cols_order = ["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Бр", "Д1", "Д2", "Ш1", "Ш2"]
        edited_df = st.data_editor(df[cols_order], num_rows="dynamic", use_container_width=True, height=350)
        st.session_state.order_list = edited_df.to_dict('records')
        
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button("📄 Свали PDF Чертежи"):
                pdf_io = io.BytesIO()
                all_p = [draw_cabinet(m, kraka) for m in st.session_state.modules_meta]
                all_p[0].save(pdf_io, format="PDF", save_all=True, append_images=all_p[1:])
                st.download_button("📥 Свали PDF", pdf_io.getvalue(), "Cherteji.pdf")
        
        # Финанси
        area = (pd.to_numeric(edited_df['Дължина']) * pd.to_numeric(edited_df['Ширина']) * pd.to_numeric(edited_df['Бр'])).sum() / 1000000
        st.info(f"Обща площ: {area:.2f} м² | Оферта: {area * 50:.2f} €")
