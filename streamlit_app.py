import streamlit as st
import pandas as pd
import os
from PIL import Image

# Настройки на страницата
st.set_page_config(page_title="SMART CUT: Витя-М", layout="wide")

st.title("🛠️ SMART CUT")
st.markdown("<p style='font-size: 18px; color: gray; margin-top: -20px;'><i>оптимизирай умно</i></p>", unsafe_allow_html=True)
st.info("Добавено: Професионален финансов модул с калкулация на дневни разходи, труд и процент печалба.")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

def add_item(modul, detail, count, l, w, kant, material, flader, note=""):
    return {
        "Модул": modul, "Детайл": detail, "Брой": count, "L": l, "W": w, 
        "Кант": kant, "Материал": material, "Фладер": flader, "Забележка": note
    }

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    st.markdown("---")
    st.header("🎨 Материали и Фладер")
    
    st.markdown("**1. Корпус (Страници, Дъна, Рафтове)**")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло гладко 18мм")
    fl_korpus = st.checkbox("Има фладер - Корпус", value=False)
    val_fl_korpus = "Да" if fl_korpus else "Няма"
    
    st.markdown("**2. Лице (Врати, Чела)**")
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    fl_lice = st.checkbox("Има фладер - Лице", value=True)
    val_fl_lice = "Да" if fl_lice else "Няма"
    
    st.markdown("**3. Чекмеджета (Царги)**")
    mat_chekm = st.text_input("Декор Чекмеджета:", value="Бяло гладко 18мм")
    fl_chekm = st.checkbox("Има фладер - Чекмеджета", value=False)
    val_fl_chekm = "Да" if fl_chekm else "Няма"
    
    st.markdown("**4. Гръб (Фазер)**")
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
        "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", 
        "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐"
    }
    
    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons[x]} {x}")
    
    try:
        if os.path.exists("sketches.jpg"):
            img = Image.open("sketches.jpg")
            w_img, h_img = img.size
            step = w_img / 7 
            cabinet_index = {"Стандартен Долен": 0, "Горен Шкаф": 1, "Шкаф Мивка": 2, "Шкаф 3 Чекмеджета": 3, "Шкаф Бутилки 15см": 4, "Шкаф за Фурна": 5, "Глух Ъгъл (Долен)": 6}
            idx = cabinet_index[tip]
            cropped_img = img.crop((idx * step, 0, (idx + 1) * step, h_img))
            st.image(cropped_img, use_container_width=True)
    except: pass
    
    name = st.text_input("Име/№ на модула", value=tip)
    
    default_w = 600
    if tip == "Шкаф Бутилки 15см": default_w = 150
    elif tip == "Глух Ъгъл (Долен)": default_w = 1000
        
    w = st.number_input("Ширина (W) на корпуса (мм)", value=default_w)
    
    if tip == "Горен Шкаф":
        h = st.number_input("Височина (H) в мм", value=720)
        d = st.number_input("Дълбочина (D) в мм", value=300)
        vrati_broi = st.radio("Брой врати:", [1, 2], index=1, horizontal=True)
        vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални (Клапващи)"], horizontal=True)
    else:
        default_d = 550 if tip == "Шкаф Мивка" else 520
        d = st.number_input("Дълбочина (D) страници (мм)", value=default_d)
        
        if tip == "Шкаф 3 Чекмеджета":
            runner_len = st.number_input("Дължина водач Blum (мм)", value=500, step=50)
            
        elif tip == "Глух Ъгъл (Долен)":
            st.markdown("##### Настройки за лицето:")
            w_vrata_input = st.number_input("Ширина Врата (мм)", value=400)
            w_gluha_input = st.number_input("Ширина Глуха част (мм)", value=600)

    if st.button("➕ Добави към списъка"):
        new_items = []
        otstyp_fazer = 4 
        h_stranica = 742 
        h_shkaf_korpus = h_stranica + deb 
        h_vrata_standart = h_shkaf_korpus - fuga_obshto
        
        if tip == "Горен Шкаф":
            new_items.append(add_item(name, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus))
            new_items.append(add_item(name, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus))
            new_items.append(add_item(name, "Гръб (Фазер)", 1, h - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))
            if vrati_orientacia == "Вертикални":
                h_vrata = h - fuga_obshto
                w_vrata = w - fuga_obshto if vrati_broi == 1 else (w/2) - (fuga_obshto/2)
            else:
                w_vrata = w - fuga_obshto
                h_vrata = h - fuga_obshto if vrati_broi == 1 else (h/2) - (fuga_obshto/2)
            new_items.append(add_item(name, "Врата", vrati_broi, h_vrata, w_vrata, "4 страни", mat_lice, val_fl_lice))
            
        else:
            w_vrata_dvoina = (w/2) - (fuga_obshto/2)
            w_vrata_edinichna = w - fuga_obshto

            if tip == "Шкаф Мивка":
                new_items.append(add_item(name, "Дъно", 1, w, 480, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Врата", 2, h_vrata_standart, w_vrata_dvoina, "4 страни", mat_lice, val_fl_lice))
                
            elif tip == "Стандартен Долен":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Врата", 2, h_vrata_standart, w_vrata_dvoina, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))
                
            elif tip == "Шкаф Бутилки 15см":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Врата", 1, h_vrata_standart, w_vrata_edinichna, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))
                
            elif tip == "Глух Ъгъл (Долен)":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Врата", 1, h_vrata_standart, w_vrata_input - fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, "Глуха част (Чело)", 1, h_vrata_standart, w_gluha_input - fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))

            elif tip == "Шкаф за Фурна":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Чело чекмедже", 1, 157, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_items.append(add_item(name, "Царги чекм.", 2, w - (2*deb) - 49, 70, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм.", 2, 490, 85, "2д", mat_chekm, val_fl_chekm))
                
            elif tip == "Шкаф 3 Чекмеджета":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))
                block_note = "В БЛОК" if fl_lice else ""
                new_items.append(add_item(name, "Чело горно", 1, 180-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note))
                new_items.append(add_item(name, "Чело средно", 1, 250-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note))
                new_items.append(add_item(name, "Чело долно", 1, 330-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note))
                w_cargi = w - (2*deb) - 49
                l_stranici_chek = runner_len - 10
                new_items.append(add_item(name, "Царги чекм. 1", 2, w_cargi, 80, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм. 1", 2, l_stranici_chek, 80+15, "2д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Царги чекм. 2", 2, w_cargi, 160, "1д", mat_che
