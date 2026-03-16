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
    if "рафт" in d: return "Рфт"
    if "врата" in d: return "Вр"
    if "гръб" in d or "фазер" in d: return "Гръб"
    if "чело" in d: return "Чело"
    return detail_name[:5].capitalize()

def calculate_hinges(height):
    if height <= 950: return 2
    elif height <= 1300: return 3
    else: return 4

# --- СТРАНИЧНО МЕНЮ ---
with st.sidebar:
    st.header("⚙️ Глобални Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka_h = st.number_input("Височина крака (мм)", value=100)
    
    st.markdown("---")
    st.header("🎨 Материали")
    mat_korpus = st.text_input("Декор Корпус:", value="Бяло 18мм")
    val_fl_korpus = "Да" if st.checkbox("Фладер Корпус", value=False) else "Няма"
    mat_lice = st.text_input("Декор Лице:", value="Дъб Вотан 18мм")
    val_fl_lice = "Да" if st.checkbox("Фладер Лице", value=True) else "Няма"
    mat_fazer = st.text_input("Декор Фазер:", value="Бял 3мм")
    
    if st.button("🗑️ Изчисти всичко"):
        st.session_state.order_list = []
        st.session_state.hardware_list = []
        st.session_state.modules_meta = []
        st.rerun()

# --- ОСНОВЕН ИНТЕРФЕЙС ---
col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    icons = {"Стандартен Долен": "🗄️", "Горен Шкаф": "⬆️", "Шкаф Мивка": "🚰", "Шкаф 3 Чекмеджета": "🔢", "Шкаф Бутилки 15см": "🍾", "Шкаф за Фурна": "🍳", "Глух Ъгъл (Долен)": "📐", "Нестандартен": "🧩"}
    tip = st.selectbox("Тип модул", options=list(icons.keys()))
    name = st.text_input("Име/№ на модула", value="1")
    
    default_w = 150 if tip == "Шкаф Бутилки 15см" else 600
    w = st.number_input("Ширина (W)", value=default_w)
    
    if "Горен" in tip:
        h = st.number_input("Височина (H)", value=720)
        d = st.number_input("Дълбочина (D)", value=300)
        vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True)
        vrati_orientacia = "Вертикални"
    else:
        h = 742 + kraka_h + 38 
        d = st.number_input("Дълбочина (D)", value=520)
        vrati_broi = st.radio("Брой врати:", [1, 2], index=1 if w > 500 else 0, horizontal=True)

    if st.button("➕ ДОБАВИ"):
        new_items = []
        new_hw = []
        otstyp_f = 4; h_str = 742; h_korp = h_str + deb; h_vr_std = h_korp - fuga_obshto
        
        st.session_state.modules_meta.append({"№": name, "Тип": tip, "W": w, "H": h, "D": d, "Vrati": vrati_broi})

        if "Горен" not in tip:
            legs = 5 if w > 900 else 4
            new_hw.append({"№": name, "Артикул": "Крака", "Брой": legs})
        
        if tip == "Шкаф 3 Чекмеджета":
            new_hw.append({"№": name, "Артикул": "Комплект водачи", "Брой": 3})
            new_items.extend([add_item(name, "Чело 180", 1, 180-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice),
                              add_item(name, "Чело 250", 1, 250-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice),
                              add_item(name, "Чело 330", 1, 330-fuga_obshto, w-fuga_obshto, "4 страни", mat_lice, val_fl_lice)])
        elif tip == "Шкаф Мивка":
            new_items.append(add_item(name, "Врата", vrati_broi, h_vr_std, (w/vrati_broi)-(fuga_obshto/2), "4 страни", mat_lice, val_fl_lice))
        elif tip == "Горен Шкаф":
            shelves = 2 if h > 800 else 1
            new_hw.append({"№": name, "Артикул": "Окачвачи", "Брой": 2})
            new_hw.append({"№": name, "Артикул": "LED (лм)", "Брой": w/1000})
            new_hw.append({"№": name, "Артикул": "Рафтоносачи", "Брой": shelves*4})
            new_items.append(add_item(name, "Врата", vrati_broi, h-fuga_obshto, (w/vrati_broi)-(fuga_obshto/2), "4 страни", mat_lice, val_fl_lice))
        else:
            new_items.append(add_item(name, "Врата", vrati_broi, h_vr_std, (w/vrati_broi)-(fuga_obshto/2), "4 страни", mat_lice, val_fl_lice))

        st.session_state.order_list.extend(new_items)
        st.session_state.hardware_list.extend(new_hw)
        st.rerun()

with col2:
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        st.data_editor(df, use_container_width=True, height=300)
        
        if st.session_state.hardware_list:
            st.markdown("#### 🔩 Обков")
            hw_df = pd.DataFrame(st.session_state.hardware_list).groupby("Артикул")["Брой"].sum().reset_index()
            st.table(hw_df)

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Разкрой')
                if st.session_state.hardware_list:
                    hw_df.to_excel(writer, index=False, sheet_name='Обков')
            st.download_button(label="📊 Свали в Excel (.xlsx)", data=output.getvalue(), file_name="razkroi_vitya_kuhni.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col_ex2:
            # --- ИНТЕГРАЦИЯ С ОПТИМИК ---
            df_optimik = df.copy()
            df_optimik = df_optimik.rename(columns={"Бр": "Количество", "Детайл": "Описание", "Плоскост": "Материал"})
            optimik_cols = ["№", "Описание", "Дължина", "Ширина", "Количество", "Материал", "Д1", "Д2", "Ш1", "Ш2"]
            df_optimik = df_optimik[optimik_cols]
            # Използваме точка и запетая за разделител, тъй като Оптимик често работи с европейски локални настройки
            csv_optimik = df_optimik.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Експорт за ОПТИМИК (.csv)", data=csv_optimik, file_name="Export_Optimik.csv", mime="text/csv")
            
# --- PDF ГЕНЕРАТОР С 3D ПОДОБРЕНИЯ ---
def generate_improved_pdf(meta, orders, k_h):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except: pass
    try: f_title = ImageFont.truetype(font_path, 70); f_text = ImageFont.truetype(font_path, 45); f_dim = ImageFont.truetype(font_path, 55)
    except: f_title = f_text = f_dim = ImageFont.load_default()

    pages = []
    for mod in meta:
        img = Image.new('RGB', (2480, 3508), 'white'); draw = ImageDraw.Draw(img)
        draw.text((150, 150), f"МОДУЛ №{mod['№']} - {mod['Тип']}", fill="black", font=f_title)
        
        W, H, D = float(mod['W']), float(mod['H']), float(mod['D'])
        scale = 1000.0 / max(W, H, D) if max(W, H, D) > 0 else 1
        w_px, h_px, d_px = W * scale, H * scale, D * scale * 0.5
        ox, oy = d_px * 0.8, d_px * 0.4
        sx, sy = 1240 - (w_px + ox)/2, 1000 - (h_px + oy)/2
        
        # Кутия
        pts = [(sx, sy), (sx+w_px, sy), (sx+w_px, sy+h_px), (sx, sy+h_px)]
        draw.polygon([(sx, sy), (sx+ox, sy-oy), (sx+w_px+ox, sy-oy), (sx+w_px, sy)], fill="#e0e0e0", outline="black", width=4)
        draw.polygon([(sx+w_px, sy), (sx+w_px+ox, sy-oy), (sx+w_px+ox, sy+h_px-oy), (sx+w_px, sy+h_px)], fill="#d0d0d0", outline="black", width=4)
        draw.polygon(pts, fill="#f5f5f5", outline="black", width=5)

        # КРАЧЕТА (4 правоъгълника)
        if any(t in mod['Тип'] for t in ["Долен", "Мивка", "Чекмеджета", "Фурна"]):
            leg_w, leg_h = 40 * scale, k_h * scale
            offset = 50 * scale
            draw.rectangle([sx+offset, sy+h_px-leg_h, sx+offset+leg_w, sy+h_px], outline="black", width=3)
            draw.rectangle([sx+w_px-offset-leg_w, sy+h_px-leg_h, sx+w_px-offset, sy+h_px], outline="black", width=3)
            draw.rectangle([sx+offset+ox, sy+h_px-leg_h-oy, sx+offset+leg_w+ox, sy+h_px-oy], outline="black", width=2)
            draw.rectangle([sx+w_px-offset-leg_w+ox, sy+h_px-leg_h-oy, sx+w_px-offset+ox, sy+h_px-oy], outline="black", width=2)

        # ДВЕ ВРАТИ (Линия по средата)
        if mod['Vrati'] == 2 and "Чекмеджета" not in mod['Тип']:
            draw.line([(sx + w_px/2, sy), (sx + w_px/2, sy + h_px - (leg_h if 'leg_h' in locals() else 0))], fill="black", width=3)

        # ЧЕЛА НА ЧЕКМЕДЖЕТА С РАЗМЕРИ
        if "3 Чекмеджета" in mod['Тип']:
            y180 = sy + (180 * scale); y250 = y180 + (250 * scale)
            draw.line([(sx, y180), (sx+w_px, y180)], fill="black", width=4); draw.text((sx+w_px+20, sy+70*scale), "180", fill="red", font=f_dim)
            draw.line([(sx, y250), (sx+w_px, y250)], fill="black", width=4); draw.text((sx+w_px+20, y180+100*scale), "250", fill="red", font=f_dim)
            draw.text((sx+w_px+20, y250+120*scale), "330", fill="red", font=f_dim)

        draw.text((sx + w_px/2 - 50, sy + h_px + 40), f"W:{int(W)}", fill="red", font=f_dim)
        draw.text((sx - 200, sy + h_px/2), f"H:{int(H)}", fill="red", font=f_dim)
        
        # Спецификация отдолу
        y_off = 1900; draw.text((150, y_off), "ДЕТАЙЛИ:", font=f_title, fill="black"); y_off += 120
        for p in [o for o in orders if str(o['№']) == str(mod['№'])]:
            row = f"{p['Детайл'][:15]:<15} | {int(p['Дължина']):>4} x {int(p['Ширина']):>4} | {p['Бр']}бр | {p['Плоскост'][:15]}"
            draw.text((150, y_off), row, font=f_text, fill="#333"); y_off += 70
        pages.append(img)
    
    if pages:
        pdf = io.BytesIO()
        pages[0].save(pdf, format="PDF", save_all=True, append_images=pages[1:])
        return pdf.getvalue()
    return None

st.markdown("---")
c_p1, c_p2 = st.columns(2)
with c_p1:
    if st.button("📄 Генерирай PDF Чертежи"):
        if not st.session_state.modules_meta:
            st.warning("Добави поне един модул!")
        else:
            pdf_file = generate_improved_pdf(st.session_state.modules_meta, st.session_state.order_list, kraka_h)
            if pdf_file:
                st.download_button("📥 ИЗТЕГЛИ PDF", pdf_file, "SmartCut_Vitya_M.pdf", mime="application/pdf")

# --- ФИНАНСИ ---
with c_p2:
    st.subheader("💰 ФИНАНСИ")
    if st.session_state.order_list:
        p_days = st.number_input("Дни проект", value=15)
        osig = 450; naem_kon = (p_days/15)*300; bus = 100; schet = 80; nadnici = p_days*225
        fix_total = osig + naem_kon + bus + schet + nadnici
        
        st.write(f"- Труд и фиксирани: **{fix_total:.2f} €**")
        transport = st.number_input("Транспорт €", 0); hamal = st.number_input("Хамали €", 0)
        
        df_calc = pd.DataFrame(st.session_state.order_list)
        m2_total = (pd.to_numeric(df_calc['Дължина'])*pd.to_numeric(df_calc['Ширина'])*pd.to_numeric(df_calc['Бр'])).sum()/1000000
        mat_cost = m2_total * 25 
        
        subtotal = fix_total + transport + hamal + mat_cost
        nepredvideni = subtotal * 0.15
        final = (subtotal + nepredvideni) * 1.25
        
        st.success(f"ОФЕРТА КЪМ КЛИЕНТ: {final:.2f} €")
        st.info(f"Чиста печалба: {final - (subtotal + nepredvideni):.2f} €")
