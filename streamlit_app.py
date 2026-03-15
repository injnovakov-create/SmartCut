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

# --- НОВА ЛОГИКА ЗА ЗАПИС С 4 КОЛОНИ ЗА КАНТ ---
def add_item(modul, detail, count, l, w, kant_str, material, flader, note=""):
    # Проверка дали детайлът е лице, за да сложи дебел кант (2) или тънък (1)
    thick = 2 if any(x in str(detail).lower() for x in ["врата", "чело", "дублираща"]) else 1
    d1 = d2 = sh1 = sh2 = ""
    
    k = str(kant_str).lower()
    if "1д" in k: d1 = thick
    if "2д" in k or "4" in k: d1 = thick; d2 = thick
    if "1к" in k or "1ш" in k: sh1 = thick
    if "2к" in k or "2ш" in k or "4" in k: sh1 = thick; sh2 = thick
    
    return {
        "Модул": modul, "Детайл": detail, "Брой": count, "L": l, "W": w, 
        "Д1": d1, "Д2": d2, "Ш1": sh1, "Ш2": sh2, 
        "Материал": material, "Фладер": flader, "Забележка": note
    }

def get_abbrev(detail_name):
    d = str(detail_name).lower()
    if "дублираща" in d: return "ДублСтр"
    if "страница" in d and "чекм" not in d: return "Стр"
    if "дъно/таван" in d: return "Д/Т"
    if "дъно" in d: return "Дън"
    if "бленда" in d: return "Бл"
    if "рафт" in d and "фурна" not in d: return "Рфт"
    if "рафт" in d and "фурна" in d: return "РфтФур"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело горно" in d: return "ЧГ"
    if "чело средно" in d: return "ЧС"
    if "чело долно" in d: return "ЧД"
    if "чело чекмедже" in d: return "ЧЧ"
    if "глуха част" in d: return "ГлЧ"
    if "царги чекм" in d:
        num = ''.join(filter(str.isdigit, d))
        return f"Цч{num}" if num else "Цч"
    if "страници чекм" in d:
        num = ''.join(filter(str.isdigit, d))
        return f"Сч{num}" if num else "Сч"
    return detail_name[:5].capitalize()

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
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    icons = {
        "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Шкаф Мивка": "🚰", 
        "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", "Шкаф за Фурна": "🍳", 
        "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐", 
        "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"
    }
    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    
    cabinet_index = {"Стандартен Долен": 0, "Горен Шкаф": 1, "Шкаф Мивка": 2, "Шкаф 3 Чекмеджета": 3, "Шкаф Бутилки 15см": 4, "Шкаф за Фурна": 5, "Глух Ъгъл (Долен)": 6}
    if tip in cabinet_index:
        try:
            if os.path.exists("sketches.jpg"):
                img = Image.open("sketches.jpg")
                w_img, h_img = img.size
                step = w_img / 7 
                idx = cabinet_index[tip]
                cropped_img = img.crop((idx * step, 0, (idx + 1) * step, h_img))
                st.image(cropped_img, use_container_width=True)
        except: pass
    
    name = st.text_input("Име/№ на модула", value=tip)
    
    if tip == "Дублираща страница долен":
        custom_h = st.number_input("Височина (H) мм", value=860)
        custom_d = st.number_input("Ширина (W) мм", value=580)
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Нестандартен детайл")
        colA, colB, colC = st.columns(3)
        custom_l = colA.number_input("Дължина (L) мм", value=600)
        custom_w = colB.number_input("Ширина (W) мм", value=300)
        custom_count = colC.number_input("Брой", value=1, min_value=1)
        colD, colE = st.columns(2)
        custom_kant = colD.selectbox("Кант", ["Без", "1д", "2д", "1д+1к", "1д+2к", "2д+1к", "4 страни", "2д+2к"], index=6)
        custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер"])
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
            if tip == "Шкаф 3 Чекмеджета": runner_len = st.number_input("Дължина водач Blum (мм)", value=500, step=50)
            elif tip == "Глух Ъгъл (Долен)":
                st.markdown("##### Настройки за лицето:")
                w_vrata_input = st.number_input("Ширина Врата (мм)", value=400)
                w_gluha_input = st.number_input("Ширина Глуха част (мм)", value=600)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Добави към списъка"):
        new_items = []
        otstyp_fazer = 4; h_stranica = 742; h_shkaf_korpus = h_stranica + deb; h_vrata_standart = h_shkaf_korpus - fuga_obshto
        
        if tip == "Дублираща страница долен":
            new_items.append(add_item(name, "Дублираща страница", 1, custom_h, custom_d, "4 страни", mat_lice, val_fl_lice))
            
        elif tip == "Нестандартен":
            m_choice = mat_korpus; f_choice = val_fl_korpus
            if custom_mat_type == "Лице": m_choice = mat_lice; f_choice = val_fl_lice
            elif custom_mat_type == "Чекмеджета": m_choice = mat_chekm; f_choice = val_fl_chekm
            elif custom_mat_type == "Фазер": m_choice = mat_fazer; f_choice = "Няма"
            new_items.append(add_item(name, custom_detail, custom_count, custom_l, custom_w, custom_kant, m_choice, f_choice))
            
        elif tip == "Горен Шкаф":
            new_items.extend([
                add_item(name, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
            ])
            h_vrata = h - fuga_obshto if vrati_orientacia == "Вертикални" else (h - fuga_obshto if vrati_broi == 1 else int((h/2) - fuga_obshto))
            w_vrata = w - fuga_obshto if vrati_orientacia != "Вертикални" else (w - fuga_obshto if vrati_broi == 1 else int((w/2) - fuga_obshto))
            new_items.append(add_item(name, "Врата", vrati_broi, h_vrata, w_vrata, "4 страни", mat_lice, val_fl_lice))
            
        elif tip == "Глух Ъгъл (Горен)":
            new_items.extend([
                add_item(name, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                add_item(name, "Врата", 1, h - fuga_obshto, int(w_vrata_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                add_item(name, "Глуха част (Чело)", 1, h - fuga_obshto, int(w_gluha_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice)
            ])
            
        else:
            w_vrata_dvoina, w_vrata_edinichna = int((w/2) - fuga_obshto), w - fuga_obshto
            if tip == "Шкаф Мивка":
                new_items.extend([
                    add_item(name, "Дъно", 1, w, 480, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Врата", 2, h_vrata_standart, w_vrata_dvoina, "4 страни", mat_lice, val_fl_lice)
                ])
            elif tip == "Стандартен Долен":
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Врата", 2, h_vrata_standart, w_vrata_dvoina, "4 страни", mat_lice, val_fl_lice), add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Шкаф Бутилки 15см":
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Врата", 1, h_vrata_standart, w_vrata_edinichna, "4 страни", mat_lice, val_fl_lice),
                    add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
                ])
            elif tip == "Глух Ъгъл (Долен)":
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Врата", 1, h_vrata_standart, int(w_vrata_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                    add_item(name, "Глуха част (Чело)", 1, h_vrata_standart, int(w_gluha_input - fuga_obshto), "4 страни", mat_lice, val_fl_lice),
                    add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
