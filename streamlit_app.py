import streamlit as st
import pandas as pd
import os
import io
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# Настройки на страницата
st.set_page_config(page_title="SMART CUT: Витя-М", layout="wide")

# --- CSS ЗА ДИЗАЙН ---
st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; }
.stButton>button { background-color: #008080 !important; color: white !important; font-weight: bold !important; width: 100%; }
[data-testid="stSidebar"] { background-color: #f0fafa !important; }
</style>
""", unsafe_allow_html=True)

if 'order_list' not in st.session_state: st.session_state.order_list = []
if 'hardware_list' not in st.session_state: st.session_state.hardware_list = []
if 'modules_meta' not in st.session_state: st.session_state.modules_meta = [] 

# --- ПОМОЩНИ ФУНКЦИИ ---
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

def get_module_abbrev(tip):
    t = str(tip).lower()
    if "3 чекмеджета" in t: return "Шк 3 ч-та"
    if "трети ред" in t: return "3-ти ред"
    if "шкаф колона" in t: return "Колона"
    return tip[:12]

# --- ФУНКЦИЯ ЗА ЧЕРТАНЕ (ИЗПОЛЗВА СЕ ЗА ПРЕВЮ И PDF) ---
def draw_cabinet(mod_meta, order_list_temp, kraka_height, preview=False):
    canvas_w = 800 if preview else 2480
    canvas_h = 1000 if preview else 3508
    img = Image.new('RGB', (canvas_w, canvas_h), 'white')
    draw = ImageDraw.Draw(img)
    
    # Шрифтове
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try:
        f_dim = ImageFont.truetype(font_path, 25 if preview else 60)
        f_title = ImageFont.truetype(font_path, 30 if preview else 80)
    except:
        f_dim = f_title = ImageFont.load_default()

    W, H, D = float(mod_meta['W']), float(mod_meta['H']), float(mod_meta['D'])
    scale = (500.0 / max(W, H, D)) if preview else (1200.0 / max(W, H, D))
    
    w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
    ox, oy = d_px * 0.8, d_px * 0.4
    sx = (canvas_w - (w_px + ox)) / 2
    sy = (canvas_h / 2.5) - (h_px / 2) if preview else 800
    
    # Кутия
    draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=2)
    draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black", width=2)
    draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=3)
    
    # Крака / Цокъл
    is_lower = any(t in mod_meta['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"])
    leg_h_px = 0
    if is_lower:
        leg_h_px = kraka_height * scale
        draw.line([(sx, sy+h_px-leg_h_px), (sx+w_px, sy+h_px-leg_h_px)], fill="gray", width=2)

    # Врати и Деления
    vr_cnt = mod_meta.get('vr_cnt', 1)
    tip = mod_meta['Тип']
    
    if "3 Чекмеджета" in tip:
        draw.line([(sx, sy+180*scale), (sx+w_px, sy+180*scale)], fill="black", width=2)
        draw.line([(sx, sy+(180+250)*scale), (sx+w_px, sy+(180+250)*scale)], fill="black", width=2)
    elif "Колона" in tip:
        ld_h = mod_meta.get('ld_h', 0)
        md_h = mod_meta.get('md_h', 0)
        app_type = mod_meta.get('app_type', "Без уреди")
        
        curr_y = sy + h_px - leg_h_px
        if ld_h > 0:
            draw.line([(sx, curr_y - ld_h*scale), (sx+w_px, curr_y - ld_h*scale)], fill="black", width=3)
        if md_h > 0:
            draw.line([(sx, curr_y - (ld_h+md_h)*scale), (sx+w_px, curr_y - (ld_h+md_h)*scale)], fill="black", width=3)
        
        if app_type != "Без уреди":
            draw.text((sx+w_px/2, sy+h_px/2), "УРЕДИ", anchor="mm", font=f_dim, fill="gray")

    if vr_cnt == 2 and "Чекмеджета" not in tip:
        draw.line([(sx+w_px/2, sy), (sx+w_px/2, sy+h_px-leg_h_px)], fill="black", width=2)

    # Размери
    draw.text((sx+w_px/2, sy+h_px+20), f"W:{int(W)}", font=f_dim, fill="black", anchor="mt")
    draw.text((sx-20, sy+h_px/2), f"H:{int(H)}", font=f_dim, fill="black", anchor="rm")
    
    if not preview:
        draw.text((150, 150), f"МОДУЛ: {mod_meta['№']} - {mod_meta['Тип']}", fill="black", font=f_title)
    return img

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga = st.number_input("Фуга (мм)", value=3.0)
    kraka_h = st.number_input("Височина крака (мм)", value=100)
    st.markdown("---")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло 18мм")
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    mat_fazer = st.text_input("Декор Фазер:", value="Бял 3мм")
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []; st.session_state.modules_meta = []; st.rerun()

# --- ИНТЕРФЕЙС ---
col_ui, col_list = st.columns([1.2, 2])

with col_ui:
    cat = st.radio("Категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Допълнителни"], horizontal=True)
    
    if "Кухненски" in cat:
        tip = st.selectbox("Тип модул:", ["Стандартен Долен", "Горен Шкаф", "Трети ред (Надстройка)", "Шкаф 3 Чекмеджета", "Шкаф Мивка"])
    else:
        tip = st.selectbox("Тип модул:", ["Шкаф Колона", "Дублираща страница", "Нестандартен"])

    name = st.text_input("Име/№:", value="1")
    
    # Специфични параметри
    w = st.number_input("Ширина (W):", value=600)
    h = 720; d = 520; vr_cnt = 1; ld_h = 0; md_h = 0; app = "Без уреди"
    
    if "Горен" in tip: h = 720; d = 300; vr_cnt = st.radio("Врати:", [1, 2], horizontal=True)
    elif "Трети ред" in tip: h = 350; d = 500; vr_cnt = 1
    elif "Шкаф Колона" in tip:
        h = st.number_input("Височина корпуса (H):", value=2040)
        d = 550
        app = st.radio("Уреди:", ["Без уреди", "Само Фурна", "Фурна + М.В."], horizontal=True)
        vr_mode = st.selectbox("Брой врати по височина:", ["1 цяла", "2 врати", "3 врати"])
        if vr_mode == "2 врати": ld_h = st.number_input("Височина долна врата:", value=718)
        elif vr_mode == "3 врати":
            ld_h = st.number_input("Височина долна (1):", value=718)
            md_h = st.number_input("Височина средна (2):", value=718)
        vr_cnt = st.radio("Врати на ред:", [1, 2], horizontal=True)
        h = h + kraka_h
    else:
        h = 742 + kraka_h + 38; d = 520
        vr_cnt = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True)

    # ПОДГОТОВКА НА МЕТА ДАННИ ЗА ПРЕВЮ
    current_meta = {"№": name, "Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vr_cnt, "ld_h": ld_h, "md_h": md_h, "app_type": app}
    
    # ПРЕВЮ НА ЖИВО
    st.markdown("### 👁️ Превю на модула:")
    preview_img = draw_cabinet(current_meta, [], kraka_h, preview=True)
    st.image(preview_img, use_container_width=True)

    if st.button("➕ ДОБАВИ В СПИСЪКА"):
        st.session_state.modules_meta.append(current_meta)
        # Тук се добавя логиката за детайлите (същата като преди)
        new_items = []
        if "Колона" in tip:
            new_items.append(add_item(name, tip, "Страница", 2, h-kraka_h, d, "1д", mat_korpus, "Не"))
            new_items.append(add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, "Не"))
            if ld_h > 0 and md_h > 0: # 3 врати
                new_items.append(add_item(name, tip, "Врата долна", vr_cnt, ld_h, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
                new_items.append(add_item(name, tip, "Врата средна", vr_cnt, md_h, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
                new_items.append(add_item(name, tip, "Врата горна", vr_cnt, h-kraka_h-ld_h-md_h-fuga*2, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
            elif ld_h > 0: # 2 врати
                new_items.append(add_item(name, tip, "Врата долна", vr_cnt, ld_h, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
                new_items.append(add_item(name, tip, "Врата горна", vr_cnt, h-kraka_h-ld_h-fuga, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
            else:
                new_items.append(add_item(name, tip, "Врата", vr_cnt, h-kraka_h-fuga, (w/vr_cnt)-fuga, "4 стр", mat_lice, "Да"))
        elif "Трети ред" in tip:
             new_items.append(add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", mat_korpus, "Не"))
             new_items.append(add_item(name, tip, "Страница", 2, h-2*deb, d, "1д", mat_korpus, "Не"))
             new_items.append(add_item(name, tip, "Врата Клапваща", 1, h-fuga, w-fuga, "4 стр", mat_lice, "Да"))
        
        st.session_state.order_list.extend(new_items)
        st.rerun()

with col_list:
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.data_editor(df, use_container_width=True)
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button("📄 Свали PDF Чертежи"):
                # Поправка на шрифтовете вътре в генератора
                pdf_io = io.BytesIO()
                all_pages = []
                for m in st.session_state.modules_meta:
                    all_pages.append(draw_cabinet(m, st.session_state.order_list, kraka_h, preview=False))
                all_pages[0].save(pdf_io, format="PDF", save_all=True, append_images=all_pages[1:])
                st.download_button("📥 ИЗТЕГЛИ PDF", pdf_io.getvalue(), "Cherteji.pdf")
