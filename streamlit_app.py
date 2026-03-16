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
    if "шкаф колона" in t: return "Колона"
    if "трети ред" in t: return "3-ти ред"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- ФУНКЦИЯ ЗА ПРЕВЮ (3D) ---
def draw_mini_preview(mod_meta, kraka_height):
    img = Image.new('RGB', (200, 250), 'white')
    draw = ImageDraw.Draw(img)
    W, H, D = float(mod_meta.get('W', 600)), float(mod_meta.get('H', 720)), float(mod_meta.get('D', 550))
    scale = 100.0 / max(W, H, D) if max(W, H, D) > 0 else 1
    w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
    ox, oy = d_px * 0.8, d_px * 0.5
    sx, sy = (200 - (w_px + ox)) / 2, (250 - (h_px + oy)) / 2 + oy
    draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black")
    draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black")
    draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=2)
    is_lower = any(t in mod_meta['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"])
    if is_lower:
        leg_px = kraka_height * scale
        draw.rectangle([sx+5, sy+h_px, sx+10, sy+h_px+leg_px], fill="black")
        draw.rectangle([sx+w_px-10, sy+h_px, sx+w_px-5, sy+h_px+leg_px], fill="black")
    if mod_meta.get('vr_cnt', 1) == 2:
        draw.line([(sx+w_px/2, sy), (sx+w_px/2, sy+h_px)], fill="black", width=1)
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
    cat_choice = st.radio("Категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Други"], horizontal=True)
    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {"Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", "Шкаф Мивка": "🚰", "Шкаф 3 Чекмеджета": "🔢", "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"}
    else:
        icons = {"Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"}
    
    tip = st.selectbox("Тип модул", options=list(icons.keys()))
    name = st.text_input("Име/№", value="1")
    
    # Стойности по подразбиране
    w, h, d, vrati_broi = 600, 720, 520, 1
    has_app = "Без уреди"; lower_mode = "Врата"; lower_door_h = 718; ch_heights = []; runner_len = 500

    if tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина W мм", value=600)
        h = st.number_input("Височина H мм", value=350)
        d = st.number_input("Дълбочина D мм", value=500)
        vrati_broi = st.radio("Врати:", [1, 2], horizontal=True)
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина W мм", value=600)
        h_korp = st.number_input("Височина корпус мм", value=2040)
        d = st.number_input("Дълбочина D мм", value=550)
        h = h_korp + kraka
        has_app = st.selectbox("Уреди:", ["Без уреди", "Само Фурна", "Само Микровълнова", "Фурна + Микровълнова"])
        lower_mode = st.radio("Долна част:", ["Врата", "До 3 чекмеджета"], horizontal=True)
        if lower_mode == "До 3 чекмеджета":
            num_ch = st.slider("Брой чекмеджета:", 1, 3, 2)
            for i in range(num_ch): ch_heights.append(st.number_input(f"Чело {i+1} H", value=360, key=f"c_h_{i}"))
            runner_len = st.number_input("Водач мм", value=500, step=50)
        else: lower_door_h = st.number_input("Долна врата H", value=718)
        vrati_broi = st.radio("Врати на ред:", [1, 2], index=1 if w > 500 else 0, horizontal=True)
    else:
        w = st.number_input("Ширина W мм", value=600)
        if "Горен" in tip: h = st.number_input("H мм", value=720); d = 300
        else: h, d = 742 + kraka + 38, 520
        vrati_broi = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True)

    st.image(draw_mini_preview({"Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi}, kraka), width=180)

    if st.button("➕ Добави към списъка"):
      new_items = []
        new_hw = []
        otstyp_fazer = 4; h_stranica_std = 742; h_korpus_std = h_stranica_std + deb; h_vrata_std = h_korpus_std - fuga_obshto
        
        # Мета данни за чертежите
        st.session_state.modules_meta.append({"№": name, "Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi})

        # --- 1. ТРЕТИ РЕД (НАДСТРОЙКА) ---
        if tip == "Трети ред (Надстройка)":
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница (вътрешна)", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата (Клапваща)", vrati_broi, h - fuga_obshto, (w/vrati_broi) - fuga_obshto, "4 страни", mat_lice, val_fl_lice)
            ])
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(h)*vrati_broi})

        # --- 2. ШКАФ КОЛОНА (С ПРОМЕНЛИВИ ЧЕЛА) ---
        elif tip == "Шкаф Колона":
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h - kraka - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - kraka - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            h_f = 595 if "Фурна" in has_app else 0
            h_m = 380 if "Микровълнова" in has_app else 0
            
            if lower_mode == "До 3 чекмеджета":
                cw = w - (2*deb) - 49; total_low_h = sum(ch_heights)
                for idx, ch_h in enumerate(ch_heights):
                    new_items.append(add_item(name, tip, f"Чело {idx+1}", 1, ch_h - fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                    new_items.extend([
                        add_item(name, tip, f"Царги ч.{idx+1}", 2, cw, 160, "1д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, f"Страници ч.{idx+1}", 2, runner_len - 10, 175, "2д", mat_chekm, val_fl_chekm),
                        add_item(name, tip, f"Дъно ч.{idx+1}", 1, runner_len - 13, cw + 12, "Без", mat_fazer, "Няма")
                    ])
                new_hw.append({"№": name, "Артикул": "Водачи за чекм.", "Брой": len(ch_heights)})
            else:
                total_low_h = lower_door_h
                new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lower_door_h, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
            
            h_up_v = (h - kraka) - total_low_h - h_f - h_m - (fuga_obshto * 2)
            if h_up_v > 100:
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_up_v, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))

        # --- 3. СТАНДАРТНИ МОДУЛИ ---
        else:
            if "Горен" in tip:
                new_items.extend([
                    add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                    add_item(name, tip, "Врата", vrati_broi, h - fuga_obshto, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice)
                ])
            else:
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница", 2, h_stranica_std, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Гръб (Фазер)", 1, h_korpus_std - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                    add_item(name, tip, "Врата", vrati_broi, h_vrata_std, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice)
                ])

        st.session_state.order_list.extend(new_items); st.session_state.hardware_list.extend(new_hw); st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=450)
        st.session_state.order_list = edited_df.to_dict('records')
        
        # Обков
        if st.session_state.hardware_list:
            hw_sum = pd.DataFrame(st.session_state.hardware_list).groupby("Артикул")["Брой"].sum().reset_index()
            st.table(hw_sum)

# --- ТЕХНИЧЕСКИ ФУНКЦИИ ---
def generate_technical_pdf(modules_meta, order_list, kraka_height):
    font_path = "Roboto-Regular.ttf"
    try: f_title = ImageFont.truetype(font_path, 80); f_text = ImageFont.truetype(font_path, 50)
    except: f_title = f_text = ImageFont.load_default()
    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white'); draw = ImageDraw.Draw(img)
        draw.text((150, 150), f"МОДУЛ: {mod['№']} - {mod['Тип']}", fill="black", font=f_title)
        # (тук е твоята PDF логика...)
        pages.append(img)
    if pages:
        pdf_b = io.BytesIO(); pages[0].save(pdf_b, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_b.getvalue()
    return None

# ТУК ЗАЛЕПИ ОСТАНАЛИТЕ ТВОИ ФУНКЦИИ (етикети, разкрой и финансовия калкулатор)
