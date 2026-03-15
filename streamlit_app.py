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

# --- ЛОГИКА ЗА ЗАПИС ТОЧНО КАТО В EXCEL ---
def add_item(modul, detail, count, l, w, kant_str, material, flader, note=""):
    thick = 2 if any(x in str(detail).lower() for x in ["врата", "чело", "дублираща"]) else 1
    d1 = d2 = sh1 = sh2 = ""
    
    k = str(kant_str).lower()
    if "1д" in k: d1 = thick
    if "2д" in k or "4" in k: d1 = thick; d2 = thick
    if "1к" in k or "1ш" in k: sh1 = thick
    if "2к" in k or "2ш" in k or "4" in k: sh1 = thick; sh2 = thick
    
    return {
        "Плоскост": material, "№": modul, "Детайл": detail, "Дължина": l, "Ширина": w, 
        "Фладер": flader, "Бр": count, "Д1": d1, "Д2": d2, "Ш1": sh1, "Ш2": sh2, "Забележка": note
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
            
            # --- ЛОГИКА ЗА ДОЛНИТЕ ВРАТИ ---
            if tip in ["Стандартен Долен", "Шкаф Мивка"]:
                def_vrati = 0 if w <= 500 else 1
                vrati_broi = st.radio("Брой врати:", [1, 2], index=def_vrati, horizontal=True)

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
                w_izbrana = w_vrata_edinichna if vrati_broi == 1 else w_vrata_dvoina
                new_items.extend([
                    add_item(name, "Дъно", 1, w, 480, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Врата", vrati_broi, h_vrata_standart, w_izbrana, "4 страни", mat_lice, val_fl_lice)
                ])
            elif tip == "Стандартен Долен":
                w_izbrana = w_vrata_edinichna if vrati_broi == 1 else w_vrata_dvoina
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Рафт", 1, w-(2*deb), d - 10, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Врата", vrati_broi, h_vrata_standart, w_izbrana, "4 страни", mat_lice, val_fl_lice), add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма")
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
                ])
            elif tip == "Шкаф за Фурна":
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Рафт (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Чело чекмедже", 1, 157, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice), add_item(name, "Царги чекм.", 2, w - (2*deb) - 49, 70, "1д", mat_chekm, val_fl_chekm),
                    add_item(name, "Страници чекм.", 2, 490, 85, "2д", mat_chekm, val_fl_chekm)
                ])
            elif tip == "Шкаф 3 Чекмеджета":
                block_note = "В БЛОК" if val_fl_lice == "Да" else ""
                new_items.extend([
                    add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus), add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                    add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus), add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"),
                    add_item(name, "Чело горно", 1, 180-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, "Чело средно", 1, 250-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, "Чело долно", 1, 330-fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice, block_note),
                    add_item(name, "Царги чекм. 1", 2, w - (2*deb) - 49, 80, "1д", mat_chekm, val_fl_chekm), add_item(name, "Страници чекм. 1", 2, runner_len - 10, 80+15, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, "Царги чекм. 2", 2, w - (2*deb) - 49, 160, "1д", mat_chekm, val_fl_chekm), add_item(name, "Страници чекм. 2", 2, runner_len - 10, 160+15, "2д", mat_chekm, val_fl_chekm),
                    add_item(name, "Царги чекм. 3", 2, w - (2*deb) - 49, 200, "1д", mat_chekm, val_fl_chekm), add_item(name, "Страници чекм. 3", 2, runner_len - 10, 200+15, "2д", mat_chekm, val_fl_chekm)
                ])

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")
        st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        cols_order = ["Плоскост", "№", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2", "Забележка"]
        df = df[cols_order]
        
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=400, key="editor")
        st.session_state.order_list = edited_df.to_dict('records')
        
        # --- ЕКСПОРТ КЪМ EXCEL ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Разкрой')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Свали в Excel (.xlsx)", 
            data=excel_data, 
            file_name="razkroi_vitya_kuhni.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Списъкът е празен. Добави първия си модул отляво!")

# --- ПОДГОТОВКА ЗА ЧЕРТАЕНЕ С НОВИТЕ КОЛОНИ ---
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
                    'l': float(item['Дължина']), 
                    'w': float(item['Ширина']),
                    'd1': str(item.get('Д1', '')).strip(),
                    'd2': str(item.get('Д2', '')).strip(),
                    'sh1': str(item.get('Ш1', '')).strip(),
                    'sh2': str(item.get('Ш2', '')).strip()
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
                    current_board.append({'x': curr_x, 'y': curr_y, 'l': part_l, 'w': part_w, 'name': p['name'], 'd1': p['d1'], 'd2': p['d2'], 'sh1': p['sh1'], 'sh2': p['sh2']})
                    curr_x += part_l + kerf
                else:
                    boards.append(current_board); current_board = [{'x': 0, 'y': 0, 'l': part_l, 'w': part_w, 'name': p['name'], 'd1': p['d1'], 'd2': p['d2'], 'sh1': p['sh1'], 'sh2': p['sh2']}]
                    curr_x = part_l + kerf; curr_y = 0; shelf_h = part_w
            else:
                curr_x = 0; curr_y += shelf_h + kerf; shelf_h = part_w
                if curr_y + part_w <= use_w:
                    current_board.append({'x': curr_x, 'y': curr_y, 'l': part_l, 'w': part_w, 'name': p['name'], 'd1': p['d1'], 'd2': p['d2'], 'sh1': p['sh1'], 'sh2': p['sh2']})
                    curr_x += part_l + kerf
                else:
                    boards.append(current_board); current_board = [{'x': 0, 'y': 0, 'l': part_l, 'w': part_w, 'name': p['name'], 'd1': p['d1'], 'd2': p['d2'], 'sh1': p['sh1'], 'sh2': p['sh2']}]
                    curr_x = part_l + kerf; curr_y = 0; shelf_h = part_w
        if current_board: boards.append(current_board)
        boards_per_material[mat_name] = boards
        
    return boards_per_material, board_l, board_w, trim

def generate_boards_jpeg(boards_per_mat, board_l, board_w, trim):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: font = ImageFont.truetype(font_path, 35)
    except: font = ImageFont.load_default()

    images_bytes = {}
    for mat_name, boards in boards_per_mat.items():
        final_image = Image.new('RGB', (board_l, board_w * len(boards) + 50 * len(boards)), "white")
        draw = ImageDraw.Draw(final_image)

        for idx, b_parts in enumerate(boards):
            board_y_offset = idx * (board_w + 50)
            use_trim_y = trim + board_y_offset
            draw.rectangle([(trim, use_trim_y), (board_l - trim, board_w + board_y_offset - trim)], outline="red", width=5)
            
            for p in b_parts:
                px, py, pl, pw = p['x'] + trim, p['y'] + use_trim_y, p['l'], p['w']
                
                ew_1 = 12 if p['d1'] in ['2', '2.0'] else (6 if p['d1'] in ['1', '1.0'] else 0)
                ew_2 = 12 if p['d2'] in ['2', '2.0'] else (6 if p['d2'] in ['1', '1.0'] else 0)
                eh_1 = 12 if p['sh1'] in ['2', '2.0'] else (6 if p['sh1'] in ['1', '1.0'] else 0)
                eh_2 = 12 if p['sh2'] in ['2', '2.0'] else (6 if p['sh2'] in ['1', '1.0'] else 0)
                
                draw.rectangle([(px, py), (px+pl, py+pw)], outline="black", width=2)
                
                if ew_1: draw.line([(px, py+pw), (px+pl, py+pw)], fill="black", width=ew_1)
                if ew_2: draw.line([(px, py), (px+pl, py)], fill="black", width=ew_2)
                if eh_1: draw.line([(px, py), (px, py+pw)], fill="black", width=eh_1)
                if eh_2: draw.line([(px+pl, py), (px+pl, py+pw)], fill="black", width=eh_2)

                text_name = p['name'][:15]
                text_size = f"{int(pl)}/{int(pw)}"
                
                try:
                    bbox_n = draw.textbbox((0, 0), text_name, font=font); w_n, h_n = bbox_n[2] - bbox_n[0], bbox_n[3] - bbox_n[1]
                    bbox_s = draw.textbbox((0, 0), text_size, font=font); w_s, h_s = bbox_s[2] - bbox_s[0], bbox_s[3] - bbox_s[1]
                    if pl > max(w_n, w_s) + 10 and pw > h_n + h_s + 15:
                        draw.text((px + pl/2 - w_n/2, py + pw/2 - h_n - 5), text_name, fill="black", font=font)
                        draw.text((px + pl/2 - w_s/2, py + pw/2 + 5), text_size, fill="black", font=font)
                except:
                    draw.text((px + 10, py + 10), f"{text_name}\n{text_size}", fill="black", font=font)

        img_byte_arr = io.BytesIO()
        final_image.save(img_byte_arr, format='JPEG')
        images_bytes[mat_name] = img_byte_arr.getvalue()
    return images_bytes

# --- ВИЗУАЛИЗАЦИЯ НА РАЗКРОЯ ---
st.markdown("---")
st.subheader("✂️ Визуализация на разкроя")

boards_per_mat, board_l, board_w, trim = get_optimized_boards(st.session_state.order_list)

if st.button("Генерирай чертеж на плочите"):
    if not st.session_state.order_list: st.warning("Добави детайли, за да генерираш разкрой!")
    else:
        for mat_name, boards in boards_per_mat.items():
            st.markdown(f"#### 🪵 Материал: {mat_name}")
            st.success(f"Нужни плочи: {len(boards)} бр.")
            
            for idx, b_parts in enumerate(boards):
                st.write(f"**Плоча {idx+1} ({mat_name})**")
                svg = f'<svg viewBox="0 0 {board_l} {board_w}" style="background-color:#ffffff; border:2px solid #333; margin-bottom: 20px; width: 100%; max-width: 900px;">'
                svg += f'<rect x="{trim}" y="{trim}" width="{board_l - 2*trim}" height="{board_w - 2*trim}" fill="none" stroke="red" stroke-width="4" stroke-dasharray="20,20"/>'
                
                for p in b_parts:
                    px, py, pl, pw = p['x'] + trim, p['y'] + trim, p['l'], p['w']
                    ew_1 = 12 if p['d1'] in ['2', '2.0'] else (6 if p['d1'] in ['1', '1.0'] else 0)
                    ew_2 = 12 if p['d2'] in ['2', '2.0'] else (6 if p['d2'] in ['1', '1.0'] else 0)
                    eh_1 = 12 if p['sh1'] in ['2', '2.0'] else (6 if p['sh1'] in ['1', '1.0'] else 0)
                    eh_2 = 12 if p['sh2'] in ['2', '2.0'] else (6 if p['sh2'] in ['1', '1.0'] else 0)
                    
                    svg += f'<rect x="{px}" y="{py}" width="{pl}" height="{pw}" fill="#ffffff" stroke="#000000" stroke-width="2"/>'
                    
                    if ew_1: svg += f'<line x1="{px}" y1="{py+pw}" x2="{px+pl}" y2="{py+pw}" stroke="#000000" stroke-width="{ew_1}"/>'
                    if ew_2: svg += f'<line x1="{px}" y1="{py}" x2="{px+pl}" y2="{py}" stroke="#000000" stroke-width="{ew_2}"/>'
                    if eh_1: svg += f'<line x1="{px}" y1="{py}" x2="{px}" y2="{py+pw}" stroke="#000000" stroke-width="{eh_1}"/>'
                    if eh_2: svg += f'<line x1="{px+pl}" y1="{py}" x2="{px+pl}" y2="{py+pw}" stroke="#000000" stroke-width="{eh_2}"/>'
                    
                    svg += f'<text x="{px + pl/2}" y="{py + pw/2 - 15}" font-size="30" fill="black" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-weight="bold">{p["name"]}</text>'
                    svg += f'<text x="{px + pl/2}" y="{py + pw/2 + 25}" font-size="35" fill="black" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif">{int(pl)}/{int(pw)}</text>'
                
                svg += '</svg>'
                st.markdown(svg, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if st.session_state.order_list and st.button("🖼️ Генерирай JPEG файлове за сваляне"):
    with st.spinner("Подготовка на чертежите..."):
        jpeg_boards = generate_boards_jpeg(boards_per_mat, board_l, board_w, trim)
        if jpeg_boards:
            st.markdown("##### 📥 Свали JPEG чертежи:")
            for mat_name, img_bytes in jpeg_boards.items():
                st.download_button(label=f"🖼️ Свали чертеж ({mat_name})", data=img_bytes, file_name=f"razkroi_{mat_name}.jpeg", mime="image/jpeg")

# --- ФИНАНСОВ КАЛКУЛАТОР ---
st.markdown("---")
st.subheader("💰 Финанси и Оферта")

if st.session_state.order_list:
    try:
        if 'edited_df' in locals():
            df_to_calc = edited_df
        else:
            df_to_calc = pd.DataFrame(st.session_state.order_list)
            
        df_to_calc['Area'] = (pd.to_numeric(df_to_calc['Дължина']) * pd.to_numeric(df_to_calc['Ширина']) * pd.to_numeric(df_to_calc['Бр'])) / 1000000
        summary = df_to_calc.groupby('Плоскост')['Area'].sum()
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

        st.markdown("##### 3. Твърди разходи, Труд и Услуги")
        col_fixed, col_labor = st.columns(2)
        
        with col_fixed:
            st.write("**Месечни разходи (база 21 дни):**")
            osigurovki = st.number_input("Осигуровки (за теб и двамата помощници) €", value=450)
            naem = st.number_input("Наем (работилница в двора) €", value=400)
            tok = st.number_input("Ток и консумативи €", value=100)
            bus = st.number_input("Бус (гориво/поддръжка) €", value=100)
            schetovodstvo = st.number_input("Счетоводство €", value=80)
            
        with col_labor:
            st.write("**Труд и Директни разходи:**")
            project_days = st.number_input("Дни за този проект:", value=15, min_value=1)
            nadnici = st.number_input("Надници (общо за тримата/ден) €", value=225)
            transport = st.number_input("Транспорт (за поръчката) €", value=0)
            komandirovachni = st.number_input("Командировъчни €", value=0)
            hamal = st.number_input("Хамалски услуги €", value=0)

        st.markdown("##### 4. Буфери и Печалба")
        col_buf1, col_buf2 = st.columns(2)
        with col_buf1:
            nepredvideni_pct = st.number_input("Непредвидени разходи (%)", value=15)
        with col_buf2:
            pechalba_pct = st.number_input("Печалба (%)", value=25)

        # --- ИЗЧИСЛЕНИЯ ---
        # 1. Прилагане на стратегията за наем и консумативи (override)
        rent_cons_cost = (project_days / 15.0) * 300.0
        
        # 2. Останали месечни разходи (пропорционално на 21 дни)
        other_monthly = osigurovki + bus + schetovodstvo
        other_fixed_cost = (other_monthly / 21.0) * project_days
        total_fixed_project = rent_cons_cost + other_fixed_cost
        
        # 3. Труд и Услуги
        total_labor_cost = nadnici * project_days
        total_services = transport + komandirovachni + hamal
        
        # 4. Базова стойност
        total_materials_all = total_material_cost + total_cut_cost + total_edge_cost
        base_cost = total_materials_all + total_fixed_project + total_labor_cost + total_services
        
        # 5. Непредвидени
        unforeseen_cost = base_cost * (nepredvideni_pct / 100.0)
        sebestoinost = base_cost + unforeseen_cost
        
        # 6. Печалба и Крайна цена
        profit_val = sebestoinost * (pechalba_pct / 100.0)
        final_offer = sebestoinost + profit_val
        
        st.markdown("### 📊 Оферта и Калкулация:")
        st.write(f"- Материали и разкрой: **{total_materials_all:.2f} €**")
        st.write(f"- Труд (за {project_days} дни): **{total_labor_cost:.2f} €**")
        st.write(f"- Фиксирани разходи и услуги: **{(total_fixed_project + total_services):.2f} €**")
        st.write(f"- Непредвидени ({nepredvideni_pct}%): **{unforeseen_cost:.2f} €**")
        
        st.info(f"Вътрешна себестойност (всичко включено): **{sebestoinost:.2f} €**")
        st.success(f"ОФЕРТА КЪМ КЛИЕНТ: **{final_offer:.2f} €**")
        st.write(f"🌟 **Чиста печалба (след всички разходи и заплати):** {profit_val:.2f} €")
        
    except Exception as e: 
        st.warning(f"Въведи валидни числа в таблицата. Грешка: {e}")
else: st.info("Списъкът е празен. Добави първия си модул, за да видиш финансите.")
