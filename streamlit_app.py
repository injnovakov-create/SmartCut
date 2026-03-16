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
.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
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
    if "врата" in d: return "Вр"
    if "гръб" in d: return "Гръб"
    if "чело" in d: return "Чело"
    if "царги" in d: return "Цч"
    if "страници чекм" in d: return "Сч"
    return detail_name[:5].capitalize()

def get_module_abbrev(tip):
    t = str(tip).lower()
    if "3 чекмеджета" in t: return "Шк 3 ч-та"
    if "трети ред" in t: return "3-ти ред"
    if "шкаф колона" in t: return "Колона"
    if "стандартен долен" in t: return "Долен шк"
    return tip[:12]

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- ФУНКЦИЯ ЗА ЧЕРТАНЕ (ПРЕВЮ И PDF) ---
def draw_cabinet(mod_meta, order_list_temp, kraka_height, preview=False):
    canvas_w = 600 if preview else 2480 # Намалено превю с 25%
    canvas_h = 750 if preview else 3508
    img = Image.new('RGB', (canvas_w, canvas_h), 'white')
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try:
        f_dim = ImageFont.truetype(font_path, 22 if preview else 60)
        f_title = ImageFont.truetype(font_path, 26 if preview else 80)
        f_bold = ImageFont.truetype(font_path, 24 if preview else 55)
    except:
        f_dim = f_title = f_bold = ImageFont.load_default()

    W, H, D = float(mod_meta['W']), float(mod_meta['H']), float(mod_meta['D'])
    scale = (400.0 / max(W, H, D)) if preview else (1200.0 / max(W, H, D))
    
    w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
    ox, oy = d_px * 0.866, d_px * 0.5
    sx = (canvas_w - (w_px + ox)) / 2
    sy = (canvas_h / 2) - (h_px / 2) if preview else 800
    
    # Рисуване на кутията
    if "Трети ред" in mod_meta['Тип']:
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=2)
        draw.polygon([(sx, sy+h_px), (sx+ox, sy+h_px-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#e0e0e0", outline="black", width=2)
        draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=3)
    else:
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=2)
        draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black", width=2)
        draw.polygon([(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)], fill="#f5f5f5", outline="black", width=3)

    # Крака / Цокъл
    is_lower = any(t in mod_meta['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна", "Колона"])
    leg_h_px = (kraka_height * scale) if is_lower else 0
    if is_lower:
        draw.line([(sx, sy+h_px-leg_h_px), (sx+w_px, sy+h_px-leg_h_px)], fill="gray", width=2)
        leg_w_px = 40 * scale
        draw.rectangle([sx+40*scale, sy+h_px-leg_h_px, sx+40*scale+leg_w_px, sy+h_px], outline="black")
        draw.rectangle([sx+w_px-80*scale, sy+h_px-leg_h_px, sx+w_px-80*scale+leg_w_px, sy+h_px], outline="black")

    # Врати и уреди
    tip = mod_meta['Тип']
    if "3 Чекмеджета" in tip:
        draw.line([(sx, sy+180*scale), (sx+w_px, sy+180*scale)], fill="black", width=2)
        draw.line([(sx, sy+(180+250)*scale), (sx+w_px, sy+(180+250)*scale)], fill="black", width=2)
    elif "Колона" in tip:
        ld_h, md_h = mod_meta.get('ld_h', 0), mod_meta.get('md_h', 0)
        app_type = mod_meta.get('app_type', "Без уреди")
        curr_y = sy + h_px - leg_h_px
        if ld_h > 0: draw.line([(sx, curr_y - ld_h*scale), (sx+w_px, curr_y - ld_h*scale)], fill="black", width=3)
        if md_h > 0: draw.line([(sx, curr_y - (ld_h+md_h)*scale), (sx+w_px, curr_y - (ld_h+md_h)*scale)], fill="black", width=3)
        if app_type != "Без уреди":
            draw.text((sx+w_px/2, sy+h_px/2), "УРЕДИ", anchor="mm", font=f_dim, fill="#999")

    if mod_meta.get('vr_cnt', 1) == 2 and "Чекмеджета" not in tip:
        draw.line([(sx+w_px/2, sy), (sx+w_px/2, sy+h_px-leg_h_px)], fill="black", width=2)

    # Размери
    draw.text((sx+w_px/2, sy+h_px+15), f"W:{int(W)}", font=f_dim, fill="black", anchor="mt")
    draw.text((sx-15, sy+h_px/2), f"H:{int(H)}", font=f_dim, fill="black", anchor="rm")
    
    if not preview:
        draw.text((150, 150), f"МОДУЛ: {mod_meta['№']} - {mod_meta['Тип']}", fill="black", font=f_title)
        # Таблица спецификация в PDF
        draw.text((150, 1800), "СПЕЦИФИКАЦИЯ:", fill="black", font=f_title)
        cols_x = [170, 850, 1150, 1400, 1600, 2000]
        y_off = 1950
        headers = ["ДЕТАЙЛ", "ДЪЛЖ.", "ШИР.", "БР.", "КАНТ", "ПЛОСКОСТ"]
        for i, h_t in enumerate(headers): draw.text((cols_x[i], y_off), h_t, fill="black", font=f_bold)
        y_off += 100
        parts = [p for p in order_list_temp if str(p.get("№", "")) == str(mod_meta["№"])]
        for p in parts:
            row = [str(p['Детайл'])[:18], str(int(p['Дължина'])), str(int(p['Ширина'])), str(int(p['Бр'])), "Кант", str(p['Плоскост'])[:15]]
            for i, txt in enumerate(row): draw.text((cols_x[i], y_off), txt, fill="#222222", font=f_dim)
            y_off += 75
    return img

# --- ЕТИКЕТИ ---
def draw_edge_marking(draw, x, y, w, h, side, edge_type, font):
    if not edge_type: return
    text = f" {edge_type} "; lw = 2 if edge_type == '0.8' else 8
    bbox = draw.textbbox((0,0), text, font=font); tw = bbox[2]-bbox[0]
    if side == 'top':
        draw.line([(x, y), (x+w/2-tw/2, y)], fill="black", width=lw); draw.line([(x+w/2+tw/2, y), (x+w, y)], fill="black", width=lw)
        draw.text((x+w/2, y), text, fill="black", font=font, anchor="mm")
    elif side == 'bottom':
        draw.line([(x, y+h), (x+w/2-tw/2, y+h)], fill="black", width=lw); draw.line([(x+w/2+tw/2, y+h), (x+w, y+h)], fill="black", width=lw)
        draw.text((x+w/2, y+h), text, fill="black", font=font, anchor="mm")
    elif side == 'left':
        draw.line([(x, y), (x, y+h/2-10)], fill="black", width=lw); draw.line([(x, y+h/2+10), (x, y+h)], fill="black", width=lw)
        draw.text((x+12, y+h/2), text, fill="black", font=font, anchor="lm")
    elif side == 'right':
        draw.line([(x+w, y), (x+w, y+h/2-10)], fill="black", width=lw); draw.line([(x+w, y+h/2+10), (x+w, y+h)], fill="black", width=lw)
        draw.text((x+w-12, y+h/2), text, fill="black", font=font, anchor="rm")

def generate_labels_pdf(order_list):
    font_path = "Roboto-Regular.ttf"
    try: f_small = ImageFont.truetype(font_path, 20); f_text = ImageFont.truetype(font_path, 24); f_huge = ImageFont.truetype(font_path, 45); f_edge = ImageFont.truetype(font_path, 18)
    except: f_small = f_text = f_huge = f_edge = ImageFont.load_default()
    labels = []
    for p in order_list:
        for _ in range(int(p['Бр'])): labels.append(p)
    if not labels: return None
    px_mm = 11.811; page_w, page_h = 2480, 3508; cols, rows = 4, 11
    label_w, label_h = int(44*px_mm), int(20*px_mm); marg_x, marg_y = int(4*px_mm), int(9*px_mm); gap_x, gap_y = int(6*px_mm), int(6.5*px_mm)
    pages = []; current_page = Image.new('RGB', (page_w, page_h), 'white'); draw = ImageDraw.Draw(current_page)
    for i, lbl in enumerate(labels):
        if i > 0 and i % 44 == 0: pages.append(current_page); current_page = Image.new('RGB', (page_w, page_h), 'white'); draw = ImageDraw.Draw(current_page)
        c, r = (i % 44) % cols, (i % 44) // cols
        x, y = marg_x + c * (label_w + gap_x), marg_y + r * (label_h + gap_y)
        draw.rectangle([x, y, x+label_w, y+label_h], outline="#eee")
        d1 = "0.8" if str(lbl.get('Д1')) in ['1', '1.0'] else ("2" if str(lbl.get('Д1')) in ['2', '2.0'] else "")
        d2 = "0.8" if str(lbl.get('Д2')) in ['1', '1.0'] else ("2" if str(lbl.get('Д2')) in ['2', '2.0'] else "")
        sh1 = "0.8" if str(lbl.get('Ш1')) in ['1', '1.0'] else ("2" if lbl.get('Ш1') in ['2', '2.0'] else "")
        sh2 = "0.8" if str(lbl.get('Ш2')) in ['1', '1.0'] else ("2" if lbl.get('Ш2') in ['2', '2.0'] else "")
        draw_edge_marking(draw, x, y, label_w, label_h, 'top', d1, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'bottom', d2, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'left', sh1, f_edge)
        draw_edge_marking(draw, x, y, label_w, label_h, 'right', sh2, f_edge)
        draw.text((x + label_w/2, y + 35), f"[{lbl['№']}] {get_abbrev(lbl['Детайл'])}", fill="black", font=f_text, anchor="mm")
        draw.text((x + label_w/2, y + label_h/2+10), f"{int(lbl['Дължина'])}x{int(lbl['Ширина'])}", fill="black", font=f_huge, anchor="mm")
        draw.text((x + label_w/2, y + label_h - 25), f"{lbl['Плоскост'][:18]}", fill="black", font=f_small, anchor="mm")
    pages.append(current_page)
    pdf_b = io.BytesIO(); pages[0].save(pdf_b, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return pdf_b.getvalue()

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_val = st.number_input("Фуга врати (мм)", value=3.0)
    kraka_val = st.number_input("Височина крака (мм)", value=100)
    st.markdown("---")
    m_korp = st.text_input("Декор Корпус:", value="Бяло 18мм")
    m_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    m_faz = st.text_input("Декор Фазер:", value="Бял 3мм")
    if st.button("🗑️ ИЗЧИСТИ ВСИЧКО"):
        st.session_state.order_list = []; st.session_state.hardware_list = []; st.session_state.modules_meta = []; st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col_ui, col_list = st.columns([1.2, 2])

with col_ui:
    cat = st.radio("Категория:", ["🍳 Кухненски Шкафове", "🏢 Колони и Други"], horizontal=True)
    if "Кухненски" in cat:
        tip = st.selectbox("Тип модул:", ["Стандартен Долен", "Горен Шкаф", "Трети ред (Надстройка)", "Шкаф 3 Чекмеджета", "Шкаф Мивка"])
    else:
        tip = st.selectbox("Тип модул:", ["Шкаф Колона", "Дублираща страница", "Нестандартен"])

    name = st.text_input("№ на модул:", value="1")
    w = st.number_input("Ширина (W) мм:", value=600)
    h, d, vr_cnt, ld_h, md_h, app = 720, 520, 1, 0, 0, "Без уреди"

    if tip == "Шкаф Колона":
        h = st.number_input("Височина корпуса (H) мм:", value=2040)
        d = st.number_input("Дълбочина (D) мм:", value=550)
        app = st.radio("Уреди:", ["Без уреди", "Само Фурна", "Фурна + М.В."], horizontal=True)
        vr_mode = st.selectbox("Врати по височина:", ["1 цяла", "2 врати", "3 врати"])
        if vr_mode == "2 врати": ld_h = st.number_input("Долна врата (мм):", value=718)
        elif vr_mode == "3 врати":
            ld_h = st.number_input("Долна врата 1 (мм):", value=718)
            md_h = st.number_input("Средна врата 2 (мм):", value=718)
        vr_cnt = st.radio("Врати на ред:", [1, 2], index=1 if w > 500 else 0)
        h = h + kraka_val
    elif "Горен" in tip:
        d = 300; vr_cnt = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0)
    elif tip == "Трети ред (Надстройка)":
        h, d = 350, 500; vr_cnt = 1
    else:
        h = 742 + kraka_val + 38; d = 520
        vr_cnt = st.radio("Врати:", [1, 2], index=1 if w > 500 else 0)

    # ПРЕВЮ НА ЖИВО (Намалено с 25%)
    current_meta = {"№": name, "Тип": tip, "W": w, "H": h, "D": d, "vr_cnt": vr_cnt, "ld_h": ld_h, "md_h": md_h, "app_type": app}
    st.markdown("### 👁️ Превю:")
    st.image(draw_cabinet(current_meta, [], kraka_val, preview=True), use_container_width=False, width=350)

    if st.button("➕ ДОБАВИ В СПИСЪКА"):
        st.session_state.modules_meta.append(current_meta)
        new_items = []
        # Опростена логика за детайли (може да се разшири за всеки тип)
        if "Трети ред" in tip:
            new_items.extend([add_item(name, tip, "Дъно/Таван", 2, w, d, "1д", m_korp, "Не"),
                              add_item(name, tip, "Страница", 2, h-2*deb, d, "1д", m_korp, "Не"),
                              add_item(name, tip, "Врата", 1, h-fuga_obshto, w-fuga_obshto, "4 стр", m_lice, "Да")])
        else:
            new_items.append(add_item(name, tip, "Врата", vr_cnt, h-kraka_val-fuga_obshto, (w/vr_cnt)-fuga_obshto, "4 стр", m_lice, "Да"))
        
        st.session_state.order_list.extend(new_items)
        st.rerun()

with col_list:
    st.subheader("📋 Списък детайли")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.data_editor(df, use_container_width=True, height=400)
        
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button("📄 PDF Чертежи"):
                pdf_io = io.BytesIO()
                all_p = [draw_cabinet(m, st.session_state.order_list, kraka_val) for m in st.session_state.modules_meta]
                all_p[0].save(pdf_io, format="PDF", save_all=True, append_images=all_p[1:])
                st.download_button("📥 Свали Чертежи", pdf_io.getvalue(), "Vitya_M_Cherteji.pdf")
        with c_b2:
            if st.button("🏷️ PDF Етикети (44)"):
                labels = generate_labels_pdf(st.session_state.order_list)
                if labels: st.download_button("📥 Свали Етикети", labels, "Vitya_M_Etiketi.pdf")
        
        # --- ФИНАНСИ ---
        st.markdown("---")
        area = (pd.to_numeric(df['Дължина'])*pd.to_numeric(df['Ширина'])*pd.to_numeric(df['Бр'])).sum()/1000000
        st.write(f"Обща площ ПДЧ: **{area:.2f} м²**")
        p_days = st.number_input("Дни проект", value=15)
        cena = (area * 25) + (p_days * 225) + 300
        st.success(f"💰 Оферта към клиент: **{cena * 1.4:.2f} €**")
