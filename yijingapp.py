import streamlit as st
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import io
import os
import requests

# ==================== 中文字体加载（使用项目内字体文件） ====================
def get_chinese_font():
    """加载项目 fonts 目录下的中文字体文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, 'fonts', 'chinesefont.otf')
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        return prop.get_name()
    else:
        # 备选：尝试系统字体
        fonts = [f.name for f in fm.fontManager.ttflist]
        for font in ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS']:
            if font in fonts:
                return font
        return 'DejaVu Sans'

# 设置全局中文字体
plt.rcParams['font.sans-serif'] = [get_chinese_font()]
plt.rcParams['axes.unicode_minus'] = False

# ==================== 页面配置（移动端优化） ====================
st.set_page_config(
    page_title="周易蓍草占筮 · 亲手推演",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== 移动端 CSS 样式（优化版） ====================
st.markdown("""
<style>
    /* 按钮全宽，易点击 */
    .stButton > button {
        width: 100%;
        font-size: 18px;
        padding: 12px;
        border-radius: 8px;
        margin: 15px 0 8px 0;  /* 上边距加大，下边距适中 */
    }
    /* 输入框字体 */
    .stTextArea textarea, .stTextInput input {
        font-size: 16px;
    }
    /* 标题间距 */
    h3, h4 {
        margin-top: 0.8rem !important;
        margin-bottom: 0.5rem !important;
    }
    /* 段落间距调整 */
    p {
        margin: 0.5rem 0 !important;
    }
    /* 移动端边距调整 */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 2rem !important;   /* 增大顶部内边距，让标题完全显示 */
            padding-bottom: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* 按钮在手机上更大一点 */
        .stButton > button {
            font-size: 20px;
            padding: 14px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 64卦完整数据库 ====================
# 键为六爻阴阳标记（自下而上，1=阳，0=阴），值为（卦名，卦辞）
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
    """将 Matplotlib 图转为 PNG 并显示，自适应宽度"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    st.image(buf, use_container_width=True)

def draw_initial_bunch(total=50, highlight_index=None, title_text='已为您备好50根蓍草'):
    """整齐排列50根蓍草：5排，每排10根，水平间距0.8，垂直间距1.5
       highlight_index: 若提供，则该索引的蓍草绘制为红色（太极）
       title_text: 图片顶部显示的文字
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.text(5, 8.0, title_text, fontsize=14, ha='center', va='bottom')

    cols_per_row = 10
    rows = 5
    x_step = 0.8
    y_step = 1.5
    start_x = 1.4
    start_y = 6.5

    for i in range(total):
        row = i // cols_per_row
        col = i % cols_per_row
        x = start_x + col * x_step
        y = start_y - row * y_step
        color = 'red' if (highlight_index is not None and i == highlight_index) else 'forestgreen'
        ax.plot([x, x], [y, y+1], color=color, linewidth=2)
    return fig

def draw_state(yao_index, change_index, total_sticks, left, right, left_rem, right_rem,
               hand_person, hand_rem, taiji_collected, show_left_groups=False, show_right_groups=False):
    """绘制推演状态图：行距1.2，蓍草下移1单位，距边框大于0.5
       太极与归奇画框水平居中，当前蓍草数文字水平居中
       人（左手）画框位于天（左堆）下方，与太极与归奇画框对齐
       人区域蓍草排布：第一根距上边框0.5倍蓍草长度，距左边框0.5倍蓍草长度，
       其余蓍草与天、地堆间距一致，行距1.2（蓍草长度1 + 间距0.2）
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # 区域边框（天、地）
    ax.add_patch(patches.Rectangle((0.5, 4.5), 5.5, 3.0, fill=False, edgecolor='black', lw=2))
    ax.text(3.25, 7.8, '天（左堆）', fontsize=14, ha='center', weight='bold')
    ax.add_patch(patches.Rectangle((7.5, 4.5), 5.5, 3.0, fill=False, edgecolor='black', lw=2))
    ax.text(10.25, 7.8, '地（右堆）', fontsize=14, ha='center', weight='bold')

    # 人（左手）画框
    ax.add_patch(patches.Rectangle((2.5, 1.0), 3.0, 2.5, fill=False, edgecolor='black', lw=2))
    ax.text(4.0, 3.8, '人（左手）', fontsize=14, ha='center', weight='bold')

    # 太极与归奇画框
    rect_x = 5.5
    rect_width = 7.0
    ax.add_patch(patches.Rectangle((rect_x, 1.0), rect_width, 2.5, fill=False, edgecolor='black', lw=2))
    ax.text(rect_x + rect_width/2, 3.8, '太极与归奇', fontsize=14, ha='center', weight='bold')

    # 太极单根
    tai_ji_x = rect_x + 1.0
    ax.plot([tai_ji_x, tai_ji_x], [1.5, 2.8], color='red', linewidth=4, solid_capstyle='butt')
    ax.text(tai_ji_x, 1.2, '太极', fontsize=14, ha='center', color='red')

    # 归奇蓍草
    max_cols_taiji = 25
    gui_qi_start_x = rect_x + 1.5
    for i in range(taiji_collected):
        row = i // max_cols_taiji
        col = i % max_cols_taiji
        x = gui_qi_start_x + col * 0.2
        y = 1.5 + row * 0.6
        ax.plot([x, x], [y, y+1.0], color='gray', linewidth=2)

    # 天、地、人堆统一参数
    heap_row_height = 1.2
    heap_x_step = 0.15
    max_cols_heaps = 30
    max_cols_hand = 13
    left_region_x = 1.0
    right_region_x = 8.0
    hand_region_x = 3.0
    region_y_top = 6.0
    hand_region_top = 2.0

    # 左堆
    for i in range(left):
        row = i // max_cols_heaps
        col = i % max_cols_heaps
        x = left_region_x + col * heap_x_step
        y = region_y_top - row * heap_row_height
        color = 'gold' if left_rem > 0 and i >= left - left_rem else 'forestgreen'
        ax.plot([x, x], [y, y+1.0], color=color, linewidth=2)

    if show_left_groups and left > 0:
        for k in range(4, left, 4):
            row = k // max_cols_heaps
            col = k % max_cols_heaps
            x_line = left_region_x + col * heap_x_step - heap_x_step/2
            y_line = region_y_top - row * heap_row_height
            ax.axvline(x=x_line, ymin=(y_line-0.1)/9, ymax=(y_line+1.1)/9,
                       color='gray', linestyle='--', linewidth=1)

    # 右堆
    for i in range(right):
        row = i // max_cols_heaps
        col = i % max_cols_heaps
        x = right_region_x + col * heap_x_step
        y = region_y_top - row * heap_row_height
        color = 'gold' if right_rem > 0 and i >= right - right_rem else 'forestgreen'
        ax.plot([x, x], [y, y+1.0], color=color, linewidth=2)

    if show_right_groups and right > 0:
        for k in range(4, right, 4):
            row = k // max_cols_heaps
            col = k % max_cols_heaps
            x_line = right_region_x + col * heap_x_step - heap_x_step/2
            y_line = region_y_top - row * heap_row_height
            ax.axvline(x=x_line, ymin=(y_line-0.1)/9, ymax=(y_line+1.1)/9,
                       color='gray', linestyle='--', linewidth=1)

    # 人（左手）区
    hand_total = hand_person + hand_rem
    for i in range(hand_total):
        row = i // max_cols_hand
        col = i % max_cols_hand
        x = hand_region_x + col * heap_x_step
        y = hand_region_top - row * heap_row_height
        color = 'purple' if i < hand_person else 'darkviolet'
        ax.plot([x, x], [y, y+1.0], color=color, linewidth=3)

    # 当前参与推演的蓍草根数
    ax.text(9.0, 0.5, f'当前参与推演的蓍草根数：{total_sticks} 根',
            fontsize=14, ha='center', bbox=dict(facecolor='white', alpha=0.8))

    return fig

# ==================== 解卦工具 ====================
YAO_NAMES = {6:"老阴⚋(变)",7:"少阳⚊",8:"少阴⚋",9:"老阳⚊(变)"}

def draw_yao(yao):
    return "━━━━━" if yao in (7, 9) else "━━ ━━"

def interpret(yao_list):
    # 本卦：yao_list 0=初爻，5=上爻
    orig_bin = ''.join('1' if y in (7,9) else '0' for y in yao_list)
    # 变卦：老阳(9)变阴(0)，老阴(6)变阳(1)
    changed_bin = ''.join('1' if y==6 else ('0' if y==9 else '1' if y==7 else '0') for y in yao_list)
    orig = HEXAGRAM_DATA.get(orig_bin, ("未知卦",""))
    changed = HEXAGRAM_DATA.get(changed_bin, ("未知卦",""))
    pos = [i+1 for i,y in enumerate(yao_list) if y in (6,9)]  # 变爻位置
    lines = [draw_yao(y) + (f"  ← 第{i+1}爻变" if y in (6,9) else "") for i,y in enumerate(yao_list)]
    lines.reverse()  # 变为上爻到初爻，便于打印
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

# ==================== 状态管理与推进逻辑 ====================
def advance_phase():
    phase = st.session_state.app_phase
    if phase == "preparation":
        st.session_state.app_phase = "question"
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
        L = random.randint(1, sticks-1)
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
        if rem == 0: rem = 4
        st.session_state.left_rem = rem
        st.session_state.hand_rem += rem
        st.session_state.app_phase = "stepE_group"
    elif phase == "stepE_group":
        st.session_state.app_phase = "stepE_rem"
    elif phase == "stepE_rem":
        right = st.session_state.right
        rem = right % 4
        if rem == 0: rem = 4
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
            st.session_state.app_phase = "result"

# ==================== 主程序 ====================
with st.sidebar:
    st.header("🤖 AI 解卦（可选）")
    use_ai = st.checkbox("启用 AI 白话解卦")
    deepseek_key = None
    if use_ai:
        deepseek_key = st.text_input("DeepSeek API Key", type="password")

# 初始化 session_state
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

phase = st.session_state.app_phase

# ==================== 紧凑布局标题 ====================
# 优化标题：增加上边距，防止被遮挡
st.markdown("<h3 style='margin-top: 0.5rem; margin-bottom:0;'>🌿 周易蓍草占筮 · 古法亲手推演</h3>", unsafe_allow_html=True)

# 顶部提醒（仅在问题提交后显示）
if phase not in ["preparation", "question"]:
    question_display = st.session_state.question.strip() if st.session_state.question.strip() else "（尚未填写）"
    st.markdown(f"<p style='margin-top:0; margin-bottom:0;'><b>🧘 耐心虔诚。心中默念所求之事：{question_display}</b></p>", unsafe_allow_html=True)

# 阶段0：准备仪式
if phase == "preparation":
    st.markdown("## 🪷 仪式准备")
    st.markdown("""
    **请沐浴更衣、洗手静心，虔心端坐，诚心诚意。**  
    确认已做好身心的准备后，再进入下一步写下心中所问之事。
    """)
    if st.button("🧘 我已准备好，开始默念所求"):
        advance_phase()
        st.rerun()

# 阶段1：输入问题
elif phase == "question":
    st.markdown("## 🔮 静心凝神，写下心中所问")
    question = st.text_area("所求之事", placeholder="例如：这次旅行是否顺利？")
    if st.button("✨ 心意已定，备蓍起卦"):
        if question.strip() == "":
            st.warning("请先填写所求之事。")
        else:
            st.session_state.question = question
            st.session_state.app_phase = "ready"
            st.rerun()

# 阶段2：准备蓍草（展示50根）
elif phase == "ready":
    st.subheader("🪷 备蓍")
    st.info(f"心中默念：**{st.session_state.question}**")
    fig = draw_initial_bunch(50)
    show_fig(fig)
    if st.button("🌱 开始取太极"):
        advance_phase()
        st.rerun()

# 阶段3：取太极
elif phase == "stepA":
    st.subheader("☯️ 步骤 A：取太极")
    st.markdown("请从50根中取出 **1根** 放在桌面前方，代表太极、不易、坚强意志。")
    st.caption("图中红色蓍草为随机选中的太极。")
    fig = draw_initial_bunch(50, highlight_index=st.session_state.taiji_stick_index, title_text='取太极')
    show_fig(fig)
    if st.button("☯️ 我已取出太极，意志坚定"):
        advance_phase()
        st.rerun()

# 阶段4：推演过程（stepB ~ stepI）
elif phase in ["stepB","stepC","stepD_group","stepD_rem","stepE_group","stepE_rem","stepF","stepI"]:
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

    prompts = {
        "stepB": ("分二", "将手中蓍草随机分为左右两堆（分天地）"),
        "stepC": ("挂一", "从右堆（地）中取出1根挂于左手（人）"),
        "stepD_group": ("揲左", "将左堆4根一组进行分组"),
        "stepD_rem": ("取余", "左堆分组完毕，请将余数挂于左手"),
        "stepE_group": ("揲右", "将右堆4根一组进行分组"),
        "stepE_rem": ("取余", "右堆分组完毕，请将余数挂于左手"),
        "stepF": ("归奇", "将左手所挂蓍草归置于太极旁"),
        "stepI": ("得爻", "三次推演完成，请查看天地组数"),
    }
    btn_label, desc = prompts.get(phase, ("继续", ""))

    # 紧凑显示阶段标题和描述
    st.markdown(f"<h3 style='margin-bottom:0;'>⚊ 第{idx+1}爻 · 第{ch}变</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:0; margin-bottom:0;'>{desc}</p>", unsafe_allow_html=True)

    show_l = (phase in ["stepD_group", "stepD_rem"])
    show_r = (phase in ["stepE_group", "stepE_rem"])
    fig = draw_state(idx, ch, sticks, left, right, lr, rr, hp, hr, taiji, show_l, show_r)
    show_fig(fig)

    # 在“得爻”阶段显示蓍草堆数
    if phase == "stepI":
        groups = sticks // 4
        yao_num = groups
        yao_desc = YAO_NAMES.get(yao_num, "未知")
        st.info(f"**当前剩余蓍草：{sticks} 根**  \n"
                f"**4根一组，可得：{groups} 堆**  \n"
                f"**此爻为：{yao_desc}**")

    if st.button(btn_label):
        advance_phase()
        st.rerun()

    # 推演过程中实时显示已得之爻（自下而上）
    if len(st.session_state.yao_results) > 0:
        yao_results = st.session_state.yao_results
        lines = []
        for i in range(len(yao_results)-1, -1, -1):
            lines.append(f"{i} {YAO_NAMES[yao_results[i]]}")
        st.markdown("**已得之爻（自下而上）：**")
        st.markdown("<br>".join(lines), unsafe_allow_html=True)

# 阶段5：结果展示与AI解卦
elif phase == "result":
    yao_list = st.session_state.yao_results
    if len(yao_list) < 6:
        st.warning("尚未完成六爻，请返回")
        st.stop()

    # ===== 详细六爻显示（自下而上） =====
    st.markdown("### 📜 推演所得六爻（自下而上）")
    yao_details = []
    for i, y in enumerate(yao_list):
        pos_name = ["初爻","二爻","三爻","四爻","五爻","上爻"][i]
        yin_yang = "阳" if y in (7,9) else "阴"
        change = "变" if y in (6,9) else "不变"
        yao_details.append(f"**{pos_name}**：{YAO_NAMES[y]}（{yin_yang}，{change}）")
    # 从上到下显示（上爻在前）
    for line in reversed(yao_details):
        st.markdown(line)
    st.markdown("---")

    # ===== 匹配卦象 =====
    disp, orig, changed, pos = interpret(yao_list)

    st.markdown("## 🔮 占卜结果")
    st.markdown(f"**所问：** {st.session_state.question}")

    st.subheader("本卦")
    st.code(disp, language="")
    st.markdown(f"**{orig[0]}**：{orig[1]}")

    if pos:
        st.markdown("### 之卦（变卦）")
        changed_lines = [draw_yao(9 if y==6 else (6 if y==9 else y)) for y in reversed(yao_list)]
        st.code("\n".join(changed_lines), language="")
        st.markdown(f"**{changed[0]}**：{changed[1]}")
        st.write(f"变爻位置（自下而上）：第 {', '.join(map(str,pos))} 爻")
        if len(pos)==1:
            st.info("一爻变，以本卦变爻爻辞为主。")
        else:
            st.info("多爻变，以本卦卦辞为主，兼看之卦卦辞。")
    else:
        st.info("静卦（无变爻），以本卦卦辞为主。")

    if use_ai and deepseek_key:
        prompt = f"用户问题：{st.session_state.question}\n本卦：{orig[0]}（{orig[1]}）"
        if pos:
            prompt += f"\n之卦：{changed[0]}（{changed[1]}），变爻：{pos}"
        prompt += "\n请作为易经专家，用白话给出通俗解读与建议。"
        with st.spinner("DeepSeek 正在解卦..."):
            ai_reply = call_deepseek(prompt, deepseek_key)
        st.subheader("🤖 AI 解读")
        st.write(ai_reply)

    if st.button("🔄 重新占卜"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
