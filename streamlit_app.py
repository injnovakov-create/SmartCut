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
    if "рафт твърд" in d: return "РфтТв"
    if "рафт подвижен" in d: return "РфтПод"
    if "рафт" in d and "фурна" not in d: return "Рфт"
    if "рафт" in d and "фурна" in d: return "РфтФур"
    if "врата долна" in d: return "ВрДол"
    if "врата горна" in d: return "ВрГор"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело горно" in d: return "ЧГ"
    if "чело средно" in d: return "ЧС"
    if "чело долно" in d: return "ЧД"
    if "чело чекмедже" in d: return "ЧЧ"
    if "чело" in d: return "Чело"
    if "царги чекм" in d: return "Цч"
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
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

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
    
    # Категоризация
    cat_choice = st.radio("Избери категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)

    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {
            "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Шкаф Мивка": "🚰", 
            "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", "Шкаф за Фурна": "🍳", 
            "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"
        }
    else:
        icons = {
            "Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"
        }

    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    name = st.text_input("Име/№ на модула", value=tip)
    
    if tip == "Дублираща страница долен":
        h = st.number_input("Височина (H) мм", value=860)
        d = st.number_input("Дълбочина (D) мм", value=580)
        w = deb
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Нестандартен детайл")
        colA, colB, colC = st.columns(3)
        h = custom_l = colA.number_input("Дължина (L) мм", value=600)
        d = custom_w = colB.number_input("Ширина (W) мм", value=300)
        w = deb
        custom_count = colC.number_input("Брой", value=1, min_value=1)
        colD, colE = st.columns(2)
        custom_kant = colD.selectbox("Кант", ["Без", "1д", "2д", "1д+1к", "1д+2к", "2д+1к", "4 страни", "2д+2к"], index=6)
        custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер"])
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) на корпуса (мм)", value=600)
        h_korpus = st.number_input("Височина на корпуса без крака (H) мм", value=2040)
        d = st.number_input("Дълбочина (D) страници (мм)", value=550)
        split_doors = st.checkbox("Две врати по височина (Долна + Горна)?", value=True)
        if split_doors:
            lower_door_h = st.number_input("Височина на долната врата (мм)", value=718)
        vrati_broi = st.radio("Брой врати на ред (лява/дясна):", [1, 2], index=0 if w <= 500 else 1, horizontal=True)
        h = h_korpus + kraka 
    else:
        default_w = 150 if tip == "Шкаф Бутилки 15см" else (1000 if "Глух" in tip else 600)
        w = st.number_input("Ширина (W) на корпуса (мм)", value=default_w)
        
        if "Горен" in tip:
            h = st.number_input("Височина (H) в мм", value=720)
            d = st.number_input("Дълбочина (D) в мм", value=300)
            if tip == "Горен Шкаф":
                vrati_broi = st.radio("Брой врати:", [1, 2], index=1, horizontal=True)
                vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални (Клапващи)"], horizontal=True)
            elif tip == "Глух Ъгъл (Горен)":
                st.markdown("##### Настройки за лицето:")
                w_vrata_input = st.number_input("Ширина Врата (мм)", value=400)
                w_gluha_input = st.number_input("Ширина Глуха част (мм)", value=300)
        else:
            d = st.number_input("Дълбочина (D) страници (мм)", value=(550 if tip == "Шкаф Мивка" else 520))
            if tip == "Шкаф 3 Чекмеджета": runner_len = st.number_input("Дължина водач (мм)", value=500, step=50)
            elif tip == "Шкаф за Фурна": runner_len = 500
            elif tip == "Глух Ъгъл (Долен)":
                st.markdown("##### Настройки за лицето:")
                w_vrata_input = st.number_input("Ширина Врата (мм)", value=400)
                w_gluha_input = st.number_input("Ширина Глуха част (мм)", value=600)
            
            h = 742 + kraka + 38 
            
            if tip in ["Стандартен Долен", "Шкаф Мивка"]:
                def_vrati = 0 if w <= 500 else 1
                vrati_broi = st.radio("Брой врати:", [1, 2], index=def_vrati, horizontal=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Добави към списъка"):
        new_items = []
        new_hw = []
        otstyp_fazer = 4; h_stranica = 742; h_shkaf_korpus = h_stranica + deb; h_vrata_standart = h_shkaf_korpus - fuga_obshto
        
        st.session_state.modules_meta.append({"№": name, "Тип": tip, "W": w, "H": h, "D": d})

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Шкаф Бутилки 15см", "Глух Ъгъл (Долен)", "Шкаф за Фурна", "Шкаф 3 Чекмеджета", "Шкаф Колона"]:
            hw_legs = 5 if w > 900 else 4
            new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": hw_legs})

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Горен Шкаф"]:
            h_door_hw = h_vrata_standart if tip != "Горен Шкаф" else (h - fuga_obshto if vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto)))
            hw_hinges = calculate_hinges(h_door_hw) * vrati_broi
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": hw_hinges})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": vrati_broi})
            
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
            
        if tip == "Шкаф 3 Чекмеджета":
            new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": 3})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 3})
        elif tip == "Шкаф за Фурна":
            new_hw.append({"№": name, "Артикул": "Комплект водачи за чекмедже", "Брой": 1})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 1})

        if "Горен" in tip:
            new_hw.append({"№": name, "Артикул": "Окачвачи за горен шкаф", "Брой": 2})
            new_hw.append({"№": name, "Артикул": "LED осветление (л.м.)", "Брой": w / 1000.0})

        if tip == "Дублираща страница долен":
            new_items.append(add_item(name, tip, "Дублираща страница", 1, h, d, "4 страни", mat_lice, val_fl_lice))
        elif tip == "Нестандартен":
            m_choice = mat_korpus; f_choice = val_fl_korpus
            if custom_mat_type == "Лице": m_choice = mat_lice; f_choice = val_fl_lice
            elif custom_mat_type == "Чекмеджета": m_choice = mat_chekm; f_choice = val_fl_chekm
            elif custom_mat_type == "Фазер": m_choice = mat_fazer; f_choice = "Няма"
            new_items.append(add_item(name, tip, custom_detail, custom_count, custom_l, custom_w, custom_kant, m_choice, f_choice))
        elif tip == "Шкаф Колона":
            new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": 12})
            w_izbrana = int((w/2) - fuga_obshto) if vrati_broi == 2 else int(w - fuga_obshto)
            new_items.extend([
                add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h_korpus - deb, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Рафт твърд", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Рафт подвижен", 3, w-(2*deb), d-10, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
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
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Чело чекмедже", 1, 157, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice), add_item(name, tip, "Царги чекм.", 2, cargi_w, 70, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Страници чекм.", 2, runner_len - 10, 85, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Дъно чекмедже", 1, duno_l, duno_w, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Шкаф 3 Чекмеджета":
                block_note = "В БЛОК" if val_fl_lice == "Да" else ""
                cargi_w = w - (2*deb) - 49
                duno_w = cargi_w + 12
                duno_l = runner_len - 13
                new_items.extend([
                    add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, tip, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                    add_item(name, tip, "Чело горно", 1, 180-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, tip, "Чело средно", 1, 250-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, tip, "Чело долно", 1, 330-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, tip, "Царги чекм. 1", 2, cargi_w, 80, "1д", mat_chekm, val_fl_chekm), add_item(name, tip, "Страници чекм. 1", 2, runner_len - 10, 80+15, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Царги чекм. 2", 2, cargi_w, 160, "1д", mat_chekm, val_fl_chekm), add_item(name, tip, "Страници чекм. 2", 2, runner_len - 10, 160+15, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Царги чекм. 3", 2, cargi_w, 200, "1д", mat_chekm, val_fl_chekm), add_item(name, tip, "Страници чекм. 3", 2, runner_len - 10, 200+15, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, tip, "Дъно чекмедже", 3, duno_l, duno_w, "Без", mat_fazer, "Няма")
                ])

        st.session_state.order_list.extend(new_items)
        st.session_state.hardware_list.extend(new_hw)
        st.success(f"Модул {name} е добавен!")
        st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        cols_order = ["Плоскост", "№", "Тип", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[[c for c in cols_order if c in df.columns]]
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=350, key="editor")
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

# --- ГЕНЕРИРАНЕ НА PDF С ЧЕРТЕЖИ ---
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
        lower_types = ["Долен", "Мивка", "Чекмеджета", "Фурна", "Бутилки", "Колона"]
        
        leg_h_px = 0
        if any(t in tip for t in lower_types):
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
        has_split_doors = False
        ld_h = 0
        for p in parts:
            if "врата" in str(p['Детайл']).lower():
                vrati_count = int(p['Бр'])
            if "врата долна" in str(p['Детайл']).lower():
                has_split_doors = True
                ld_h = float(p['Дължина'])

        if "3 Чекмеджета" in tip:
            d1_y = start_y + (180 * scale)
            draw.line([(start_x, d1_y), (start_x + w_px, d1_y)], fill="#333333", width=6)
            d2_y = d1_y + (250 * scale)
            draw.line([(start_x, d2_y), (start_x + w_px, d2_y)], fill="#333333", width=6)
            draw.text((start_x + w_px + 20, start_y + 70*scale), "180", fill="black", font=font_dim)
            draw.text((start_x + w_px + 20, d1_y + 100*scale), "250", fill="black", font=font_dim)
            draw.text((start_x + w_px + 20, d2_y + 120*scale), "330", fill="black", font=font_dim)
            
        elif "Фурна" in tip:
            d_y = start_y + h_px - leg_h_px - (157 * scale)
            draw.line([(start_x, d_y), (start_x + w_px, d_y)], fill="#333333", width=6)
            
        elif has_split_doors and "Колона" in tip:
            split_y = start_y + h_px - leg_h_px - (ld_h * scale)
            draw.line([(start_x, split_y), (start_x + w_px, split_y)], fill="black", width=4)

        if vrati_count == 2 and "Колона" not in tip:
            draw.line([(start_x + w_px/2, start_y), (start_x + w_px/2, start_y + h_px - leg_h_px)], fill="black", width=3)
        elif vrati_count == 2 and "Колона" in tip:
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
            if p.get('Д1'): kant_str += f"Д1({p['Д1']}) "
            if p.get('Д2'): kant_str += f"Д2({p['Д2']}) "
            if p.get('Ш1'): kant_str += f"Ш1({p['Ш1']}) "
            if p.get('Ш2'): kant_str += f"Ш2({p['Ш2']}) "
            
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

# --- ГЕНЕРИРАНЕ НА ЕТИКЕТИ С 44 БРОЯ НА А4 ---
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

    px_per_mm = 11.811
    page_w, page_h = 2480, 3508
    cols, rows = 4, 11
    
    label_w = int(44 * px_per_mm)    
    label_h = int(20 * px_per_mm)    
    margin_x = int(4 * px_per_mm)    
    margin_y = int(9 * px_per_mm)    
    gap_x = int(6 * px_per_mm)       
    gap_y = int(6.5 * px_per_mm)     
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
                    pdf_data = generate_technical_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka_h)
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
