"""
Visual Flow Editor — Interactive Streamlit page for designing agent flows.
Uses an embedded HTML5 Canvas for drag-and-drop agent boxes with arrows,
plus a sidebar properties panel and Vision Agent integration.
"""

import streamlit as st
import sys
import os
import json
import uuid

# Resolve imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import init_db, get_projects_by_user, create_project, get_project
from core.flow_builder import FlowBuilder, AGENT_COLORS, AGENT_MODELS, DEFAULT_TOOLS
from agents.vision_agent import VisionAgent

init_db()

st.set_page_config(page_title="Flow Editor — Visual Agent Builder", page_icon="🎨", layout="wide")

# ────────── Auth guard ──────────
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("⚠️ يرجى تسجيل الدخول أولاً من صفحة Login.")
    st.stop()

# ────────── Session defaults ──────────
DEFAULTS = {
    "current_project_id": None,
    "selected_agent_id": None,
    "canvas_action": None,
    "vision_result": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════
#  SIDEBAR — Project selector + Agent properties + Vision
# ════════════════════════════════════════════════════════════
def render_sidebar(fb: FlowBuilder | None):
    with st.sidebar:
        st.markdown("## 📂 المشاريع")

        projects = get_projects_by_user(st.session_state.user_id)
        project_names = {p["id"]: p["name"] for p in projects}

        # New project
        with st.expander("➕ مشروع جديد", expanded=not projects):
            new_name = st.text_input("اسم المشروع", key="new_proj_name")
            new_desc = st.text_input("وصف (اختياري)", key="new_proj_desc")
            if st.button("إنشاء", key="create_proj_btn", use_container_width=True):
                if new_name.strip():
                    pid = str(uuid.uuid4())
                    create_project(pid, st.session_state.user_id, new_name.strip(), new_desc.strip())
                    st.session_state.current_project_id = pid
                    st.rerun()
                else:
                    st.error("أدخل اسم المشروع.")

        if projects:
            options = list(project_names.keys())
            labels = list(project_names.values())
            current_idx = 0
            if st.session_state.current_project_id in options:
                current_idx = options.index(st.session_state.current_project_id)
            sel = st.selectbox("اختر مشروع", options, index=current_idx,
                               format_func=lambda x: project_names[x], key="proj_select")
            if sel != st.session_state.current_project_id:
                st.session_state.current_project_id = sel
                st.session_state.selected_agent_id = None
                st.rerun()

        st.divider()

        # ─── Properties panel ───
        if fb and st.session_state.selected_agent_id:
            agents = {a["id"]: a for a in fb.get_agents()}
            agent = agents.get(st.session_state.selected_agent_id)
            if agent:
                st.markdown("## ⚙️ خصائص العميل")
                meta = agent.get("meta", {})

                new_name = st.text_input("الاسم", value=agent["name"], key="prop_name")
                new_instructions = st.text_area("التعليمات", value=meta.get("instructions", ""),
                                                 height=120, key="prop_instr")
                new_model = st.selectbox("نموذج AI", AGENT_MODELS,
                                          index=AGENT_MODELS.index(meta.get("model", "gemini-2.0-flash"))
                                          if meta.get("model", "gemini-2.0-flash") in AGENT_MODELS else 0,
                                          key="prop_model")
                current_tools = meta.get("tools", [])
                new_tools = st.multiselect("الأدوات", DEFAULT_TOOLS, default=current_tools, key="prop_tools")
                new_color = st.color_picker("اللون", value=meta.get("color", "#6C5CE7"), key="prop_color")
                new_desc = st.text_input("وصف قصير", value=meta.get("description", ""), key="prop_desc")

                col_save, col_del = st.columns(2)
                with col_save:
                    if st.button("💾 حفظ التعديلات", use_container_width=True, key="save_props"):
                        fb.update_agent(
                            agent["id"],
                            name=new_name, instructions=new_instructions,
                            model=new_model, tools=new_tools,
                            color=new_color, description=new_desc,
                        )
                        st.success("✅ تم الحفظ!")
                        st.rerun()
                with col_del:
                    if st.button("🗑️ حذف", use_container_width=True, key="del_agent",
                                 type="primary"):
                        fb.delete_agent(agent["id"])
                        st.session_state.selected_agent_id = None
                        st.rerun()

        st.divider()

        # ─── Vision Agent ───
        st.markdown("## 👁️ Vision Agent")
        api_key = st.text_input("🔑 Gemini API Key", type="password",
                                 value="", key="gemini_key",
                                 help="أدخل مفتاح Gemini API الخاص بك من Google AI Studio")
        vision_model = st.selectbox("نموذج الرؤية", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"], key="vision_model_select")
        uploaded = st.file_uploader("📷 ارفع صورة", type=["png", "jpg", "jpeg", "webp"], key="vision_upload")
        mode = st.radio("نوع التحليل", list(VisionAgent.SUPPORTED_MODES.values()),
                        key="vision_mode", horizontal=True)
        mode_key = list(VisionAgent.SUPPORTED_MODES.keys())[
            list(VisionAgent.SUPPORTED_MODES.values()).index(mode)
        ]

        if st.button("🔍 حلّل الصورة", use_container_width=True, key="analyze_btn"):
            if not api_key:
                st.error("أدخل مفتاح Gemini API.")
            elif not uploaded:
                st.error("ارفع صورة أولاً.")
            else:
                with st.spinner("جارٍ التحليل... (قد يستغرق وقتاً إذا كان هناك Rate Limit)"):
                    try:
                        va = VisionAgent(api_key=api_key, model_name=vision_model)
                        result = va.analyze(uploaded.read(), mode=mode_key, mime_type=uploaded.type)
                        st.session_state.vision_result = result
                    except Exception as e:
                        st.error(f"خطأ: {e}")

        if st.session_state.vision_result:
            st.markdown("### 📝 النتيجة")
            st.markdown(st.session_state.vision_result)


# ════════════════════════════════════════════════════════════
#  CANVAS — Generates the HTML/JS for the interactive editor
# ════════════════════════════════════════════════════════════
def build_canvas_html(agents: list[dict], edges: list[dict]) -> str:
    """Build a self-contained HTML/CSS/JS canvas for the flow editor."""

    # Encode data for JS
    js_agents = json.dumps([{
        "id": a["id"],
        "name": a["name"],
        "x": a["x_position"],
        "y": a["y_position"],
        "color": a.get("meta", {}).get("color", "#6C5CE7"),
        "model": a.get("meta", {}).get("model", ""),
        "desc": a.get("meta", {}).get("description", ""),
    } for a in agents], ensure_ascii=False)

    js_edges = json.dumps([{
        "source": e["source_node_id"],
        "target": e["target_node_id"],
    } for e in edges], ensure_ascii=False)

    return f"""
<!DOCTYPE html>
<html dir="rtl">
<head>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0e1117; overflow:hidden; font-family:'Segoe UI',Tahoma,sans-serif; }}
  canvas {{ display:block; cursor:default; }}
  #tooltip {{
    position:absolute; display:none; background:rgba(30,30,46,0.95);
    color:#cdd6f4; padding:8px 14px; border-radius:10px; font-size:13px;
    pointer-events:none; border:1px solid rgba(137,180,250,0.3);
    backdrop-filter:blur(8px); max-width:220px; z-index:100;
  }}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="tooltip"></div>
<script>
const agents = {js_agents};
const edges  = {js_edges};

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

const W = () => window.innerWidth;
const H = () => window.innerHeight;
canvas.width = W(); canvas.height = H();
window.addEventListener('resize', () => {{ canvas.width=W(); canvas.height=H(); draw(); }});

const NODE_W = 180, NODE_H = 72, RADIUS = 14;
let dragging = null, dragOff = {{x:0,y:0}};
let hoveredNode = null;
let selectedId = null;

// ── Drawing ──
function hexToRgba(hex, a) {{
  if (!hex || hex.length < 7) hex = '#6C5CE7';
  const r = parseInt(hex.slice(1,3),16) || 108;
  const g = parseInt(hex.slice(3,5),16) || 92;
  const b = parseInt(hex.slice(5,7),16) || 231;
  return `rgba(${{r}},${{g}},${{b}},${{a}})`;
}}

function drawArrow(x1,y1,x2,y2,color) {{
  const dx=x2-x1, dy=y2-y1, angle=Math.atan2(dy,dx);
  const headLen=14;

  // Curved line
  const mx = (x1+x2)/2, my = (y1+y2)/2 - 30;
  ctx.beginPath();
  ctx.moveTo(x1,y1);
  ctx.quadraticCurveTo(mx,my,x2,y2);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.setLineDash([]);
  ctx.stroke();

  // Arrowhead
  const t = 0.98;
  const px = (1-t)*(1-t)*x1 + 2*(1-t)*t*mx + t*t*x2;
  const py = (1-t)*(1-t)*y1 + 2*(1-t)*t*my + t*t*y2;
  const angle2 = Math.atan2(y2-py, x2-px);
  ctx.beginPath();
  ctx.moveTo(x2,y2);
  ctx.lineTo(x2-headLen*Math.cos(angle2-0.4), y2-headLen*Math.sin(angle2-0.4));
  ctx.lineTo(x2-headLen*Math.cos(angle2+0.4), y2-headLen*Math.sin(angle2+0.4));
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
}}

function drawNode(a, isSelected) {{
  const x=a.x, y=a.y, w=NODE_W, h=NODE_H;

  // Shadow
  ctx.shadowColor = hexToRgba(a.color, 0.45);
  ctx.shadowBlur = isSelected ? 28 : 14;
  ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 4;

  // Box with gradient
  const grad = ctx.createLinearGradient(x, y, x+w, y+h);
  grad.addColorStop(0, hexToRgba(a.color, 0.92));
  grad.addColorStop(1, hexToRgba(a.color, 0.7));

  ctx.beginPath();
  ctx.roundRect(x, y, w, h, RADIUS);
  ctx.fillStyle = grad;
  ctx.fill();

  // Border
  ctx.strokeStyle = isSelected ? '#f1fa8c' : 'rgba(255,255,255,0.15)';
  ctx.lineWidth = isSelected ? 3 : 1.5;
  ctx.stroke();
  ctx.shadowColor = 'transparent';

  // Icon
  ctx.font = '22px serif';
  ctx.fillText('🤖', x+12, y+30);

  // Name
  ctx.font = 'bold 14px "Segoe UI", sans-serif';
  ctx.fillStyle = '#fff';
  ctx.textAlign = 'left';
  const displayName = a.name.length > 16 ? a.name.slice(0,15)+'…' : a.name;
  ctx.fillText(displayName, x+42, y+28);

  // Model badge
  ctx.font = '11px "Segoe UI", sans-serif';
  ctx.fillStyle = 'rgba(255,255,255,0.6)';
  const modelShort = (a.model||'').replace('gemini-','').slice(0,18);
  ctx.fillText(modelShort, x+42, y+48);

  // Connector dots
  // Output (right)
  ctx.beginPath();
  ctx.arc(x+w, y+h/2, 6, 0, Math.PI*2);
  ctx.fillStyle = '#50fa7b';
  ctx.fill();
  ctx.strokeStyle = '#282a36';
  ctx.lineWidth = 2;
  ctx.stroke();
  // Input (left)
  ctx.beginPath();
  ctx.arc(x, y+h/2, 6, 0, Math.PI*2);
  ctx.fillStyle = '#ff79c6';
  ctx.fill();
  ctx.stroke();
}}

function draw() {{
  ctx.clearRect(0,0,canvas.width,canvas.height);

  // Grid dots
  ctx.fillStyle = 'rgba(255,255,255,0.04)';
  for(let gx=0; gx<canvas.width; gx+=30)
    for(let gy=0; gy<canvas.height; gy+=30) {{
      ctx.beginPath(); ctx.arc(gx,gy,1,0,Math.PI*2); ctx.fill();
    }}

  // Edges
  edges.forEach(e => {{
    const src = agents.find(a=>a.id===e.source);
    const tgt = agents.find(a=>a.id===e.target);
    if(src && tgt) {{
      drawArrow(
        src.x+NODE_W, src.y+NODE_H/2,
        tgt.x, tgt.y+NODE_H/2,
        hexToRgba(src.color, 0.7)
      );
    }}
  }});

  // Nodes
  agents.forEach(a => drawNode(a, a.id===selectedId));
}}

// ── Interaction ──
function getNodeAt(mx, my) {{
  for(let i=agents.length-1; i>=0; i--) {{
    const a=agents[i];
    if(mx>=a.x && mx<=a.x+NODE_W && my>=a.y && my<=a.y+NODE_H) return a;
  }}
  return null;
}}

canvas.addEventListener('mousedown', e => {{
  const a = getNodeAt(e.offsetX, e.offsetY);
  if(a) {{
    dragging = a;
    dragOff = {{x: e.offsetX - a.x, y: e.offsetY - a.y}};
    selectedId = a.id;
    // Send selection to Streamlit
    window.parent.postMessage({{type:'agentSelected', id:a.id}}, '*');
    draw();
  }} else {{
    selectedId = null;
    window.parent.postMessage({{type:'agentSelected', id:null}}, '*');
    draw();
  }}
}});

canvas.addEventListener('mousemove', e => {{
  const mx=e.offsetX, my=e.offsetY;
  if(dragging) {{
    dragging.x = mx - dragOff.x;
    dragging.y = my - dragOff.y;
    draw();
  }}
  // Tooltip
  const node = getNodeAt(mx, my);
  if(node) {{
    tooltip.style.display = 'block';
    tooltip.style.left = (mx+16)+'px';
    tooltip.style.top  = (my+16)+'px';
    tooltip.innerHTML = '<b>'+node.name+'</b><br><span style="opacity:.7">'+(node.desc||'بدون وصف')+'</span>';
    canvas.style.cursor = 'grab';
  }} else {{
    tooltip.style.display = 'none';
    canvas.style.cursor = 'default';
  }}
}});

canvas.addEventListener('mouseup', e => {{
  if(dragging) {{
    // Notify Streamlit of new position
    window.parent.postMessage({{
      type:'agentMoved', id:dragging.id,
      x:Math.round(dragging.x), y:Math.round(dragging.y)
    }}, '*');
    dragging = null;
  }}
}});

canvas.addEventListener('dblclick', e => {{
  const a = getNodeAt(e.offsetX, e.offsetY);
  if(a) {{
    selectedId = a.id;
    window.parent.postMessage({{type:'agentSelected', id:a.id}}, '*');
    draw();
  }}
}});

draw();
</script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════════
#  MAIN PAGE
# ════════════════════════════════════════════════════════════
def main():
    # ── Sidebar ──
    fb = None
    if st.session_state.current_project_id:
        fb = FlowBuilder(st.session_state.current_project_id)
    render_sidebar(fb)

    # ── Header ──
    st.markdown("""
    <style>
    .flow-header { 
        background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
        padding: 18px 28px; border-radius: 16px; margin-bottom: 18px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .flow-header h1 { color: #fff; font-size: 26px; margin: 0; }
    .flow-header p  { color: rgba(255,255,255,0.8); font-size: 14px; margin: 4px 0 0; }
    .stButton > button { border-radius: 10px !important; }
    </style>
    <div class="flow-header">
        <div>
            <h1>🎨 محرر التدفق البصري</h1>
            <p>صمّم فريق AI الخاص بك — اسحب الصناديق وربطها بأسهم</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.current_project_id:
        st.info("👈 اختر مشروع أو أنشئ واحد جديد من القائمة الجانبية.")
        return

    project = get_project(st.session_state.current_project_id)
    if not project:
        st.error("المشروع غير موجود.")
        return

    st.markdown(f"**📁 المشروع:** {project['name']}")

    # ── Toolbar ──
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        add_clicked = st.button("➕ أضف Agent", use_container_width=True, key="add_agent_btn")
    with col2:
        save_clicked = st.button("💾 احفظ المواقع", use_container_width=True, key="save_pos_btn")
    with col3:
        run_clicked = st.button("▶️ شغّل", use_container_width=True, key="run_flow_btn")
    with col4:
        layout_clicked = st.button("📐 ترتيب تلقائي", use_container_width=True, key="auto_layout_btn")
    with col5:
        export_clicked = st.button("📤 تصدير JSON", use_container_width=True, key="export_btn")
    with col6:
        clear_clicked = st.button("🗑️ امسح الكل", use_container_width=True, key="clear_all_btn", type="primary")

    # ── Handle toolbar actions ──
    if add_clicked:
        st.session_state.canvas_action = "add"
    if clear_clicked:
        fb.clear_flow()
        st.session_state.selected_agent_id = None
        st.rerun()
    if layout_clicked:
        fb.auto_layout()
        st.rerun()
    if export_clicked:
        json_data = fb.export_flow_json()
        st.download_button("⬇️ تحميل JSON", data=json_data,
                           file_name=f"{project['name']}_flow.json", mime="application/json")

    if run_clicked:
        order = fb.get_execution_order()
        agents_map = {a["id"]: a["name"] for a in fb.get_agents()}
        if order:
            names = [agents_map.get(nid, nid[:8]) for nid in order]
            st.success(f"🚀 ترتيب التنفيذ: {' → '.join(names)}")
        else:
            st.warning("لا يوجد Agents لتشغيلها.")

    # ── Add Agent Dialog ──
    if st.session_state.canvas_action == "add":
        with st.expander("➕ إضافة Agent جديد", expanded=True):
            with st.form("add_agent_form"):
                a_name = st.text_input("اسم العميل", placeholder="مثال: باحث")
                a_instr = st.text_area("التعليمات", placeholder="أنت باحث متخصص في...", height=80)
                a_model = st.selectbox("نموذج AI", AGENT_MODELS)
                a_tools = st.multiselect("الأدوات", DEFAULT_TOOLS)
                a_color = st.color_picker("اللون", value=AGENT_COLORS[len(fb.get_agents()) % len(AGENT_COLORS)])
                a_desc  = st.text_input("وصف قصير", placeholder="وصف مختصر للدور")
                submitted = st.form_submit_button("✅ إنشاء", use_container_width=True)
                if submitted and a_name.strip():
                    # Calculate position based on existing agents
                    existing = fb.get_agents()
                    new_x = 80 + (len(existing) % 4) * 220
                    new_y = 80 + (len(existing) // 4) * 140
                    fb.add_agent(
                        name=a_name.strip(), x=new_x, y=new_y,
                        instructions=a_instr, model=a_model,
                        tools=a_tools, color=a_color, description=a_desc,
                    )
                    st.session_state.canvas_action = None
                    st.rerun()

    # ── Edge management ──
    agents = fb.get_agents()
    if len(agents) >= 2:
        with st.expander("🔗 ربط Agents بأسهم"):
            agent_names = {a["id"]: a["name"] for a in agents}
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                src = st.selectbox("من", list(agent_names.keys()),
                                    format_func=lambda x: agent_names[x], key="edge_src")
            with c2:
                tgt = st.selectbox("إلى", list(agent_names.keys()),
                                    format_func=lambda x: agent_names[x], key="edge_tgt")
            with c3:
                if st.button("➕ ربط", key="add_edge_btn", use_container_width=True):
                    if src != tgt:
                        fb.add_edge(src, tgt)
                        st.rerun()
                    else:
                        st.error("لا يمكن ربط Agent بنفسه.")

            # Show existing edges
            edges_list = fb.get_edges_list()
            if edges_list:
                st.markdown("**الاتصالات الحالية:**")
                for e in edges_list:
                    src_name = agent_names.get(e["source_node_id"], "?")
                    tgt_name = agent_names.get(e["target_node_id"], "?")
                    ec1, ec2 = st.columns([4, 1])
                    with ec1:
                        st.write(f"  {src_name} → {tgt_name}")
                    with ec2:
                        if st.button("❌", key=f"del_edge_{e['id']}"):
                            fb.delete_edge(e["id"])
                            st.rerun()

    # ── Validation warnings ──
    warnings = fb.validate_flow()
    if warnings:
        with st.expander("⚠️ تحذيرات التدفق", expanded=False):
            for w in warnings:
                st.warning(w)

    # ── Canvas ──
    st.markdown("---")
    agents = fb.get_agents()
    edges_data = fb.get_edges_list()

    if agents:
        html = build_canvas_html(agents, edges_data)
        st.components.v1.html(html, height=520, scrolling=False)

        # Agent selector (fallback for non-JS environments)
        agent_names = {a["id"]: a["name"] for a in agents}
        sel = st.selectbox(
            "🖱️ اختر Agent لتعديل خصائصه",
            [None] + list(agent_names.keys()),
            format_func=lambda x: "— اضغط على صندوق —" if x is None else agent_names[x],
            key="agent_selector_fallback",
        )
        if sel != st.session_state.selected_agent_id:
            st.session_state.selected_agent_id = sel
            st.rerun()
    else:
        st.markdown("""
        <div style="
            text-align:center; padding:80px 20px;
            background:rgba(108,92,231,0.06); border-radius:16px;
            border:2px dashed rgba(108,92,231,0.25); margin:10px 0;
        ">
            <div style="font-size:56px; margin-bottom:12px;">🤖</div>
            <h3 style="color:#a29bfe; margin:0 0 8px;">لا يوجد Agents بعد</h3>
            <p style="color:#888;">اضغط <b>➕ أضف Agent</b> لبدء تصميم الفريق</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Quick agent info cards ──
    if agents:
        st.markdown("### 🤖 الفريق الحالي")
        cols = st.columns(min(len(agents), 4))
        for i, a in enumerate(agents):
            meta = a.get("meta", {})
            with cols[i % len(cols)]:
                color = meta.get("color", "#6C5CE7")
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}22, {color}11);
                    border: 1px solid {color}44; border-radius: 12px;
                    padding: 14px; margin-bottom: 8px;
                ">
                    <div style="font-size:13px; color:{color}; font-weight:700;">🤖 {a['name']}</div>
                    <div style="font-size:11px; color:#888; margin-top:4px;">
                        {meta.get('model','').replace('gemini-','')}
                    </div>
                    <div style="font-size:11px; color:#aaa; margin-top:2px;">
                        {meta.get('description','') or '—'}
                    </div>
                </div>
                """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
