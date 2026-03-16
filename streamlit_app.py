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
.block-container { padding-top: 2.5rem !important; padding-bottom: 1.5rem !important; }
h1, h2, h3, h4, h5 { padding-top: 0.3rem !important; padding-bottom: 0.3rem !important; margin-bottom: 0 !important; }
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
    if "шкаф мивка" in t: return "Шк мивка"
    if "шкаф за фурна" in t: return "Шк фурна"
    if "шкаф колона" in t: return "Колона"
    if "бутилки" in t: return "Бутилки"
    if "глух ъгъл (долен)" in t: return "Глух дол"
    if "глух ъгъл (горен)" in t: return "Глух гор"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950:
        return 2
    elif height <= 1300:
        return 3
    else:
        return 4

def draw_mini_preview(mod_meta, kraka_height):
    img = Image.new('RGB', (200, 250), 'white')
    draw = ImageDraw.Draw(img)
    
    # Вземаме размерите
    W = float(mod_meta.get('W', 600))
    H = float(mod_meta.get('H', 720))
    D = float(mod_meta.get('D', 550))
    tip = mod_meta.get('Тип', '')
    vr_cnt = int(mod_meta.get('vr_cnt', 1))
    app_type = mod_meta.get('app_type', "Без уреди")
    ld_h = float(mod_meta.get('ld_h', 0)) # височина на долната част при колона

    # Мащабиране
    scale = 110.0 / max(W, H, D) if max(W, H, D) > 0 else 1
    w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
    ox, oy = d_px * 0.8, d_px * 0.5
    sx, sy = (200 - (w_px + ox)) / 2, (250 - (h_px + oy)) / 2 + oy

    # 1. Рисуване на корпуса (3D тяло)
    draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black")
    draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black")
    draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=2)

    # 2. Крачета (за долни модули)
    if any(t in tip for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"]):
        leg_px = kraka_height * scale
        draw.rectangle([sx+5, sy+h_px, sx+10, sy+h_px+leg_px], fill="black")
        draw.rectangle([sx+w_px-10, sy+h_px, sx+w_px-5, sy+h_px+leg_px], fill="black")

    # 3. Визуализация на Лицето (Чела/Врати/Уреди)
    
    # --- ЛОГИКА ЗА ЧЕКМЕДЖЕТА ---
    if "Чекмеджета" in tip and "Колона" not in tip:
        # Рисуваме хоризонтални линии за 3-те стандартни или динамичните чекмеджета
        num_ch = 3 # по подразбиране
        for i in range(1, num_ch):
            y_line = sy + (h_px / num_ch) * i
            draw.line([(sx, y_line), (sx + w_px, y_line)], fill="black", width=1)

    # --- ЛОГИКА ЗА КОЛОНА С УРЕДИ ---
    elif tip == "Шкаф Колона":
        curr_y = sy + h_px # започваме от долу нагоре
        # 1. Долна част (врата или чекмеджета)
        if ld_h > 0:
            split_y = sy + h_px - (ld_h * scale)
            draw.line([(sx, split_y), (sx + w_px, split_y)], fill="black", width=2)
            curr_y = split_y
            
        # 2. Ниши за уреди
        if "Фурна" in app_type:
            f_h = 595 * scale
            draw.rectangle([sx+5, curr_y - f_h + 5, sx+w_px-5, curr_y - 5], outline="red", width=1) # Фурна
            curr_y -= f_h
        if "Микровълнова" in app_type:
            m_h = 380 * scale
            draw.rectangle([sx+10, curr_y - m_h + 5, sx+w_px-10, curr_y - 5], outline="blue", width=1) # МВ
            
    # 4. Вертикална линия за 2 врати
    if vr_cnt == 2 and "Чекмеджета" not in tip:
        draw.line([(sx + w_px/2, sy), (sx + w_px/2, sy + h_px)], fill="black", width=1)

    return img

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
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
        st.session_state.order_list = []
        st.session_state.hardware_list = []
        st.session_state.modules_meta = []
        st.rerun()

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
        icons = {
            "Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"
        }

    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    name = st.text_input("Име/№ на модула", value=tip)
    
    # --- Инициализация на променливи (за предотвратяване на NameError) ---
    appliances_type = "Без уреди"
    split_doors = False
    lower_door_h = 0
    lower_type = "Врата"
    vrati_broi = 1
    ch_heights = [] # Важно за динамичните чекмеджета
    runner_len = 500
    
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
        colD, colE = st.columns(2)
        custom_kant = colD.selectbox("Кант", ["Без", "1д", "2д", "4 страни"], index=3)
        custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер"])
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600, key="w_col")
        h_korpus = st.number_input("Височина корпуса (H) мм", value=2040, key="h_col")
        d = st.number_input("Дълбочина (D) мм", value=550, key="d_col")
        appliances_type = st.radio("Вградени уреди:", ["Без уреди", "Само Фурна", "Само Микровълнова", "Фурна + Микровълнова"], horizontal=True)
        if appliances_type != "Без уреди":
            lower_door_h = st.number_input("Височина на долната част мм", value=718)
            lower_type = st.radio("Тип долна част:", ["Врата", "2 Чекмеджета", "3 Чекмеджета"], horizontal=True)
            if "Чекмеджета" in lower_type: runner_len = st.number_input("Дължина водач (мм)", value=500, step=50, key="run_col")
        else:
            split_doors = st.checkbox("Две врати по височина (Долна + Горна)?", value=True)
            if split_doors: lower_door_h = st.number_input("Височина долна врата (мм)", value=718)
        vrati_broi = st.radio("Брой врати на ред:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_col")
        h = h_korpus + kraka 
    elif tip == "Шкаф 3 Чекмеджета":
        w = st.number_input("Ширина (W) мм", value=600, key="w_ch")
        num_ch = st.slider("Брой чекмеджета:", 1, 6, 3, key="n_ch")
        st.markdown("##### Височини на челата (мм):")
        cols_ch = st.columns(num_ch)
        for i in range(num_ch):
            with cols_ch[i]:
                val_h = st.number_input(f"Чело {i+1}", value=int(718/num_ch), key=f"ch_h_inp_{i}")
                ch_heights.append(val_h)
        runner_len = st.number_input("Водач (мм)", value=500, step=50, key="run_ch")
        d = st.number_input("Дълбочина (D) мм", value=520, key="d_ch")
        h = 742 + kraka + 38
    else:
        default_w = 150 if tip == "Шкаф Бутилки 15см" else (1000 if "Глух" in tip else 600)
        w = st.number_input("Ширина (W) мм", value=default_w, key="w_std")
        if "Горен" in tip:
            h = st.number_input("Височина (H) мм", value=720, key="h_up")
            d = st.number_input("Дълбочина (D) мм", value=300, key="d_up")
            vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_up")
            vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални"], horizontal=True) if tip == "Горен Шкаф" else "Вертикални"
        else:
            d = st.number_input("Дълбочина (D) мм", value=(550 if tip == "Шкаф Мивка" else 520), key="d_low")
            h = 742 + kraka + 38 
            vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True, key="vr_low")

    # --- ВИЗУАЛИЗАЦИЯ (Преди бутона за добавяне) ---
    st.markdown("---")
    temp_meta = {"Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vrati_broi}
    preview_img = draw_mini_preview(temp_meta, kraka)
    st.image(preview_img, caption="Скица на модула")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Добави към списъка"):
        new_items = []
        new_hw = []
        otstyp_fazer = 4; h_stranica = 742; h_shkaf_korpus = h_stranica + deb; h_vrata_standart = h_shkaf_korpus - fuga_obshto
        
        # Записване на мета данни
        meta_dict = {"№": name, "Тип": tip, "W": w, "H": h, "D": d}
        if tip == "Шкаф Колона": meta_dict.update({"app_type": appliances_type, "ld_h": lower_door_h, "lower_type": lower_type})
        st.session_state.modules_meta.append(meta_dict)

        # 1. ОБКОВ: Крака
        if any(x in tip for x in ["Долен", "Мивка", "Бутилки", "Чекмеджета", "Фурна", "Колона"]):
            new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": 5 if w > 900 else 4})

        # --- СПЕЦИФИЧНА ЛОГИКА ---
        if tip == "Трети ред (Надстройка)":
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата", vrati_broi, h - fuga_obshto, (w/vrati_broi) - fuga_obshto, "4 страни", mat_lice, val_fl_lice)
            ])
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": calculate_hinges(h)*vrati_broi})

        elif tip == "Шкаф 3 Чекмеджета":
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            cw = w - (2*deb) - 49
            for idx, ch_h in enumerate(ch_heights):
                h_tsarga = max(70, ch_h - 60) # Автоматична царга (чело - 60)
                new_items.append(add_item(name, tip, f"Чело {idx+1}", 1, ch_h-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, tip, f"Царга ч.{idx+1}", 2, cw, h_tsarga, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, tip, f"Стр. кутия ч.{idx+1}", 2, runner_len-10, h_tsarga+15, "2д", mat_chekm, val_fl_chekm))
            new_hw.append({"№": name, "Артикул": "Водачи", "Брой": len(ch_heights)})

        elif tip == "Шкаф Колона":
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h_korpus - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            h_f = 595 if "Фурна" in appliances_type else 0
            h_m = 380 if "Микровълнова" in appliances_type else 0
            if appliances_type != "Без уреди":
                new_items.append(add_item(name, tip, "Рафт ниша", (2 if h_f and h_m else 1), w-(2*deb), d, "1д", mat_korpus, val_fl_korpus))
            # Лице
            w_v = int((w/vrati_broi) - fuga_obshto)
            if lower_type == "Врата":
                new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lower_door_h, w_v, "4 страни", mat_lice, val_fl_lice))
            h_up = h_korpus - lower_door_h - h_f - h_m - (fuga_obshto*2)
            if h_up > 150:
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_up, w_v, "4 страни", mat_lice, val_fl_lice))

        else: # Стандартни
            if "Горен" in tip:
                new_items.extend([
                    add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Врата", vrati_broi, h-fuga_obshto, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice)
                ])
            else:
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, 480 if "Мивка" in tip else d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Врата", vrati_broi, h_vrata_standart, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice)
                ])

        st.session_state.order_list.extend(new_items); st.session_state.hardware_list.extend(new_hw)
        st.success(f"Модул {name} добавен!"); st.rerun()

# --- ФУНКЦИЯ ЗА ЧЕРТЕЖИ ---
# --- ФУНКЦИЯ ЗА ЧЕРТЕЖИ (3D Версия + Спецификация) ---
def generate_technical_pdf(modules_meta, order_list, kraka_height=100):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: 
        font_title = ImageFont.truetype(font_path, 80)
        font_text = ImageFont.truetype(font_path, 40) 
        font_dim = ImageFont.truetype(font_path, 50)
        font_bold = ImageFont.truetype(font_path, 45)
    except: 
        font_title = font_text = font_dim = font_bold = ImageFont.load_default()

    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white')
        draw = ImageDraw.Draw(img)
        
        # 1. Заглавие
        draw.text((150, 150), f"ТЕХНИЧЕСКИ ЧЕРТЕЖ: {mod['№']} - {mod['Тип']}", fill="black", font=font_title)
        draw.line([(150, 260), (2330, 260)], fill="black", width=5)

        W, H, D = float(mod['W']), float(mod['H']), float(mod['D'])
        scale = 800.0 / max(W, H, D) if max(W, H, D) > 0 else 1
        w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
        
        # 3D перспектива
        ox, oy = d_px * 0.8, d_px * 0.5
        sx, sy = 1450 - (w_px + ox)/2, 1100 - (h_px + oy)/2

        # --- ФУНКЦИЯ ЗА ЗАВЪРТАН ТЕКСТ ---
        def draw_rotated_text(image, center_x, center_y, text, font, color):
            txt_w = int(font.getlength(text))
            txt_h = int(font.size)
            txt_img = Image.new('RGBA', (txt_w + 40, txt_h + 40), (255, 255, 255, 0))
            d = ImageDraw.Draw(txt_img)
            d.text((20, 20), text, font=font, fill=color)
            rotated = txt_img.rotate(90, expand=True)
            paste_x = int(center_x - rotated.width / 2)
            paste_y = int(center_y - rotated.height / 2)
            image.paste(rotated, (paste_x, paste_y), rotated)

        # --- ФУНКЦИЯ ЗА СТЪПАЛОВИДНИ КОТИ ---
        def draw_vitya_dim(p_top_y, p_bottom_y, offset_x, text, color="black"):
            line_x = sx - offset_x
            draw.line([(line_x, p_top_y), (line_x, p_bottom_y)], fill=color, width=3)
            draw.line([(line_x - 20, p_top_y), (line_x + 10, p_top_y)], fill=color, width=3)
            draw.line([(line_x - 20, p_bottom_y), (line_x + 10, p_bottom_y)], fill=color, width=3)
            draw_rotated_text(img, line_x - 45, (p_top_y + p_bottom_y)/2, text, font_dim, color)

        # 2. РИСУВАНЕ НА КОРПУСА В 3D
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#eeeeee", outline="black", width=3)
        draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#dddddd", outline="black", width=3)
        draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="white", outline="black", width=5)
        
        # Крачета 100мм (за долни модули)
        is_lower = any(t in mod['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"])
        leg_px = 100 * scale if is_lower else 0
        if is_lower:
            draw.rectangle([sx+40, sy+h_px, sx+90, sy+h_px+leg_px], fill="black")
            draw.rectangle([sx+w_px-90, sy+h_px, sx+w_px-40, sy+h_px+leg_px], fill="black")

        # Най-външна кота: Обща височина
        draw_vitya_dim(sy, sy+h_px, 450, f"{int(H)}")

        # Вземаме детайлите за текущия модул, за да ги четем
        mod_parts = [p for p in order_list if str(p.get("№", "")) == str(mod["№"])]

        # --- СПЕЦИФИЧНА ЛОГИКА ЗА ЛИЦЕТО СПОРЕД ТИПА ---
        
        # А) ШКАФ КОЛОНА (както го направихме досега)
        if mod['Тип'] == "Шкаф Колона":
            offsets = [120, 230, 340] 
            off_idx = 0
            ld_h = float(mod.get('ld_h', 718))
            app_type = mod.get('app_type', "Без уреди")
            
            y_shelf = sy + h_px - (ld_h * scale)
            for x in range(int(sx), int(sx + w_px), 25): draw.line([(x, y_shelf), (min(x+12, sx+w_px), y_shelf)], fill="black", width=3)
            draw_vitya_dim(y_shelf, sy+h_px, offsets[off_idx], f"{int(ld_h)}")
            off_idx += 1
            
            top_y = y_shelf; total_h = ld_h

            if "Фурна" in app_type:
                f_h = 600
                y_top = top_y - (f_h * scale)
                draw.rectangle([sx, y_top, sx+w_px, top_y], outline="black", width=4)
                draw.rectangle([sx+80*scale, y_top+80*scale, sx+w_px-80*scale, top_y-80*scale], outline="#333", width=2)
                draw.text((sx + w_px/2, (y_top + top_y)/2), "ФУРНА", font=font_dim, fill="#333", anchor="mm")
                
                top_y = y_top; total_h += f_h
                for x in range(int(sx), int(sx + w_px), 25): draw.line([(x, top_y), (min(x+12, sx+w_px), top_y)], fill="black", width=3)
                draw_vitya_dim(top_y, sy+h_px, offsets[off_idx], f"{int(total_h)}")
                off_idx += 1

            if "Микровълнова" in app_type:
                m_h = 380
                y_top = top_y - (m_h * scale)
                draw.rectangle([sx, y_top, sx+w_px, top_y], outline="black", width=4)
                draw.rectangle([sx+80*scale, y_top+60*scale, sx+w_px-80*scale, top_y-60*scale], outline="#333", width=2)
                draw.text((sx + w_px/2, (y_top + top_y)/2), "МВ", font=font_dim, fill="#333", anchor="mm")
                
                top_y = y_top; total_h += m_h
                for x in range(int(sx), int(sx + w_px), 25): draw.line([(x, top_y), (min(x+12, sx+w_px), top_y)], fill="black", width=3)
                draw_vitya_dim(top_y, sy+h_px, offsets[off_idx], f"{int(total_h)}")
                off_idx += 1

            if (H - total_h) > 600:
                mid_h = total_h + ((H - total_h) / 2)
                y_mid = sy + h_px - (mid_h * scale)
                for x in range(int(sx), int(sx + w_px), 25): draw.line([(x, y_mid), (min(x+12, sx+w_px), y_mid)], fill="gray", width=3)
                draw_vitya_dim(y_mid, sy+h_px, offsets[off_idx], f"{int(mid_h)}")

        # Б) ШКАФ С ЧЕКМЕДЖЕТА (Динамични чела)
        elif "Чекмеджета" in mod['Тип']:
            chela = [p for p in mod_parts if "Чело" in str(p['Детайл'])]
            if chela:
                curr_y = sy
                for c in chela:
                    c_h = float(c['Дължина']) # Височината на челото
                    c_h_px = c_h * scale
                    # Чертаем хоризонтална линия за разделител между челата
                    draw.line([(sx, curr_y + c_h_px), (sx + w_px, curr_y + c_h_px)], fill="black", width=4)
                    # Слагаме кота само за това чело (последователно)
                    draw_vitya_dim(curr_y, curr_y + c_h_px, 120, f"{int(c_h)}")
                    curr_y += c_h_px

        # В) ШКАФ ЗА ФУРНА (Долен)
        elif mod['Тип'] == "Шкаф за Фурна":
            f_h = 595
            f_h_px = f_h * scale
            
            # 1. Фурна най-горе
            draw.rectangle([sx, sy, sx+w_px, sy+f_h_px], outline="black", width=4)
            draw.rectangle([sx+60*scale, sy+60*scale, sx+w_px-60*scale, sy+f_h_px-60*scale], outline="#333", width=2)
            draw.text((sx + w_px/2, sy + f_h_px/2), "ФУРНА", font=font_dim, fill="#333", anchor="mm")
            draw_vitya_dim(sy, sy+f_h_px, 120, f"{int(f_h)}")
            
            # 2. Врата отдолу (цяла)
            door_h = H - f_h
            if door_h > 0:
                draw_vitya_dim(sy+f_h_px, sy+h_px, 120, f"{int(door_h)}")

        # Г) СТАНДАРТНИ ШКАФОВЕ (С 1 или 2 врати)
        else:
            # Търсим дали има детайл "Врата" и колко бройки е
            vrati = [p for p in mod_parts if "Врата" in str(p['Детайл'])]
            vr_cnt = mod.get('vr_cnt', 1)
            if vrati: vr_cnt = int(vrati[0]['Бр'])
            
            if vr_cnt == 2: # Ако са 2 врати, чертаем вертикална линия по средата
                draw.line([(sx + w_px/2, sy), (sx + w_px/2, sy + h_px)], fill="black", width=4)

        # --- Ширина и Дълбочина ---
        draw.line([(sx, sy + h_px + leg_px + 80), (sx + w_px, sy + h_px + leg_px + 80)], fill="black", width=3)
        draw.line([(sx, sy + h_px + leg_px + 60), (sx, sy + h_px + leg_px + 100)], fill="black", width=3)
        draw.line([(sx+w_px, sy + h_px + leg_px + 60), (sx+w_px, sy + h_px + leg_px + 100)], fill="black", width=3)
        draw.text((sx + w_px/2, sy + h_px + leg_px + 130), f"{int(W)}", font=font_dim, fill="black", anchor="mm")
        
        draw.text((sx + w_px + ox + 60, sy + h_px - oy/2), f"D: {int(D)}", font=font_dim, fill="#555", anchor="mm")

        # --- ТАБЛИЦА СЪС СПЕЦИФИКАЦИЯ ---
        draw.text((150, 2050), "СПЕЦИФИКАЦИЯ НА ДЕТАЙЛИТЕ (РАЗМЕРИ ЗА РАЗКРОЙ)", fill="black", font=font_bold)
        y_tab = 2150
        headers = ["ДЕТАЙЛ", "ДЪЛЖ.", "ШИР.", "БР.", "МАТЕРИАЛ", "КАНТ"]
        tab_cols = [150, 850, 1100, 1300, 1500, 1950]
        
        for i, h in enumerate(headers): draw.text((tab_cols[i], y_tab), h, font=font_bold, fill="black")
        draw.line([(150, y_tab+60), (2330, y_tab+60)], fill="black", width=3)
        y_tab += 90

        for p in mod_parts:
            draw.text((tab_cols[0], y_tab), str(p['Детайл'])[:25], font=font_text, fill="black")
            draw.text((tab_cols[1], y_tab), str(int(p['Дължина'])), font=font_text, fill="black")
            draw.text((tab_cols[2], y_tab), str(int(p['Ширина'])), font=font_text, fill="black")
            draw.text((tab_cols[3], y_tab), str(int(p['Бр'])), font=font_text, fill="black")
            draw.text((tab_cols[4], y_tab), str(p['Плоскост'])[:15], font=font_text, fill="black")
            draw.text((tab_cols[5], y_tab), f"{p.get('Д1','-')}|{p.get('Ш1','-')}", font=font_text, fill="black")
            y_tab += 70
            if y_tab > 3350: break

        pages.append(img)
    
    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_bytes.getvalue()
    return None
  # --- ТОВА ВРЪЩА ТАБЛИЦАТА НА ЕКРАНА ---
with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        # Подреждаме колоните, за да изглеждат добре
        cols_order = ["Плоскост", "№", "Тип", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[[c for c in cols_order if c in df.columns]]
        
        # Основният редактор на таблицата
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=450, key="main_editor")
        st.session_state.order_list = edited_df.to_dict('records')
        
        # Бутон за сваляне на Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Разкрой')
        st.download_button(label="📊 Свали в Excel (.xlsx)", data=output.getvalue(), file_name="razkroi_vitya.xlsx")
        
        # Показваме и обкова под таблицата
        if st.session_state.hardware_list:
            st.markdown("#### 🔩 Количествена сметка: Обков")
            hw_df = pd.DataFrame(st.session_state.hardware_list)
            hw_summary = hw_df.groupby("Артикул")["Брой"].sum().reset_index()
            st.table(hw_summary)
    else:
        st.info("Списъкът е празен. Добави първия си модул отляво!")

# --- СЛЕД ТОВА СЛОЖИ ОСТАНАЛИТЕ СИ БУТОНИ ЗА PDF И ЕТИКЕТИ ---

# --- ПОМОЩНА ФУНКЦИЯ ЗА КАНТ ЛИНИИ НА ЕТИКЕТИ ---
def draw_edge_marking(draw, x, y, w, h, side, edge_type, font):
    if not edge_type: return
    text = f" {edge_type} "
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    lw = 2 if edge_type == '0.8' else 8
    
    if side == 'top':
        draw.line([(x, y), (x+w/2-tw/2, y)], fill="black", width=lw)
        draw.line([(x+w/2+tw/2, y), (x+w, y)], fill="black", width=lw)
        draw.text((x+w/2, y), text, fill="black", font=font, anchor="mm")
    elif side == 'bottom':
        draw.line([(x, y+h), (x+w/2-tw/2, y+h)], fill="black", width=lw)
        draw.line([(x+w/2+tw/2, y+h), (x+w, y+h)], fill="black", width=lw)
        draw.text((x+w/2, y+h), text, fill="black", font=font, anchor="mm")
    elif side == 'left':
        draw.line([(x, y), (x, y+h/2-th/2)], fill="black", width=lw)
        draw.line([(x, y+h/2+th/2), (x, y+h)], fill="black", width=lw)
        draw.text((x+15, y+h/2), text, fill="black", font=font, anchor="lm")
    elif side == 'right':
        draw.line([(x+w, y), (x+w, y+h/2-th/2)], fill="black", width=lw)
        draw.line([(x+w, y+h/2+th/2), (x+w, y+h)], fill="black", width=lw)
        draw.text((x+w-15, y+h/2), text, fill="black", font=font, anchor="rm")

# --- ГЕНЕРИРАНЕ НА ЕТИКЕТИ С 44 БРОЯ НА А4 (ЧЕРНО-БЯЛО С КАНТ ЛИНИИ) ---
def generate_labels_pdf(boards_per_mat):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: 
        font_small = ImageFont.truetype(font_path, 20)
        font_text = ImageFont.truetype(font_path, 24)
        font_huge = ImageFont.truetype(font_path, 45)
        font_edge = ImageFont.truetype(font_path, 18)
    except: 
        font_small = font_text = font_huge = font_edge = ImageFont.load_default()

    labels = []
    for mat_name, boards in boards_per_mat.items():
        for board in boards:
            for p in board:
                labels.append(p)
                
    if not labels: return None

    # Точни размери за 300 DPI (1 мм = 11.811 px)
    px_per_mm = 11.811
    page_w, page_h = 2480, 3508
    cols, rows = 4, 11
    
    label_w = int(44 * px_per_mm)    # 519 px
    label_h = int(20 * px_per_mm)    # 236 px
    margin_x = int(4 * px_per_mm)    # Променено на 4 мм 
    margin_y = int(9 * px_per_mm)    # 106 px
    gap_x = int(6 * px_per_mm)       # 70 px
    gap_y = int(6.5 * px_per_mm)     # 76 px
    padding = int(3 * px_per_mm)     # 35 px отстояние от ръбовете вътре
    
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
        
        # Рамка за рязане/ориентация (по избор, правим я много бледа)
        draw.rectangle([x, y, x+label_w, y+label_h], outline="#eeeeee", width=1)
        
        d1_t = "0.8" if lbl['d1'] in ['1', '1.0'] else ("2" if lbl['d1'] in ['2', '2.0'] else "")
        d2_t = "0.8" if lbl['d2'] in ['1', '1.0'] else ("2" if lbl['d2'] in ['2', '2.0'] else "")
        sh1_t = "0.8" if lbl['sh1'] in ['1', '1.0'] else ("2" if lbl['sh1'] in ['2', '2.0'] else "")
        sh2_t = "0.8" if lbl['sh2'] in ['1', '1.0'] else ("2" if lbl['sh2'] in ['2', '2.0'] else "")
        
        draw_edge_marking(draw, x, y, label_w, label_h, 'top', d1_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'bottom', d2_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'left', sh1_t, font_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'right', sh2_t, font_edge)
            
        mod_abbr = get_module_abbrev(lbl['mod_tip'])
        top_text = f"[{lbl['mod_num']}] {mod_abbr} | {lbl['part_name']}"
        dim_text = f"{int(lbl['l'])} x {int(lbl['w'])}"
        bot_text = f"{lbl['mat'][:20]}"
        
        # Разполагаме текста съобразно 3мм padding (отстояние)
        draw.text((x + label_w/2, y + padding), top_text, fill="black", font=font_text, anchor="mt")
        draw.text((x + label_w/2, y + label_h/2), dim_text, fill="black", font=font_huge, anchor="mm")
        draw.text((x + label_w/2, y + label_h - padding), bot_text, fill="black", font=font_small, anchor="mb")
        
    pages.append(current_page)
    
    pdf_bytes = io.BytesIO()
    pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_bytes.getvalue()

# --- ГЕНЕРИРАНЕ НА РАЗКРОЙ В А4 PDF ---
def generate_cutting_plan_pdf(boards_per_mat, board_l, board_w, trim):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: 
        f_title = ImageFont.truetype(font_path, 60)
        f_part = ImageFont.truetype(font_path, 50) 
        f_dim = ImageFont.truetype(font_path, 50)  
        f_small = ImageFont.truetype(font_path, 30) 
    except: 
        f_title = f_part = f_dim = f_small = ImageFont.load_default()

    page_w, page_h = 3508, 2480 # A4 Landscape
    margin = 150
    pages = []
    
    for mat_name, boards in boards_per_mat.items():
        for idx, b_parts in enumerate(boards):
            img = Image.new('RGB', (page_w, page_h), 'white')
            draw = ImageDraw.Draw(img)
            
            draw.text((margin, margin), f"МАТЕРИАЛ: {mat_name} [2800x2070 мм] | ПЛОЧА {idx+1} от {len(boards)}", fill="black", font=f_title)
            
            draw_w = page_w - 2 * margin
            draw_h = page_h - 2 * margin - 150
            scale = min(draw_w / board_l, draw_h / board_w)
            
            act_w = board_l * scale
            act_h = board_w * scale
            sx = margin + (draw_w - act_w) / 2
            sy = margin + 150 + (draw_h - act_h) / 2
            
            draw.rectangle([sx, sy, sx+act_w, sy+act_h], outline="black", width=4)
            t_px = trim * scale
            draw.rectangle([sx+t_px, sy+t_px, sx+act_w-t_px, sy+act_h-t_px], outline="#aaaaaa", width=2)
            
            for p in b_parts:
                px = sx + (p['x'] + trim) * scale
                py = sy + (p['y'] + trim) * scale
                pw = p['l'] * scale
                ph = p['w'] * scale
                draw.rectangle([px, py, px+pw, py+ph], outline="black", width=3)
                
                d1_w = 8 if p['d1'] in ['2', '2.0'] else (3 if p['d1'] in ['1', '1.0'] else 0)
                d2_w = 8 if p['d2'] in ['2', '2.0'] else (3 if p['d2'] in ['1', '1.0'] else 0)
                sh1_w = 8 if p['sh1'] in ['2', '2.0'] else (3 if p['sh1'] in ['1', '1.0'] else 0)
                sh2_w = 8 if p['sh2'] in ['2', '2.0'] else (3 if p['sh2'] in ['1', '1.0'] else 0)
                
                if d1_w: draw.line([(px, py+ph), (px+pw, py+ph)], fill="black", width=d1_w)
                if d2_w: draw.line([(px, py), (px+pw, py)], fill="black", width=d2_w)
                if sh1_w: draw.line([(px, py), (px, py+ph)], fill="black", width=sh1_w)
                if sh2_w: draw.line([(px+pw, py), (px+pw, py+ph)], fill="black", width=sh2_w)
                
                if p['l'] <= 85 or p['w'] <= 85:
                    draw.text((px+pw/2, py+ph/2), f"{int(p['l'])}/{int(p['w'])}", fill="black", font=f_small, anchor="mm")
                else:
                    if pw > 80 and ph > 80: 
                        draw.text((px+pw/2, py+ph/2 - 35), p['name'][:15], fill="black", font=f_part, anchor="mm")
                        draw.text((px+pw/2, py+ph/2 + 35), f"{int(p['l'])}/{int(p['w'])}", fill="black", font=f_dim, anchor="mm")
                    
            pages.append(img)
            
    if pages:
        pdf_bytes = io.BytesIO()
        pages[0].save(pdf_bytes, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_bytes.getvalue()
    return None

# --- ОПТИМИЗАЦИЯ НА РАЗКРОЯ ---
def get_optimized_boards(list_for_cutting):
    kerf, trim, board_l, board_w = 8, 8, 2800, 2070
    use_l, use_w = board_l - 2*trim, board_w - 2*trim
    materials_dict = {}
    for item in list_for_cutting:
        mat = item.get('Плоскост', 'Неизвестен')
        if mat not in materials_dict: materials_dict[mat] = []
        try:
            for _ in range(int(item['Бр'])):
                materials_dict[mat].append({
                    'name': f"{item['№']} {get_abbrev(item['Детайл'])}", 
                    'l': float(item['Дължина']), 'w': float(item['Ширина']),
                    'd1': str(item.get('Д1', '')).strip(), 'd2': str(item.get('Д2', '')).strip(),
                    'sh1': str(item.get('Ш1', '')).strip(), 'sh2': str(item.get('Ш2', '')).strip(),
                    'mod_num': str(item.get('№', '')), 'mod_tip': str(item.get('Тип', '')),
                    'part_name': get_abbrev(item['Детайл']), 'mat': mat
                })
        except: pass
    
    boards_per_material = {}
    for mat_name, parts in materials_dict.items():
        parts.sort(key=lambda x: (x['w'], x['l']), reverse=True)
        boards, current_board = [], []
        curr_x, curr_y, shelf_h = 0, 0, 0
        for p in parts:
            part_l, part_w = p['l'], p['w']
            if curr_x + part_l <= use_l:
                if shelf_h == 0: shelf_h = part_w
                if curr_y + part_w <= use_w:
                    p_copy = p.copy(); p_copy.update({'x': curr_x, 'y': curr_y})
                    current_board.append(p_copy); curr_x += part_l + kerf
                else:
                    boards.append(current_board)
                    p_copy = p.copy(); p_copy.update({'x': 0, 'y': 0})
                    current_board = [p_copy]; curr_x = part_l + kerf; curr_y = 0; shelf_h = part_w
            else:
                curr_x = 0; curr_y += shelf_h + kerf; shelf_h = part_w
                if curr_y + part_w <= use_w:
                    p_copy = p.copy(); p_copy.update({'x': curr_x, 'y': curr_y})
                    current_board.append(p_copy); curr_x += part_l + kerf
                else:
                    boards.append(current_board)
                    p_copy = p.copy(); p_copy.update({'x': 0, 'y': 0})
                    current_board = [p_copy]; curr_x = part_l + kerf; curr_y = 0; shelf_h = part_w
        if current_board: boards.append(current_board)
        boards_per_material[mat_name] = boards
    return boards_per_material, board_l, board_w, trim

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
                    pdf_data = generate_technical_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka)
                    if pdf_data:
                        st.download_button(label="📥 ИЗТЕГЛИ PDF", data=pdf_data, file_name="Vitya_M_Чертежи.pdf", mime="application/pdf")
                        
    with col_b2:
        if st.button("🏷️ Свали ЕТИКЕТИ (А4)"):
            if not st.session_state.order_list:
                st.warning("Добави детайли за етикетите!")
            else:
                with st.spinner("Генериране на етикети..."):
                    boards_per_mat, _, _, _ = get_optimized_boards(st.session_state.order_list)
                    labels_pdf = generate_labels_pdf(boards_per_mat)
                    if labels_pdf:
                        st.download_button(label="📥 ИЗТЕГЛИ ЕТИКЕТИ", data=labels_pdf, file_name="Vitya_M_Етикети.pdf", mime="application/pdf")

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
                    st.download_button(label="📥 ИЗТЕГЛИ РАЗКРОЙ", data=cut_pdf, file_name="Vitya_M_Разкрой.pdf", mime="application/pdf")
                    
    if st.button("Генерирай 2D разкрой на екрана"):
        if not st.session_state.order_list: st.warning("Добави детайли, за да генерираш разкрой!")
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
                        
                        if p['l'] <= 85 or p['w'] <= 85:
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2}" font-size="30" fill="black" text-anchor="middle" dominant-baseline="middle" font-weight="bold">{int(p["l"])}/{int(p["w"])}</text>'
                        else:
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2 - 25}" font-size="45" fill="black" text-anchor="middle" dominant-baseline="middle" font-weight="bold">{p["name"]}</text>'
                            svg += f'<text x="{px + pl/2}" y="{py + pw/2 + 35}" font-size="50" fill="black" text-anchor="middle" dominant-baseline="middle">{int(p["l"])}/{int(p["w"])}</text>'
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
                    if val in ['1', '2', '1.0', '2.0']:
                        thickness = "2мм" if val.startswith('2') else "0.8мм"
                        meters = (dim * count) / 1000.0
                        if meters > 0:
                            key = (mat, thickness)
                            edge_dict[key] = edge_dict.get(key, 0) + meters
            except: pass
        
        total_edge_cost = 0.0
        if edge_dict:
            col_e1, col_e2 = st.columns([1, 1])
            with col_e2: edge_price_per_m = st.number_input("€/л.м. Кант", value=1.0)
            with col_e1:
                for (mat, thick), meters in edge_dict.items():
                    meters_with_margin = meters * 1.10
                    cost = meters_with_margin * edge_price_per_m
                    total_edge_cost += cost
                    st.write(f"- **{mat} ({thick}):** {meters_with_margin:.1f} л.м.")
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
        with col_ext1: plot_cost = st.number_input("Плот (Общо) €", value=100.0)
        with col_ext2: grub_cost = st.number_input("Гръб (Общо) €", value=80.0)
        total_extra_mats = total_hw_cost + plot_cost + grub_cost

        st.markdown("##### 5. Твърди разходи, Труд и Услуги")
        col_fixed, col_labor = st.columns(2)
        with col_fixed:
            osigurovki = st.number_input("Осигуровки (на месец) €", value=450)
            naem = st.number_input("Наем (на месец) €", value=400)
            tok = st.number_input("Ток/Консумативи €", value=100)
            bus = st.number_input("Бус €", value=100)
            schetovodstvo = st.number_input("Счетоводство €", value=80)
        with col_labor:
            project_days = st.number_input("Дни за този проект:", value=15, min_value=1)
            nadnici = st.number_input("Надници (общо/ден) €", value=225)
            transport = st.number_input("Транспорт €", value=0)
            komandirovachni = st.number_input("Командировъчни €", value=0)
            hamal = st.number_input("Хамалски услуги €", value=0)

        st.markdown("##### 6. Буфери и Печалба")
        col_buf1, col_buf2 = st.columns(2)
        with col_buf1: nepredvideni_pct = st.number_input("Непредвидени разходи (%)", value=15)
        with col_buf2: pechalba_pct = st.number_input("Печалба (%)", value=25)

        rent_cons_cost = (project_days / 15.0) * 300.0
        other_monthly = osigurovki + bus + schetovodstvo
        other_fixed_cost = (other_monthly / 21.0) * project_days
        total_fixed_project = rent_cons_cost + other_fixed_cost
        
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
