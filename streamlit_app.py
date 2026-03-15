import streamlit as st
import pandas as pd

st.set_page_config(page_title="SmartCut: Витя-М", layout="wide")

st.title("🛠️ SmartCut: Конструктор на Модули")
st.info("Интерактивна таблица и вграден бърз разкрой (Плоча 2800x2070, Сряз 8мм, Окрайчване 8мм).")

if 'order_list' not in st.session_state:
    st.session_state.order_list = []

def add_item(modul, detail, count, l, w, kant, flader, note=""):
    return {"Модул": modul, "Детайл": detail, "Брой": count, "L": l, "W": w, "Кант": kant, "Фладер": flader, "Забележка": note}

with st.sidebar:
    st.header("⚙️ Настройки")
    deb = st.number_input("Дебелина ПДЧ (мм)", value=18)
    fuga_obshto = st.number_input("Фуга врати/чела (мм)", value=3.0)
    kraka = st.number_input("Височина крака (мм)", value=100)
    
    if st.button("🗑️ Изчисти списъка"):
        st.session_state.order_list = []
        st.rerun()

col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📝 Добави Модул")
    tip = st.selectbox("Тип модул", ["Шкаф Мивка", "Горен Шкаф", "Стандартен Долен", "Шкаф 3 Чекмеджета"])
    name = st.text_input("Име/№ на модула", value=tip)
    w = st.number_input("Ширина (W) в мм", value=600)
    
    runner_len = 500
    if tip == "Шкаф 3 Чекмеджета":
        runner_len = st.number_input("Дължина водач Blum (мм)", value=500, step=50)
        
    d = st.number_input("Дълбочина (D) страници", value=550)
    flader = st.selectbox("Шарка (Фладер)", ["Няма", "Да (по L)", "Да (по W)"])

    if st.button("➕ Добави към списъка"):
        new_items = []
        h_stranica = 742 
        h_shkaf_korpus = h_stranica + deb 
        h_vrata_standart = h_shkaf_korpus - fuga_obshto
        w_vrata = (w/2) - (fuga_obshto/2)

        if tip == "Шкаф Мивка":
            new_items.extend([
                add_item(name, "Дъно", 1, w, 480, "1д", flader),
                add_item(name, "Страница", 2, h_stranica, d, "1д", flader),
                add_item(name, "Бленда", 3, w-(2*deb), 112, "1д", flader),
                add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader)
            ])
        elif tip == "Стандартен Долен":
            new_items.extend([
                add_item(name, "Дъно", 1, w, 520, "1д", flader),
                add_item(name, "Страница", 2, h_stranica, d, "1д", flader),
                add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader),
                add_item(name, "Рафт", 1, w-(2*deb), 510, "1д", flader),
                add_item(name, "Врата", 2, h_vrata_standart, w_vrata, "4 страни", flader)
            ])
        elif tip == "Горен Шкаф":
            h_goren = 720
            new_items.extend([
                add_item(name, "Страница", 2, h_goren, 300, "1д", flader),
                add_item(name, "Дъно/Таван", 2, w-(2*deb), 300, "1д", flader),
                add_item(name, "Врата", 2, h_goren-fuga_obshto, w_vrata, "4 страни", flader)
            ])
        elif tip == "Шкаф 3 Чекмеджета":
            w_chelo = w - fuga_obshto
            block_note = "В БЛОК" if flader != "Няма" else ""
            w_cargi = w - (2*deb) - 49
            l_stranici_chek = runner_len - 10
            
            new_items.extend([
                add_item(name, "Дъно", 1, w, 520, "1д", flader),
                add_item(name, "Страница", 2, h_stranica, d, "1д", flader),
                add_item(name, "Бленда", 2, w-(2*deb), 112, "1д", flader),
                add_item(name, "Чело горно", 1, 180-fuga_obshto, w_chelo, "4 страни", flader, block_note),
                add_item(name, "Чело средно", 1, 250-fuga_obshto, w_chelo, "4 страни", flader, block_note),
                add_item(name, "Чело долно", 1, 330-fuga_obshto, w_chelo, "4 страни", flader, block_note),
                add_item(name, "Царги чекм. 1", 2, w_cargi, 80, "1д", flader),
                add_item(name, "Страници чекм. 1", 2, l_stranici_chek, 80+15, "2д", flader),
                add_item(name, "Царги чекм. 2", 2, w_cargi, 160, "1д", flader),
                add_item(name, "Страници чекм. 2", 2, l_stranici_chek, 160+15, "2д", flader),
                add_item(name, "Царги чекм. 3", 2, w_cargi, 200, "1д", flader),
                add_item(name, "Страници чекм. 3", 2, l_stranici_chek, 200+15, "2д", flader)
            ])

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
        st.download_button(label="📥 Свали за Excel/Optimik", data=csv, file_name="razkroi_vitya.csv", mime="text/csv")
        
        try:
            total_m2 = (pd.to_numeric(edited_df['L']) * pd.to_numeric(edited_df['W']) * pd.to_numeric(edited_df['Брой'])).sum() / 1000000
            st.metric("Обща площ ПДЧ (чиста)", f"{total_m2:.2f} м2")
        except:
            pass
    else:
        st.info("Списъкът е празен.")

# --- ВИЗУАЛИЗАЦИЯ НА РАЗКРОЯ ---
st.markdown("---")
st.subheader("✂️ Визуализация на разкроя (Плоча 2800x2070)")

if st.button("Генерирай чертеж на плочите"):
    if not st.session_state.order_list:
        st.warning("Добави детайли, за да генерираш разкрой!")
    else:
        # Параметри
        kerf = 8
        trim = 8
        board_l = 2800
        board_w = 2070
        use_l = board_l - 2*trim
        use_w = board_w - 2*trim
        
        # Подготовка на детайлите
        parts = []
        for item in st.session_state.order_list:
            try:
                for _ in range(int(item['Брой'])):
                    parts.append({
                        'name': f"{item['Модул']} - {item['Детайл']}",
                        'l': float(item['L']),
                        'w': float(item['W'])
                    })
            except: pass
            
        # Сортиране (Shelf алгоритъм - първо най-широките)
        parts.sort(key=lambda x: (x['w'], x['l']), reverse=True)
        
        boards = []
        current_board = []
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
        
        st.success(f"Нужни плочи: {len(boards)} бр.")
        
        # Чертане
        for idx, b_parts in enumerate(boards):
            st.write(f"**Плоча {idx+1}**")
            svg = f'<svg viewBox="0 0 {board_l} {board_w}" style="background-color:#f9f9f9; border:2px solid #333; margin-bottom: 20px; width: 100%; max-width: 900px;">'
            # Окрайчване (червена пунктирана линия)
            svg += f'<rect x="{trim}" y="{trim}" width="{use_l}" height="{use_w}" fill="none" stroke="red" stroke-width="4" stroke-dasharray="20,20"/>'
            
            for p in b_parts:
                px, py = p['x'] + trim, p['y'] + trim
                pl, pw = p['l'], p['w']
                name = p['name']
                # Детайл
                svg += f'<rect x="{px}" y="{py}" width="{pl}" height="{pw}" fill="#e0f7fa" stroke="#006064" stroke-width="4"/>'
                # Текст вътре в детайла
                svg += f'<text x="{px + pl/2}" y="{py + pw/2}" font-size="35" fill="#004d40" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-weight="bold">{name}</text>'
                svg += f'<text x="{px + pl/2}" y="{py + pw/2 + 45}" font-size="30" fill="#004d40" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif">{pl} x {pw}</text>'
                
            svg += '</svg>'
            st.markdown(svg, unsafe_allow_html=True)
