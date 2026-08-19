import streamlit as st
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import io
import os
import requests

# ==================== 中文字体加载 ====================
def get_chinese_font():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, 'fonts', 'chinesefont.otf')
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        return prop.get_name()
    else:
        fonts = [f.name for f in fm.fontManager.ttflist]
        for font in ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS']:
            if font in fonts:
                return font
        return 'DejaVu Sans'

plt.rcParams['font.sans-serif'] = [get_chinese_font()]
plt.rcParams['axes.unicode_minus'] = False

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="周易蓍(shī)草占筮 · 亲自参与推演",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== 蓍草长度对应像素 ====================
# 用于按钮/方框位置的精确移动
STICK_LEN_PX = 35

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("🤖 AI 解卦（可选）")
    use_ai = st.checkbox("启用 AI 白话解卦")
    deepseek_key = None
    if use_ai:
        deepseek_key = st.text_input("DeepSeek API Key", type="password")

    st.divider()
    st.subheader("🛠️ 布局调试")
    debug_grid = st.checkbox("显示网格虚线及坐标", value=False)

    st.divider()
    st.subheader("🎛️ 按钮样式自定义")
    st.caption("调整推演操作按钮的尺寸和外观")
    btn_font_size = st.slider("按钮字体大小 (px)", 14, 24, 18, key="btn_font_size")
    btn_padding_y = st.slider("按钮上下内边距 (px)", 6, 20, 12, key="btn_padding_y")
    btn_margin_bottom = st.slider("按钮下外边距 (px)", 0, 20, 8, key="btn_margin_bottom")
    btn_border_radius = st.slider("按钮圆角 (px)", 0, 20, 8, key="btn_border_radius")
    btn_width_factor = st.slider("按钮宽度扩大倍数", 1, 10, 6, key="btn_width_factor")

    st.divider()
    st.subheader("🎯 各阶段按钮位置独立微调")
    if "phase_offsets" not in st.session_state:
        st.session_state.phase_offsets = {
            "stepB": -20,
            "stepC": -20,
            "stepD_group": -20,
            "stepD_rem": -40,
            "stepE_group": -20,
            "stepE_rem": -40,
            "stepF": -40,
            "stepI": -20
        }
    phase_options = ["stepB", "stepC", "stepD_group", "stepD_rem", "stepE_group", "stepE_rem", "stepF", "stepI"]
    phase_to_adjust = st.selectbox("选择阶段", phase_options)
    current_offset = st.session_state.phase_offsets.get(phase_to_adjust, -20)
    new_offset = st.slider("该阶段按钮上偏移 (px)", -100, 100, current_offset)
    st.session_state.phase_offsets[phase_to_adjust] = new_offset

# ==================== 动态生成基础 CSS ====================
btn_width_css = f"min(100%, {btn_width_factor * 100}px)"
st.markdown(f"""
<style>
    :root {{
        --btn-font-size: {btn_font_size}px;
        --btn-padding-y: {btn_padding_y}px;
        --btn-margin-bottom: {btn_margin_bottom}px;
        --btn-border-radius: {btn_border_radius}px;
        --btn-width: {btn_width_css};
    }}
    .stButton > button {{
        width: var(--btn-width);
        font-size: var(--btn-font-size);
        padding: var(--btn-padding-y) 12px;
        border-radius: var(--btn-border-radius);
        margin: 0 auto var(--btn-margin-bottom) auto;
        margin-left: auto !important;
        margin-right: auto !important;
        background-color: rgba(255, 255, 255, 0.05);
        border: 2px solid rgba(0, 0, 0, 0.3);
        color: rgba(0, 0, 0, 0.8);
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        white-space: pre-wrap;
        height: auto;
        overflow: visible;
        line-height: 2;
        flex-direction: column;
    }}
    .stButton > button:hover {{
        background-color: rgba(255, 255, 255, 0.25);
        border: 2px solid rgba(0, 0, 0, 0.6);
        color: rgba(0, 0, 0, 1);
    }}
    .stButton > button::before,
    .stButton > button::after {{
        content: none !important;
        display: none !important;
    }}
    .stTextArea textarea, .stTextInput input {{
        font-size: 16px;
    }}
    h3, h4 {{
        margin-top: 0.8rem !important;
        margin-bottom: 0.5rem !important;
    }}
    p {{
        margin: 0.5rem 0 !important;
    }}
    @media (max-width: 768px) {{
        :root {{
            --btn-font-size: {max(20, btn_font_size)}px;
            --btn-padding-y: {max(14, btn_padding_y)}px;
            --btn-width: 100%;
        }}
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}
        .stButton > button {{
            font-size: var(--btn-font-size);
            padding: var(--btn-padding-y) 12px;
            width: 100%;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# ==================== 64卦数据库 ====================
HEXAGRAM_DATA = {
    "111111": ("乾为天", "元亨利贞。"),
    "000000": ("坤为地", "元亨，利牝马之贞。"),
    "100010": ("水雷屯", "元亨利贞，勿用有攸往，利建侯。"),
    "010001": ("山水蒙", "亨。匪我求童蒙，童蒙求我。"),
    "111010": ("水天需", "有孚，光亨，贞吉，利涉大川。"),
    "010111": ("天水讼", "有孚窒惕，中吉，终凶。利见大人，不利涉大川。"),
    "010000": ("地水师", "贞，丈人吉，无咎。"),
    "000010": ("水地比", "吉。原筮，元永贞，无咎。"),
    "111011": ("风天小畜", "亨。密云不雨，自我西郊。"),
    "110111": ("天泽履", "履虎尾，不咥人，亨。"),
    "111000": ("地天泰", "小往大来，吉亨。"),
    "000111": ("天地否", "否之匪人，不利君子贞，大往小来。"),
    "101111": ("天火同人", "同人于野，亨。利涉大川，利君子贞。"),
    "111101": ("火天大有", "元亨。"),
    "001000": ("地山谦", "亨，君子有终。"),
    "000100": ("雷地豫", "利建侯行师。"),
    "100110": ("泽雷随", "元亨利贞，无咎。"),
    "011001": ("山风蛊", "元亨，利涉大川。先甲三日，后甲三日。"),
    "110000": ("地泽临", "元亨利贞。至于八月有凶。"),
    "000011": ("风地观", "盥而不荐，有孚颙若。"),
    "100101": ("火雷噬嗑", "亨。利用狱。"),
    "101001": ("山火贲", "亨。小利有攸往。"),
    "000001": ("山地剥", "不利有攸往。"),
    "100000": ("地雷复", "亨。出入无疾，朋来无咎。"),
    "100111": ("天雷无妄", "元亨利贞。其匪正有眚，不利有攸往。"),
    "111001": ("山天大畜", "利贞，不家食吉，利涉大川。"),
    "100001": ("山雷颐", "贞吉。观颐，自求口实。"),
    "011110": ("泽风大过", "栋桡，利有攸往，亨。"),
    "010010": ("坎为水", "习坎，有孚，维心亨，行有尚。"),
    "101101": ("离为火", "利贞，亨。畜牝牛，吉。"),
    "001110": ("泽山咸", "亨利贞，取女吉。"),
    "011100": ("雷风恒", "亨，无咎，利贞，利有攸往。"),
    "001111": ("天山遁", "亨，小利贞。"),
    "111100": ("雷天大壮", "利贞。"),
    "000101": ("火地晋", "康侯用锡马蕃庶，昼日三接。"),
    "101000": ("地火明夷", "利艰贞。"),
    "101011": ("风火家人", "利女贞。"),
    "110101": ("火泽睽", "小事吉。"),
    "001010": ("水山蹇", "利西南，不利东北。利见大人，贞吉。"),
    "010100": ("雷水解", "利西南，无所往，其来复吉。有攸往，夙吉。"),
    "110001": ("山泽损", "有孚，元吉，无咎，可贞，利有攸往。"),
    "100011": ("风雷益", "利有攸往，利涉大川。"),
    "111110": ("泽天夬", "扬于王庭，孚号有厉。告自邑，不利即戎，利有攸往。"),
    "011111": ("天风姤", "女壮，勿用取女。"),
    "000110": ("泽地萃", "亨。王假有庙，利见大人，亨，利贞。用大牲吉，利有攸往。"),
    "011000": ("地风升", "元亨，用见大人，勿恤，南征吉。"),
    "010110": ("泽水困", "亨，贞，大人吉，无咎。有言不信。"),
    "011010": ("水风井", "改邑不改井，无丧无得，往来井井。汔至亦未繘井，羸其瓶，凶。"),
    "101110": ("泽火革", "己日乃孚，元亨利贞，悔亡。"),
    "011101": ("火风鼎", "元吉，亨。"),
    "100100": ("震为雷", "亨。震来虩虩，笑言哑哑。震惊百里，不丧匕鬯。"),
    "001001": ("艮为山", "艮其背，不获其身，行其庭，不见其人，无咎。"),
    "001011": ("风山渐", "女归吉，利贞。"),
    "110100": ("雷泽归妹", "征凶，无攸利。"),
    "101100": ("雷火丰", "亨，王假之，勿忧，宜日中。"),
    "001101": ("火山旅", "小亨，旅贞吉。"),
    "011011": ("巽为风", "小亨，利有攸往，利见大人。"),
    "110110": ("兑为泽", "亨，利贞。"),
    "010011": ("风水涣", "亨。王假有庙，利涉大川，利贞。"),
    "110010": ("水泽节", "亨。苦节不可贞。"),
    "110011": ("风泽中孚", "豚鱼吉，利涉大川，利贞。"),
    "001100": ("雷山小过", "亨，利贞。可小事，不可大事。"),
    "101010": ("水火既济", "亨，小利贞。初吉终乱。"),
    "010101": ("火水未济", "亨。小狐汔济，濡其尾，无攸利。"),
}

# ==================== 绘图函数 ====================
def show_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    st.image(buf, use_container_width=True)

def draw_initial_bunch(total=50, highlight_index=None, title_text='已经为您准备好50根蓍草',
                       dx=0, dy=0, shift_x=0, shift_y=0):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(shift_x, 10 + shift_x)
    ax.set_ylim(shift_y, 9 + shift_y)
    ax.axis('off')
    ax.text(5 + dx + shift_x, 7.5 + dy + shift_y, title_text,
            fontsize=22, ha='center', va='center')

    cols_per_row = 20
    rows = 3
    x_step = 0.3
    y_step = 1.5
    start_x = 1.4 + shift_x
    start_y = 6.5 + shift_y

    for i in range(total):
        row = i // cols_per_row
        col = i % cols_per_row
        x = start_x + col * x_step
        y = start_y - row * y_step
        color = 'red' if (highlight_index is not None and i == highlight_index) else 'forestgreen'
        ax.plot([x, x], [y, y+1], color=color, linewidth=5)
    return fig

def draw_state(yao_index, change_index, total_sticks, left, right, left_rem, right_rem,
               hand_person, hand_rem, taiji_collected, show_left_groups=False, show_right_groups=False,
               show_grid=False):
    stick_len = 1.0
    margin_side = 0.3 * stick_len
    margin_top = 0.3 * stick_len
    row_spacing = stick_len + 0.3 * stick_len
    text_bottom_offset = 0.2 * stick_len

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11.5)

    if show_grid:
        ax.set_xticks(range(0, 19, 1))
        ax.set_yticks(range(0, 12, 1))
        ax.grid(True, linestyle='--', alpha=0.6, linewidth=0.5)
        ax.tick_params(labelsize=8)
        ax.set_xlabel('X 坐标', fontsize=10)
        ax.set_ylabel('Y 坐标', fontsize=10)
        ax.set_axisbelow(True)
    else:
        ax.axis('off')

    box_y = 6.0
    box_h = 3.0
    label_y_top = 9.3
    lower_y = 2.0
    lower_h = 2.5
    gap = 1.0

    left_box_w = 7.5
    right_box_w = 7.5
    person_w = 4.5

    left_box_x = 0.0
    right_box_x = left_box_x + left_box_w + 1.5

    person_x = left_box_x
    taiji_w = (right_box_x + right_box_w) - (person_x + person_w + gap)
    taiji_x = person_x + person_w + gap

    ax.add_patch(patches.Rectangle((left_box_x, box_y), left_box_w, box_h, fill=False, edgecolor='black', lw=2))
    ax.text(left_box_x + left_box_w/2, label_y_top, '天（左堆）', fontsize=21, ha='center', weight='bold')

    ax.add_patch(patches.Rectangle((right_box_x, box_y), right_box_w, box_h, fill=False, edgecolor='black', lw=2))
    ax.text(right_box_x + right_box_w/2, label_y_top, '地（右堆）', fontsize=21, ha='center', weight='bold')

    ax.add_patch(patches.Rectangle((person_x, lower_y), person_w, lower_h, fill=False, edgecolor='black', lw=2))
    ax.text(person_x + person_w/2, lower_y + lower_h + 0.3, '人（左手）', fontsize=21, ha='center', weight='bold')

    ax.add_patch(patches.Rectangle((taiji_x, lower_y), taiji_w, lower_h, fill=False, edgecolor='black', lw=2))
    ax.text(taiji_x + taiji_w/2, lower_y + lower_h + 0.3, '太极与归奇', fontsize=21, ha='center', weight='bold')

    info_y = 10.8
    ax.text(9.0, info_y, f'当前参与推演的蓍草根数：{total_sticks} 根',
            fontsize=21, ha='center', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

    tai_ji_x_pos = taiji_x + 0.8
    text_bottom = lower_y + text_bottom_offset
    text_height = 0.4
    text_top = text_bottom + text_height
    tai_ji_bottom = text_top + 0.3 * stick_len
    tai_ji_top = tai_ji_bottom + stick_len
    ax.plot([tai_ji_x_pos, tai_ji_x_pos], [tai_ji_bottom, tai_ji_top],
            color='red', linewidth=4, solid_capstyle='butt')
    ax.text(tai_ji_x_pos, text_bottom, '太极',
            fontsize=21, ha='center', va='bottom', color='red')

    max_cols_taiji = 25
    gui_qi_start_x = tai_ji_x_pos + 0.8
    taiji_x_step = 0.35
    taiji_row_spacing = row_spacing
    first_row_bottom_taiji = tai_ji_bottom
    for i in range(taiji_collected):
        row = i // max_cols_taiji
        col = i % max_cols_taiji
        x = gui_qi_start_x + col * taiji_x_step
        y = first_row_bottom_taiji - row * taiji_row_spacing
        ax.plot([x, x], [y, y + stick_len], color='gray', linewidth=4)

    left_region_x = left_box_x + margin_side
    region_y_top = box_y + box_h - margin_top - stick_len
    max_cols_per_row = 24
    for i in range(left):
        if i < max_cols_per_row:
            row = 0
            col = i
        else:
            row = 1
            col = i - max_cols_per_row
        x = left_region_x + col * 0.25
        y = region_y_top - row * row_spacing
        color = 'gold' if left_rem > 0 and i >= left - left_rem else 'forestgreen'
        ax.plot([x, x], [y, y + stick_len], color=color, linewidth=4)

    if show_left_groups and left > 0:
        for k in range(4, left, 4):
            if k < max_cols_per_row:
                row = 0
                col = k
            else:
                row = 1
                col = k - max_cols_per_row
            x_line = left_region_x + col * 0.25 - 0.125
            y_line = region_y_top - row * row_spacing
            ax.axvline(x=x_line, ymin=(y_line - 0.1) / 11.5, ymax=(y_line + 1.1) / 11.5,
                       color='red', linestyle='--', linewidth=1)

    right_region_x = right_box_x + margin_side
    for i in range(right):
        if i < max_cols_per_row:
            row = 0
            col = i
        else:
            row = 1
            col = i - max_cols_per_row
        x = right_region_x + col * 0.25
        y = region_y_top - row * row_spacing
        color = 'gold' if right_rem > 0 and i >= right - right_rem else 'forestgreen'
        ax.plot([x, x], [y, y + stick_len], color=color, linewidth=4)

    if show_right_groups and right > 0:
        for k in range(4, right, 4):
            if k < max_cols_per_row:
                row = 0
                col = k
            else:
                row = 1
                col = k - max_cols_per_row
            x_line = right_region_x + col * 0.25 - 0.125
            y_line = region_y_top - row * row_spacing
            ax.axvline(x=x_line, ymin=(y_line - 0.1) / 11.5, ymax=(y_line + 1.1) / 11.5,
                       color='red', linestyle='--', linewidth=1)

    hand_region_x = person_x + margin_side
    hand_region_top = lower_y + lower_h - margin_top - stick_len
    max_cols_hand = 13
    hand_total = hand_person + hand_rem
    for i in range(hand_total):
        row = i // max_cols_hand
        col = i % max_cols_hand
        x = hand_region_x + col * 0.25
        y = hand_region_top - row * row_spacing
        color = 'purple' if i < hand_person else 'darkviolet'
        ax.plot([x, x], [y, y + stick_len], color=color, linewidth=4)

    if show_grid:
        ax.text(left_box_x, box_y + box_h + 0.2, f'({left_box_x},{box_y})', fontsize=8, ha='left')
        ax.text(right_box_x, box_y + box_h + 0.2, f'({right_box_x},{box_y})', fontsize=8, ha='left')
        ax.text(person_x, lower_y - 0.3, f'({person_x},{lower_y})', fontsize=8, ha='left')
        ax.text(taiji_x, lower_y - 0.3, f'({taiji_x},{lower_y})', fontsize=8, ha='left')

    return fig

# ==================== 解卦工具 ====================
YAO_NAMES = {6: "老阴⚋(变)", 7: "少阳⚊", 8: "少阴⚋", 9: "老阳⚊(变)"}
SIMPLE_YAO_NAMES = {6: "老阴⚋", 7: "少阳⚊", 8: "少阴⚋", 9: "老阳⚊"}

def draw_yao(yao):
    return "━━━━━" if yao in (7, 9) else "━━ ━━"

def interpret(yao_list):
    orig_bin = ''.join('1' if y in (7, 9) else '0' for y in yao_list)
    changed_bin = ''.join('1' if y == 6 else ('0' if y == 9 else '1' if y == 7 else '0') for y in yao_list)
    orig = HEXAGRAM_DATA.get(orig_bin, ("未知卦", ""))
    changed = HEXAGRAM_DATA.get(changed_bin, ("未知卦", ""))
    pos = [i + 1 for i, y in enumerate(yao_list) if y in (6, 9)]
    lines = [draw_yao(y) + (f"  ← 第{i+1}爻变" if y in (6, 9) else "") for i, y in enumerate(yao_list)]
    lines.reverse()
    return "\n".join(lines), orig, changed, pos

# ==================== AI 接口 ====================
def call_deepseek(prompt, api_key):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"DeepSeek 错误：{resp.status_code}"
    except Exception as e:
        return f"请求异常：{e}"

# ==================== 状态管理 ====================
def advance_phase():
    phase = st.session_state.app_phase
    if phase == "preparation":
        st.session_state.app_phase = "question"
        st.session_state.all_complete = False
        st.session_state.show_detailed_result = False
    elif phase == "question":
        st.session_state.app_phase = "ready"
    elif phase == "ready":
        st.session_state.taiji_stick_index = random.randint(0, 49)
        st.session_state.app_phase = "stepA"
    elif phase == "stepA":
        st.session_state.total_sticks = 49
        st.session_state.app_phase = "stepB"
    elif phase == "stepB":
        sticks = st.session_state.total_sticks
        L = random.randint(1, sticks - 1)
        R = sticks - L
        st.session_state.left = L
        st.session_state.right = R
        st.session_state.left_rem = 0
        st.session_state.right_rem = 0
        st.session_state.hand_person = 0
        st.session_state.hand_rem = 0
        st.session_state.app_phase = "stepC"
    elif phase == "stepC":
        st.session_state.right -= 1
        st.session_state.hand_person = 1
        st.session_state.app_phase = "stepD_group"
    elif phase == "stepD_group":
        st.session_state.app_phase = "stepD_rem"
    elif phase == "stepD_rem":
        left = st.session_state.left
        rem = left % 4
        if rem == 0:
            rem = 4
        st.session_state.left_rem = rem
        st.session_state.hand_rem += rem
        st.session_state.app_phase = "stepE_group"
    elif phase == "stepE_group":
        st.session_state.app_phase = "stepE_rem"
    elif phase == "stepE_rem":
        right = st.session_state.right
        rem = right % 4
        if rem == 0:
            rem = 4
        st.session_state.right_rem = rem
        st.session_state.hand_rem += rem
        st.session_state.app_phase = "stepF"
    elif phase == "stepF":
        total_hand = st.session_state.hand_person + st.session_state.hand_rem
        st.session_state.taiji_collected += total_hand
        new_sticks = st.session_state.total_sticks - total_hand
        st.session_state.total_sticks = new_sticks
        st.session_state.left = 0
        st.session_state.right = 0
        st.session_state.left_rem = 0
        st.session_state.right_rem = 0
        st.session_state.hand_person = 0
        st.session_state.hand_rem = 0
        if st.session_state.change_index == 3:
            st.session_state.left = new_sticks // 2 + new_sticks % 2
            st.session_state.right = new_sticks // 2
            st.session_state.app_phase = "stepI"
        else:
            st.session_state.change_index += 1
            st.session_state.app_phase = "stepB"
    elif phase == "stepI":
        groups = st.session_state.total_sticks // 4
        yao_num = groups
        st.session_state.yao_results.append(yao_num)
        if st.session_state.yao_index < 5:
            st.session_state.yao_index += 1
            st.session_state.total_sticks = 49
            st.session_state.change_index = 1
            st.session_state.left = 0
            st.session_state.right = 0
            st.session_state.left_rem = 0
            st.session_state.right_rem = 0
            st.session_state.hand_person = 0
            st.session_state.hand_rem = 0
            st.session_state.taiji_collected = 0
            st.session_state.app_phase = "stepB"
        else:
            st.session_state.all_complete = True
            st.session_state.show_detailed_result = False
            st.session_state.app_phase = "stepI"

# ==================== 主程序 ====================
if "app_phase" not in st.session_state:
    st.session_state.app_phase = "preparation"
    st.session_state.question = ""
    st.session_state.yao_results = []
    st.session_state.yao_index = 0
    st.session_state.change_index = 1
    st.session_state.total_sticks = 49
    st.session_state.left = 0
    st.session_state.right = 0
    st.session_state.left_rem = 0
    st.session_state.right_rem = 0
    st.session_state.hand_person = 0
    st.session_state.hand_rem = 0
    st.session_state.taiji_collected = 0
    st.session_state.taiji_stick_index = None
    st.session_state.all_complete = False
    st.session_state.show_detailed_result = False

phase = st.session_state.app_phase

# ==================== 相位特定 CSS（推演阶段按钮放大加粗，整体上移1.5倍，右侧框左移5倍） ====================
if phase in ["stepB", "stepC", "stepD_group", "stepD_rem", "stepE_group", "stepE_rem", "stepF", "stepI"]:
    st.markdown("""
    <style>
        .stButton {
            height: 100%;
            display: flex;
            align-items: stretch;
        }
        .stButton > button {
            height: auto !important;
            width: var(--btn-width);
            font-size: 24px !important;
            font-weight: bold !important;
            padding: var(--btn-padding-y) 12px;
            border-radius: var(--btn-border-radius);
            margin: 0 auto var(--btn-margin-bottom) auto;
            margin-left: auto !important;
            margin-right: auto !important;
            background-color: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(0, 0, 0, 0.3);
            color: rgba(0, 0, 0, 0.8);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            transform: translate(0px, -70px) !important;
            white-space: pre-wrap;
            overflow: visible !important;
            line-height: 2;
            flex-direction: column;
        }
        .stButton > button:hover {
            background-color: rgba(255, 255, 255, 0.25);
            border: 2px solid rgba(0, 0, 0, 0.6);
            color: rgba(0, 0, 0, 1);
        }
        .stButton > button::before,
        .stButton > button::after {
            content: none !important;
            display: none !important;
        }
        .right-content {
            transform: translate(-140px, -105px);
        }
        .complete-content {
            transform: translate(-140px, -70px);
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================== 标题 ====================
st.markdown("<h3 style='margin-top: 0.5rem; margin-bottom:0;'>🌿 周易蓍(shī)草占筮 · 古法亲手推演</h3>", unsafe_allow_html=True)

if phase not in ["preparation", "question"]:
    question_display = st.session_state.question.strip() if st.session_state.question.strip() else "（尚未填写）"
    st.markdown(f"<p style='margin-top:0; margin-bottom:0;'><b>🧘 耐心虔诚。心中默念所求之事：{question_display}</b></p>", unsafe_allow_html=True)

# ==================== 阶段0：准备仪式 ====================
if phase == "preparation":
    st.markdown("## 🪷 仪式准备")
    st.markdown("**请沐浴更衣、洗手静心，虔心端坐，诚心诚意。**")
    st.markdown("**请确认已做好身心准备，再进入下一步写下心中所问之事。**")
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        .stButton > button {
            font-size: calc(0.75 * var(--btn-font-size)) !important;
            margin-top: -20px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("☯️ 我已准备好  心中默念所求之事\n☯️ 请虔心点按此处进行下一步"):
        advance_phase()
        st.rerun()

# ==================== 阶段1：输入问题 ====================
elif phase == "question":
    st.markdown("## 🔮 静心凝神，写下心中所问")
    question = st.text_area("所求之事", placeholder="例如：这次工作是否顺利？")
    st.markdown("<div style='margin-top: 2em;'></div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        .stButton > button {
            font-size: calc(0.75 * var(--btn-font-size)) !important;
            margin-top: -20px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("☯️ 心意已定  备蓍起卦\n☯️ 请虔心点按此处进入下一步"):
        if question.strip() == "":
            st.warning("请先填写所求之事。")
        else:
            st.session_state.question = question
            st.session_state.app_phase = "ready"
            st.rerun()

# ==================== 阶段2：准备蓍草 ====================
elif phase == "ready":
    st.subheader("🪷 备蓍")
    st.info(f"心中默念：**{st.session_state.question}**")
    fig = draw_initial_bunch(50, title_text='已经为您准备好50根蓍草', dx=-0.5, dy=1.0, shift_x=-3)
    show_fig(fig)
    st.markdown("""
    <style>
        div[data-testid="stButton"] button {
            margin-top: -90px !important;
        }
        .stButton > button {
            font-size: calc(0.75 * var(--btn-font-size)) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    if st.button("☯️ 开始取太极\n☯️ 请虔心点按此处进入下一步"):
        advance_phase()
        st.rerun()

# ==================== 阶段3：取太极 ====================
elif phase == "stepA":
    st.subheader("☯️ 取太极")
    st.markdown("**已经为您从50根蓍草中取出1根代表太极、不易、坚强意志。**")
    st.caption("图中红色蓍草为随机选中的太极。")
    fig = draw_initial_bunch(50, highlight_index=st.session_state.taiji_stick_index,
                             title_text='已为您取太极', dx=-0.5, dy=1.0, shift_x=-3)
    show_fig(fig)
    st.markdown("""
    <style>
        div[data-testid="stButton"] button {
            margin-top: -90px !important;
        }
        .stButton > button {
            font-size: calc(0.75 * var(--btn-font-size)) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    if st.button("☯️ 已取太极  意志坚定  开始卜卦\n☯️ 请虔心点按此处进入下一步"):
        advance_phase()
        st.rerun()

# ==================== 阶段4：推演过程 ====================
elif phase in ["stepB", "stepC", "stepD_group", "stepD_rem", "stepE_group", "stepE_rem", "stepF", "stepI"]:
    idx = st.session_state.yao_index
    ch = st.session_state.change_index
    sticks = st.session_state.total_sticks
    left = st.session_state.left
    right = st.session_state.right
    lr = st.session_state.left_rem
    rr = st.session_state.right_rem
    hp = st.session_state.hand_person
    hr = st.session_state.hand_rem
    taiji = st.session_state.taiji_collected
    all_complete = st.session_state.all_complete
    show_detailed = st.session_state.show_detailed_result

    # 定义每个阶段的说明文字和操作名
    phase_info = {
        "stepB": ("将蓍草随机分为左右两堆（分天地）", "分二"),
        "stepC": ("从右堆中取出1根挂于左手", "挂一"),
        "stepD_group": ("将左堆4根一组进行分组", "揲左"),
        "stepD_rem": ("左堆分组完毕，请将余下蓍草挂于左手", "取余"),
        "stepE_group": ("将右堆4根一组进行分组", "揲右"),
        "stepE_rem": ("右堆分组完毕，请将余下蓍草挂于左手", "取余"),
        "stepF": ("将左手所挂蓍草归置于太极旁", "归奇"),
        "stepI": ("三次推演完成，请查看得爻结果", "得爻"),
    }

    # 按钮文本逻辑
    if all_complete:
        if show_detailed:
            btn_label = "☯️ 查看卦象"
        else:
            btn_label = "☯️ 完成六爻推演"
        full_label = btn_label
    else:
        desc_text, op_name = phase_info.get(phase, ("", ""))
        full_label = (
            f"{desc_text}\n"
            f"☯️  {op_name}  ☯️\n\n"
            f"心中默念所求之事\n"
            f"请虔心点按此框任意位置卜卦"
        )

    st.markdown(f"<h3 style='margin-bottom:0;'>第{idx+1}爻 · 第{ch}变</h3>", unsafe_allow_html=True)

    show_l = (phase in ["stepD_group", "stepD_rem", "stepI"])
    show_r = (phase in ["stepE_group", "stepE_rem", "stepI"])
    fig = draw_state(idx, ch, sticks, left, right, lr, rr, hp, hr, taiji, show_l, show_r,
                     show_grid=debug_grid)
    show_fig(fig)

    yao_results = st.session_state.yao_results
    chinese_nums = ["一", "二", "三", "四", "五", "六"]

    phase_offset = st.session_state.phase_offsets.get(phase, -20)

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        # “将蓍草随机分为左右两堆（分天地）”按钮向下移动1倍蓍草长度
        if phase == "stepB":
            button_spacer_height = phase_offset + STICK_LEN_PX
        else:
            button_spacer_height = phase_offset
        st.markdown(f"<div style='height: {button_spacer_height}px;'></div>", unsafe_allow_html=True)
        if st.button(full_label, key=f"btn_{phase}_{idx}_{ch}"):
            if all_complete:
                if show_detailed:
                    st.session_state.app_phase = "result"
                    st.rerun()
                else:
                    st.session_state.show_detailed_result = True
                    st.rerun()
            else:
                advance_phase()
                st.rerun()
    with col2:
        st.markdown(f"<div style='height: {phase_offset}px;'></div>", unsafe_allow_html=True)
        # 统一显示已得之爻（按第六→第一的顺序）
        lines = []
        for i in range(len(yao_results)-1, -1, -1):
            label = f"第{chinese_nums[i]}爻"
            value = SIMPLE_YAO_NAMES.get(yao_results[i], "未知")
            lines.append(f"{label}：{value}")
        yao_text = "☯️ 所得之爻<br>" + "<br>".join(lines) if lines else "（暂无已得之爻）"
        st.markdown(f'''
        <div class="right-content" style="width: fit-content; margin-left: auto; margin-right: 0; text-align: left; border: 2px solid #555; border-radius: 8px; padding: 8px 12px; min-height: 200px; display: flex; flex-direction: column; justify-content: center;">
            {yao_text}
        </div>
        ''', unsafe_allow_html=True)

    # 得爻详情显示（带方框）- 仅当未完成时显示，左侧对齐人（左手）框
    if phase == "stepI" and not all_complete:
        left_groups = left // 4
        right_groups = right // 4
        total_groups = left_groups + right_groups
        yin_yang = "阳" if total_groups % 2 == 1 else "阴"
        yao_name = SIMPLE_YAO_NAMES.get(total_groups, "未知")
        st.markdown(f"""
        <div style='margin-top: 1em; margin-left: 0; margin-right: auto; width: fit-content; text-align: left; transform: translate(0px, -80px); border: 2px solid #555; border-radius: 8px; padding: 12px 16px;'>
        ☯  得爻：<br>
        左堆（天）：{left} 根，{left_groups} 组（每组4根）。<br>
        右堆（地）：{right} 根，{right_groups} 组（每组4根）。<br>
        组数：{left_groups} + {right_groups} = {total_groups} 。<br>
        规则：组数为奇（7或9）则阳，偶（6或8）则阴。<br>
        当前组数 {total_groups}，为 {yin_yang}，所得爻为 {yao_name}。
        </div>
        """, unsafe_allow_html=True)

# ==================== 阶段5：占卜结果 ====================
elif phase == "result":
    yao_list = st.session_state.yao_results
    if len(yao_list) < 6:
        st.warning("尚未完成六爻，请返回")
        st.stop()

    disp, orig, changed, pos = interpret(yao_list)

    st.markdown("## 🪷 卦象与卦辞")

    st.markdown(f"**本卦  {orig[0]}**：{orig[1]}")
    st.code(disp, language="")

    if pos:
        changed_lines = [draw_yao(9 if y == 6 else (6 if y == 9 else y)) for y in reversed(yao_list)]
        st.markdown(f"**变卦  {changed[0]}**：{changed[1]}")
        st.code("\n".join(changed_lines), language="")
        st.write(f"变爻位置（自下而上）：第 {', '.join(map(str, pos))} 爻")
        if len(pos) == 1:
            st.info("一爻变，以本卦变爻爻辞为主。")
        else:
            st.info("多爻变，以本卦卦辞为主，兼看之卦卦辞。")
    else:
        st.info("静卦（无变爻），以本卦卦辞为主。")

    if use_ai and deepseek_key:
        prompt = f"用户问题：{st.session_state.question}\n本卦：{orig[0]}（{orig[1]}）"
        if pos:
            prompt += f"\n变卦：{changed[0]}（{changed[1]}），变爻：{pos}"
        prompt += "\n请作为易经专家，用白话给出通俗解读与建议。"
        with st.spinner("DeepSeek 正在解卦..."):
            ai_reply = call_deepseek(prompt, deepseek_key)
        st.subheader("🤖 AI 解读")
        st.write(ai_reply)

    st.markdown("---")
    st.markdown("☯ **如需详细解卦，请联系博主，微信号码：AlexanderXG**")
    st.markdown(
        '<div style="font-size: 2em; line-height: 2; font-weight: bold; text-align: center; margin-top: 20px;">☯️  卦礼随缘  ☯️</div>',
        unsafe_allow_html=True
    )
