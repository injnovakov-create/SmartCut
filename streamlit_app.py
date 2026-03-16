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
    if "рафт тв" in d: return "РфтТв"
    if "рафт подвижен" in d: return "РфтПод"
    if "рафт" in d and "фурна" not in d: return "Рфт"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело" in d: return "Чело"
    return detail_name[:5].capitalize()

def get_module_abbrev(tip):
    t = str(tip).lower()
    if "3 чекмеджета" in t: return "Шк 3 ч-та"
    if "трети ред" in t: return "3-ти ред"
    if "стандартен долен" in t: return "Долен шк"
    if "горен шкаф" in t: return "Горен шк"
    if "шкаф мивка" in t: return "Шк мивка"
    if "шкаф колона" in t: return "Колона"
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
    cat_choice = st.radio("Избери категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)

    if cat_choice == "🍳 Кухненски Шкафове":
        icons = {
            "Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Трети ред (Надстройка)": "🔝", "Шкаф Мивка": "🚰", 
            "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", "Шкаф за Фурна": "🍳", 
            "Глух Ъгъл (Долен)": "📐", "Глух Ъгъл (Горен)": "📐"
        }
    else:
        icons = {
            "Шкаф Колона": "🏢", "Дублираща страница долен": "🗂️", "Нестандартен": "🧩"
        }

    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons.get(x, '📌')} {x}")
    name = st.text_input("Име/№ на модула", value=tip)
    
    # Инициализация променливи
    appliances_type = "Без уреди"
    split_doors = False
    lower_door_h = 0
    lower_type = "Врата"
    
    if tip == "Дублираща страница долен":
        h = st.number_input("Височина (H) мм", value=860); d = st.number_input("Дълбочина (D) мм", value=580); w = deb
    elif tip == "Нестандартен":
        custom_detail = st.text_input("Име на детайла", value="Нестандартен детайл")
        colA, colB, colC = st.columns(3)
        h = custom_l = colA.number_input("Дължина (L) мм", value=600)
        d = custom_w = colB.number_input("Ширина (W) мм", value=300)
        w = deb; custom_count = colC.number_input("Брой", value=1, min_value=1)
        colD, colE = st.columns(2)
        custom_kant = colD.selectbox("Кант", ["Без", "1д", "2д", "1д+1к", "1д+2к", "2д+1к", "4 страни", "2д+2к"], index=6)
        custom_mat_type = colE.selectbox("Вид материал", ["Корпус", "Лице", "Чекмеджета", "Фазер"])
    elif tip == "Трети ред (Надстройка)":
        w = st.number_input("Ширина (W) мм", value=600)
        h = st.number_input("Височина (H) мм", value=350)
        d = st.number_input("Дълбочина (D) мм", value=500)
        vrati_broi = 1 # Винаги 1 клапваща за надстройката обикновено
    elif tip == "Шкаф Колона":
        w = st.number_input("Ширина (W) мм", value=600)
        h_korpus = st.number_input("Височина корпуса мм", value=2040)
        d = st.number_input("Дълбочина (D) мм", value=550)
        appliances_type = st.radio("Вградени уреди:", ["Без уреди", "Само Фурна", "Фурна + Микровълнова"], horizontal=True)
        if appliances_type != "Без уреди":
            lower_door_h = st.number_input("Височина долна част мм", value=718)
            lower_type = st.radio("Тип долна част:", ["Врата", "2 Чекмеджета", "3 Чекмеджета"], horizontal=True)
            if "Чекмеджета" in lower_type: runner_len = st.number_input("Дължина водач (мм)", value=500, step=50)
            split_doors = True 
        else:
            split_doors = st.checkbox("Две врати по височина?", value=True)
            if split_doors: lower_door_h = st.number_input("Височина долна врата мм", value=718)
        vrati_broi = st.radio("Брой врати на ред:", [1, 2], index=0 if w <= 500 else 1, horizontal=True)
        h = h_korpus + kraka 
    else:
        default_w = 150 if tip == "Шкаф Бутилки 15см" else (1000 if "Глух" in tip else 600)
        w = st.number_input("Ширина (W) мм", value=default_w)
        if "Горен" in tip:
            h = st.number_input("Височина (H) мм", value=720); d = st.number_input("Дълбочина (D) мм", value=300)
            vrati_broi = st.radio("Брой врати:", [1, 2], index=1, horizontal=True)
            vrati_orientacia = st.radio("Ориентация:", ["Вертикални", "Хоризонтални (Клапващи)"], horizontal=True)
        else:
            d = st.number_input("Дълбочина (D) мм", value=(550 if tip == "Шкаф Мивка" else 520))
            if tip == "Шкаф 3 Чекмеджета": runner_len = st.number_input("Дължина водач (мм)", value=500, step=50)
            elif tip == "Шкаф за Фурна": runner_len = 500
            h = 742 + kraka + 38 
            if tip in ["Стандартен Долен", "Шкаф Мивка"]:
                def_vrati = 0 if w <= 500 else 1
                vrati_broi = st.radio("Брой врати:", [1, 2], index=def_vrati, horizontal=True)

    if st.button("➕ Добави към списъка"):
        new_items = []
        new_hw = []
        otstyp_f = 4; h_stranica = 742; h_korp = h_stranica + deb; h_vrata_std = h_korp - fuga_obshto
        
        meta = {"№": name, "Тип": tip, "W": w, "H": h, "D": d}
        if tip == "Шкаф Колона": meta.update({"app_type": appliances_type, "ld_h": lower_door_h, "lower_type": lower_type})
        st.session_state.modules_meta.append(meta)

        if tip in ["Стандартен Долен", "Шкаф Мивка", "Шкаф Бутилки 15см", "Глух Ъгъл (Долен)", "Шкаф за Фурна", "Шкаф 3 Чекмеджета", "Шкаф Колона"]:
            new_hw.append({"№": name, "Артикул": "Крака за долен шкаф", "Брой": 5 if w > 900 else 4})

        if tip == "Трети ред (Надстройка)":
            new_items.extend([
                add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Страница", 2, h - (2*deb), d, "1д", mat_korpus, val_fl_korpus),
                add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_f, w - otstyp_f, "Без", mat_fazer, "Няма"),
                add_item(name, tip, "Врата (Клапваща)", 1, h - fuga_obshto, w - fuga_obshto, "4 страни", mat_lice, val_fl_lice)
            ])
            new_hw.append({"№": name, "Артикул": "Панти покрит кант", "Брой": 2})
            new_hw.append({"№": name, "Артикул": "Амортисьори/Механизъм", "Брой": 2})
            new_hw.append({"№": name, "Артикул": "Дръжки", "Брой": 1})

        elif tip == "Шкаф Колона":
            new_items.extend([add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Страница", 2, h - kraka - deb, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Таван", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Гръб (Фазер)", 1, h - kraka - otstyp_f, w - otstyp_f, "Без", mat_fazer, "Няма")])
            h_rem = h - kraka - deb
            if appliances_type != "Без уреди":
                h_f = 595; h_m = 380 if appliances_type == "Фурна + Микровълнова" else 0
                h_door_up = h_rem - lower_door_h - h_f - h_m - (fuga_obshto * 2)
                new_items.extend([add_item(name, tip, "Рафт тв. (под фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                                  add_item(name, tip, "Рафт тв. (над фурна)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus)])
                if h_m > 0: new_items.append(add_item(name, tip, "Рафт тв. (над МВ)", 1, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus))
                
                if lower_type == "Врата":
                    new_items.append(add_item(name, tip, "Врата долна", vrati_broi, lower_door_h, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                    new_hw.append({"№": name, "Артикул": "Панти", "Брой": calculate_hinges(lower_door_h)*vrati_broi})
                elif "Чекмеджета" in lower_type:
                    cnt = 2 if "2" in lower_type else 3
                    new_hw.append({"№": name, "Артикул": "Водачи", "Брой": cnt})
                new_items.append(add_item(name, tip, "Врата горна", vrati_broi, h_door_up, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_hw.append({"№": name, "Артикул": "Панти", "Брой": calculate_hinges(h_door_up)*vrati_broi})
            else:
                h_door_full = h_rem - fuga_obshto
                new_items.append(add_item(name, tip, "Врата", vrati_broi, h_door_full, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))
                new_hw.append({"№": name, "Артикул": "Панти", "Брой": calculate_hinges(h_door_full)*vrati_broi})

        elif tip == "Горен Шкаф":
            new_items.extend([add_item(name, tip, "Страница", 2, h, d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Дъно/Таван", 2, w-(2*deb), d, "1д", mat_korpus, val_fl_korpus),
                              add_item(name, tip, "Гръб (Фазер)", 1, h - otstyp_f, w - otstyp_f, "Без", mat_fazer, "Няма")])
            h_v = h - fuga_obshto; w_v = (w/vrati_broi) - (fuga_obshto if vrati_broi==1 else fuga_obshto/2)
            new_items.append(add_item(name, tip, "Врата", vrati_broi, h_v, w_v, "4 страни", mat_lice, val_fl_lice))
            new_hw.append({"№": name, "Артикул": "Окачвачи", "Брой": 2})
        
        else: # Долни стандартни
             new_items.extend([add_item(name, tip, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus),
                               add_item(name, tip, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus),
                               add_item(name, tip, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus)])
             if tip == "Шкаф 3 Чекмеджета":
                 new_items.extend([add_item(name, tip, "Чело 180", 1, 180-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice),
                                   add_item(name, tip, "Чело 250", 1, 250-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice),
                                   add_item(name, tip, "Чело 330", 1, 330-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice)])
             else:
                 new_items.append(add_item(name, tip, "Врата", vrati_broi, h_vrata_std, (w/vrati_broi)-fuga_obshto, "4 страни", mat_lice, val_fl_lice))

        st.session_state.order_list.extend(new_items); st.session_state.hardware_list.extend(new_hw)
        st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        cols = ["Плоскост", "№", "Тип", "Детайл", "Дължина", "Ширина", "Фладер", "Бр", "Д1", "Д2", "Ш1", "Ш2"]
        edited_df = st.data_editor(df[cols], num_rows="dynamic", use_container_width=True, height=350)
        st.session_state.order_list = edited_df.to_dict('records')
        
        if st.session_state.hardware_list:
            hw_summary = pd.DataFrame(st.session_state.hardware_list).groupby("Артикул")["Брой"].sum().reset_index()
            st.table(hw_summary)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Разкрой')
        st.download_button(label="📊 Свали Excel", data=output.getvalue(), file_name="razkroi.xlsx")
    else: st.info("Списъкът е празен.")

# --- PDF ГЕНЕРАТОР ---
def generate_technical_pdf(modules_meta, order_list, kraka_h):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: f_title = ImageFont.truetype(font_path, 80); f_text = ImageFont.truetype(font_path, 50); f_dim = ImageFont.truetype(font_path, 60); f_bold = ImageFont.truetype(font_path, 55)
    except: f_title = f_text = f_dim = f_bold = ImageFont.load_default()

    pages = []
    for mod in modules_meta:
        img = Image.new('RGB', (2480, 3508), 'white'); draw = ImageDraw.Draw(img)
        draw.text((150, 150), f"МОДУЛ: {mod['№']} - {mod['Тип']}", fill="black", font=font_title)
        draw.line([(150, 250), (2330, 250)], fill="black", width=5)
        
        W, H, D = float(mod['W']), float(mod['H']), float(mod['D'])
        scale = 1000.0 / max(W, H, D) if max(W, H, D) > 0 else 1
        w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
        ox, oy = d_px * 0.866, d_px * 0.5
        sx, sy = 1240 - (w_px + ox)/2, 1000 - (h_px + oy)/2
        
        # Визуално за Трети ред (Страници между дъно и таван)
        if "Трети ред" in mod['Тип']:
            # Дъно и Таван (покриват страниците)
            draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=5) # Таван
            draw.polygon([(sx, sy+h_px), (sx+ox, sy+h_px-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#e0e0e0", outline="black", width=5) # Дъно
            draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=5) # Лице
        else:
            draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=5) 
            draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black", width=5) 
            draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=5)

        draw.text((sx + w_px/2 - 100, sy + h_px + 30), f"W: {int(W)}", fill="black", font=f_dim)
        draw.text((sx - 250, sy + h_px/2 - 30), f"H: {int(H)}", fill="black", font=f_dim)
        
        # Таблица детайли
        draw.text((150, 1800), "СПЕЦИФИКАЦИЯ:", fill="black", font=font_title)
        parts = [p for p in order_list if str(p.get("№", "")) == str(mod["№"])]
        cols_x = [170, 850, 1150, 1400, 1600, 2000]; lines_x = [150, 830, 1130, 1380, 1580, 1980, 2350]
        y_off = 1950; start_y_t = y_off - 20
        headers = ["ДЕТАЙЛ", "ДЪЛЖ.", "ШИР.", "БР.", "КАНТ", "ПЛОСКОСТ"]
        for i, h_t in enumerate(headers): draw.text((cols_x[i], y_off), h_t, fill="black", font=f_bold)
        y_off += 100
        for p in parts:
            row = [str(p['Детайл'])[:18], str(int(p['Дължина'])), str(int(p['Ширина'])), str(int(p['Бр'])), "Кант", str(p['Плоскост'])[:15]]
            for i, txt in enumerate(row): draw.text((cols_x[i], y_off), txt, fill="#222222", font=f_text)
            y_off += 75
        pages.append(img)
    if pages:
        pdf_b = io.BytesIO(); pages[0].save(pdf_b, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
        return pdf_b.getvalue()
    return None

# --- ГЕНЕРИРАНЕ НА ЕТИКЕТИ ---
def draw_edge_marking(draw, x, y, w, h, side, edge_type, font):
    if not edge_type: return
    text = f" {edge_type} "; bbox = draw.textbbox((0,0), text, font=font); tw = bbox[2]-bbox[0]; th = bbox[3]-bbox[1]; lw = 2 if edge_type == '0.8' else 8
    if side == 'top': draw.line([(x, y), (x+w/2-tw/2, y)], fill="black", width=lw); draw.line([(x+w/2+tw/2, y), (x+w, y)], fill="black", width=lw); draw.text((x+w/2, y), text, fill="black", font=font, anchor="mm")
    elif side == 'bottom': draw.line([(x, y+h), (x+w/2-tw/2, y+h)], fill="black", width=lw); draw.line([(x+w/2+tw/2, y+h), (x+w, y+h)], fill="black", width=lw); draw.text((x+w/2, y+h), text, fill="black", font=font, anchor="mm")
    elif side == 'left': draw.line([(x, y), (x, y+h/2-th/2)], fill="black", width=lw); draw.line([(x, y+h/2+th/2), (x, y+h)], fill="black", width=lw); draw.text((x+15, y+h/2), text, fill="black", font=font, anchor="lm")
    elif side == 'right': draw.line([(x+w, y), (x+w, y+h/2-th/2)], fill="black", width=lw); draw.line([(x+w, y+h/2+th/2), (x+w, y+h)], fill="black", width=lw); draw.text((x+w-15, y+h/2), text, fill="black", font=font, anchor="rm")

def generate_labels_pdf(order_list):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: f_small = ImageFont.truetype(font_path, 20); f_text = ImageFont.truetype(font_path, 24); f_huge = ImageFont.truetype(font_path, 45); f_edge = ImageFont.truetype(font_path, 18)
    except: f_small = f_text = f_huge = f_edge = ImageFont.load_default()
    
    labels = []
    for p in order_list:
        for _ in range(int(p['Бр'])): labels.append(p)
    if not labels: return None

    px_mm = 11.811; page_w, page_h = 2480, 3508; cols, rows = 4, 11
    label_w, label_h = int(44*px_mm), int(20*px_mm); marg_x, marg_y = int(4*px_mm), int(9*px_mm); gap_x, gap_y = int(6*px_mm), int(6.5*px_mm); pad = int(3*px_mm)
    
    pages = []; current_page = Image.new('RGB', (page_w, page_h), 'white'); draw = ImageDraw.Draw(current_page)
    for i, lbl in enumerate(labels):
        if i > 0 and i % (cols * rows) == 0: pages.append(current_page); current_page = Image.new('RGB', (page_w, page_h), 'white'); draw = ImageDraw.Draw(current_page)
        c = (i % (cols * rows)) % cols; r = (i % (cols * rows)) // cols
        x = marg_x + c * (label_w + gap_x); y = marg_y + r * (label_h + gap_y)
        draw.rectangle([x, y, x+label_w, y+label_h], outline="#eeeeee", width=1)
        
        d1 = "0.8" if str(lbl.get('Д1')) in ['1', '1.0'] else ("2" if str(lbl.get('Д1')) in ['2', '2.0'] else "")
        d2 = "0.8" if str(lbl.get('Д2')) in ['1', '1.0'] else ("2" if str(lbl.get('Д2')) in ['2', '2.0'] else "")
        sh1 = "0.8" if str(lbl.get('Ш1')) in ['1', '1.0'] else ("2" if str(lbl.get('Ш1')) in ['2', '2.0'] else "")
        sh2 = "0.8" if str(lbl.get('Ш2')) in ['1', '1.0'] else ("2" if str(lbl.get('Ш2')) in ['2', '2.0'] else "")
        
        draw_edge_marking(draw, x, y, label_w, label_h, 'top', d1, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'bottom', d2, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'left', sh1, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'right', sh2, f_edge)
        
        mod_abbr = get_module_abbrev(lbl.get('Тип', ''))
        draw.text((x + label_w/2, y + pad), f"[{lbl['№']}] {mod_abbr} | {get_abbrev(lbl['Детайл'])}", fill="black", font=f_text, anchor="mt")
        draw.text((x + label_w/2, y + label_h/2), f"{int(lbl['Дължина'])}x{int(lbl['Ширина'])}", fill="black", font=f_huge, anchor="mm")
        draw.text((x + label_w/2, y + label_h - pad), f"{lbl['Плоскост'][:20]}", fill="black", font=f_small, anchor="mb")
    pages.append(current_page)
    pdf_b = io.BytesIO(); pages[0].save(pdf_b, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_b.getvalue()

st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    if st.button("📄 Свали PDF Чертежи"):
        pdf = generate_technical_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka)
        if pdf: st.download_button("📥 ИЗТЕГЛИ ЧЕРТЕЖИ", pdf, "Vitya_M_Cherteji.pdf", "application/pdf")
with c2:
    if st.button("🏷️ Свали ЕТИКЕТИ (44 бр. А4)"):
        pdf = generate_labels_pdf(st.session_state.order_list)
        if pdf: st.download_button("📥 ИЗТЕГЛИ ЕТИКЕТИ", pdf, "Vitya_M_Etiketi.pdf", "application/pdf")

# --- ФИНАНСИ (ОБЛЕКЧЕНИ) ---
st.markdown("---")
st.subheader("💰 ФИНАНСИ")
if st.session_state.order_list:
    df_c = pd.DataFrame(st.session_state.order_list)
    area = (pd.to_numeric(df_c['Дължина'])*pd.to_numeric(df_c['Ширина'])*pd.to_numeric(df_c['Бр'])).sum()/1000000
    st.write(f"Обща квадратура ПДЧ: **{area:.2f} м²**")
    p_days = st.number_input("Дни проект", value=15)
    total_cost = (area * 25) + (p_days * 225) + 300 # Груба сметка
    st.success(f"ОРИЕНТИРОВЪЧНА ОФЕРТА: **{total_cost*1.4:.2f} €**")
