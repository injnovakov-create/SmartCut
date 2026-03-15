import streamlit as st
import pandas as pd
import os
from PIL import Image

# Настройки на страницата
st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Добавено: Автоматично изрязване и показване на скица за всеки избран модул.")

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
        "Стандартен Долен": "🗄️",
        "Горен Шкаф": "⬆️",
        "Шкаф Мивка": "🚰",
        "Шкаф 3 Чекмеджета": "🔢",
        "Шкаф Бутилки 15см": "🍾",
        "Шкаф за Фурна": "🍳",
        "Глух Ъгъл (Долен)": "📐"
    }
    
    tip = st.selectbox("Тип модул", options=list(icons.keys()), format_func=lambda x: f"{icons[x]} {x}")
    
    # --- МАГИЯТА ЗА КАРТИНКИТЕ ---
    try:
        if os.path.exists("sketches.jpg"):
            img = Image.open("sketches.jpg")
            w_img, h_img = img.size
            step = w_img / 7 # Режем на 7 равни части
            
            # Индекси според подредбата в твоята картинка (отляво надясно)
            cabinet_index = {
                "Стандартен Долен": 0,
                "Горен Шкаф": 1,
                "Шкаф Мивка": 2,
                "Шкаф 3 Чекмеджета": 3,
                "Шкаф Бутилки 15см": 4,
                "Шкаф за Фурна": 5,
                "Глух Ъгъл (Долен)": 6
            }
            
            idx = cabinet_index[tip]
            crop_box = (idx * step, 0, (idx + 1) * step, h_img)
            cropped_img = img.crop(crop_box)
            
            # Показваме изрязаната скица
            st.image(cropped_img, use_container_width=True)
    except Exception as e:
        # Ако картинката липсва или има грешка, просто продължава без нея
        pass
    
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
                w_chelo_furna = w - fuga_obshto
                new_items.append(add_item(name, "Чело чекмедже", 1, 157, w_chelo_furna, "4 страни", mat_lice, val_fl_lice))
                w_cargi_furna = w - (2*deb) - 49
                new_items.append(add_item(name, "Царги чекм.", 2, w_cargi_furna, 70, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм.", 2, 490, 85, "2д", mat_chekm, val_fl_chekm))
                
            elif tip == "Шкаф 3 Чекмеджета":
                new_items.append(add_item(name, "Дъно", 1, w, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Страница", 2, h_stranica, d, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", mat_korpus, val_fl_korpus))
                new_items.append(add_item(name, "Гръб (Фазер)", 1, h_shkaf_korpus - otstyp_fazer, w - otstyp_fazer, "Без", mat_fazer, "Няма"))
                
                w_chelo = w - fuga_obshto
                block_note = "В БЛОК" if fl_lice else ""
                
                new_items.append(add_item(name, "Чело горно", 1, 180-fuga_obshto, w_chelo, "4 страни", mat_lice, val_fl_lice, block_note))
                new_items.append(add_item(name, "Чело средно", 1, 250-fuga_obshto, w_chelo, "4 страни", mat_lice, val_fl_lice, block_note))
                new_items.append(add_item(name, "Чело долно", 1, 330-fuga_obshto, w_chelo, "4 страни", mat_lice, val_fl_lice, block_note))
                
                w_cargi = w - (2*deb) - 49
                l_stranici_chek = runner_len - 10
                new_items.append(add_item(name, "Царги чекм. 1", 2, w_cargi, 80, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм. 1", 2, l_stranici_chek, 80+15, "2д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Царги чекм. 2", 2, w_cargi, 160, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм. 2", 2, l_stranici_chek, 160+15, "2д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Царги чекм. 3", 2, w_cargi, 200, "1д", mat_chekm, val_fl_chekm))
                new_items.append(add_item(name, "Страници чекм. 3", 2, l_stranici_chek, 200+15, "2д", mat_chekm, val_fl_chekm))

        st.session_state.order_list.extend(new_items)
        st.success(f"Модул {name} е добавен!")
        st.rerun()

with col2:
    st.subheader("📋 Списък за разкрой (Редактируем)")
    if st.session_state.order_list:
        df = pd.DataFrame(st.session_state.order_list)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        st.session_state.order_list = edited_df.to_dict('records')
        
        csv = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Свали за Excel/Optimik", data=csv, file_name="razkroi_vitya_kuhni.csv", mime="text/csv")
        
        try:
            st.markdown("##### 📊 Нужен материал (чиста площ):")
            edited_df['Area'] = (pd.to_numeric(edited_df['L']) * pd.to_numeric(edited_df['W']) * pd.to_numeric(edited_df['Брой'])) / 1000000
            summary = edited_df.groupby('Материал')['Area'].sum()
            for mat_name, area in summary.items():
                st.write(f"- **{mat_name}:** {area:.2f} м²")
        except Exception as e:
            st.warning("Въведи валидни числа за размерите, за да се изчисли площта.")
    else:
        st.info("Списъкът е празен. Добави първия си модул!")

# --- ВИЗУАЛИЗАЦИЯ НА РАЗКРОЯ ---
st.markdown("---")
st.subheader("✂️ Визуализация на разкроя (Групирана по материал)")

if st.button("Генерирай чертеж на плочите"):
    if not st.session_state.order_list:
        st.warning("Добави детайли, за да генерираш разкрой!")
    else:
        kerf = 8
        trim = 8
        board_l = 2800
        board_w = 2070
        use_l = board_l - 2*trim
        use_w = board_w - 2*trim
        
        materials_dict = {}
        for item in st.session_state.order_list:
            mat = item.get('Материал', 'Неизвестен')
            if mat not in materials_dict: materials_dict[mat] = []
            try:
                for _ in range(int(item['Брой'])):
                    materials_dict[mat].append({'name': f"{item['Модул']} - {item['Детайл']}", 'l': float(item['L']), 'w': float(item['W'])})
            except: pass
        
        for mat_name, parts in materials_dict.items():
            st.markdown(f"### 🪵 Разкрой: {mat_name}")
            parts.sort(key=lambda x: (x['w'], x['l']), reverse=True)
            boards, current_board = [], []
            curr_x, curr_y, shelf_h = 0, 0, 0
            
            for p in parts:
                part_l, part_w = p['l'], p['w']
                if curr_x + part_l <= use_l:
                    if shelf_h == 0: shelf_h = part_w
                    if curr_y + part_w <= use_w:
                        current_board.append({'x': curr_x, 'y': curr_y, 'l': part_l, 'w': part_w, 'name': p['name']})
                        curr_x += part_l + kerf
                    else:
                        boards.append(current_board)
                        current_board = [{'x': 0, 'y': 0, 'l': part_l, 'w': part_w, 'name': p['name']}]
                        curr_x = part_l + kerf
                        curr_y = 0
                        shelf_h = part_w
                else:
                    curr_x = 0
                    curr_y += shelf_h + kerf
                    shelf_h = part_w
                    if curr_y + part_w <= use_w:
                        current_board.append({'x': curr_x, 'y': curr_y, 'l': part_l, 'w': part_w, 'name': p['name']})
                        curr_x += part_l + kerf
                    else:
                        boards.append(current_board)
                        current_board = [{'x': 0, 'y': 0, 'l': part_l, 'w': part_w, 'name': p['name']}]
                        curr_x = part_l + kerf
                        curr_y = 0
                        shelf_h = part_w
                        
            if current_board: boards.append(current_board)
            st.success(f"Нужни плочи от '{mat_name}': {len(boards)} бр.")
            
            for idx, b_parts in enumerate(boards):
                st.write(f"**Плоча {idx+1} ({mat_name})**")
                svg = f'<svg viewBox="0 0 {board_l} {board_w}" style="background-color:#f9f9f9; border:2px solid #333; margin-bottom: 20px; width: 100%; max-width: 900px;"><rect x="{trim}" y="{trim}" width="{use_l}" height="{use_w}" fill="none" stroke="red" stroke-width="4" stroke-dasharray="20,20"/>'
                for p in b_parts:
                    px, py, pl, pw, name = p['x'] + trim, p['y'] + trim, p['l'], p['w'], p['name']
                    fill_color = "#e0f7fa" if "бял" in mat_name.lower() else "#ffe0b2"
                    stroke_color = "#006064" if "бял" in mat_name.lower() else "#e65100"
                    svg += f'<rect x="{px}" y="{py}" width="{pl}" height="{pw}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="4"/><text x="{px + pl/2}" y="{py + pw/2}" font-size="35" fill="#333" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-weight="bold">{name}</text><text x="{px + pl/2}" y="{py + pw/2 + 45}" font-size="30" fill="#333" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif">{pl} x {pw}</text>'
                svg += '</svg>'
                st.markdown(svg, unsafe_allow_html=True)
            st.markdown("---")
