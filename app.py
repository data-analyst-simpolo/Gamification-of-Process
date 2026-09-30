import base64
import io
import itertools
import uuid
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Four-Year Profit Optimization Challenge",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# AUTHORITATIVE MODEL INPUTS
# =============================================================================
BASELINE = {
    "productivity": 80.0,
    "quality": 0.75,
    "manufacturing_cost": 30.0,
    "selling_price": 50.0,
    "budget": 100.0,
}

# R1 is always the selection year. If an activity is selected in Year 2,
# Year 2=R1, Year 3=R2, and Year 4=R3.
ACTIVITIES = {
    "Parallel Line Installation": {
        "icon": "🏭",
        "fixed_cost": 50.0,
        "productivity": [90.0, 90.0, 90.0, 90.0],
        "quality": [0.75, 0.75, 0.75, 0.75],
        "manufacturing_cost": [27.0, 27.0, 27.0, 27.0],
    },
    "Changeover Time Optimization (SMED)": {
        "icon": "⏱️",
        "fixed_cost": 25.0,
        "productivity": [90.0, 90.0, 90.0, 90.0],
        "quality": [0.75, 0.75, 0.75, 0.75],
        "manufacturing_cost": [27.0, 27.0, 27.0, 27.0],
    },
    "Increase Speed of Bottleneck": {
        "icon": "⚙️",
        "fixed_cost": 10.0,
        "productivity": [90.0, 90.0, 90.0, 90.0],
        "quality": [0.74, 0.74, 0.74, 0.74],
        "manufacturing_cost": [27.0, 27.0, 27.0, 27.0],
    },
    "Preventive Maintenance (CLTI)": {
        "icon": "🔧",
        "fixed_cost": 20.0,
        "productivity": [81.0, 82.0, 83.0, 84.0],
        "quality": [0.75, 0.75, 0.75, 0.75],
        "manufacturing_cost": [30.0, 29.0, 28.0, 27.0],
    },
    "Statistical Process Control": {
        "icon": "📊",
        "fixed_cost": 20.0,
        "productivity": [80.0, 80.0, 80.0, 80.0],
        "quality": [0.77, 0.79, 0.81, 0.83],
        "manufacturing_cost": [30.0, 30.0, 30.0, 30.0],
    },
    "Operator Training & Performance Management": {
        "icon": "👷",
        "fixed_cost": 25.0,
        "productivity": [80.0, 81.0, 82.0, 83.0],
        "quality": [0.75, 0.76, 0.77, 0.78],
        "manufacturing_cost": [30.0, 29.0, 28.0, 27.0],
    },
}

LEADERBOARD_PATH = "data/leaderboard.csv"
LOG_PATH = "data/simulation_log.csv"
LEADERBOARD_COLUMNS = [
    "Session ID", "Team Name", "Team Members", "Year", "Selected Activity",
    "Productivity", "Quality %", "Manufacturing Cost", "Landed Cost",
    "Selling Price", "Annual Profit", "Cumulative Profit", "Budget Remaining",
    "Updated At",
]
LOG_COLUMNS = [
    "Session ID", "Team Name", "Team Members", "Year", "Selected Activity",
    "Active Activity Stages", "Productivity", "Quality %", "Manufacturing Cost",
    "Fixed Cost", "Landed Cost", "Selling Price", "Annual Profit",
    "Cumulative Profit", "Budget Remaining", "Diagnosis", "Created At",
]

# =============================================================================
# STYLE
# =============================================================================
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 8% 4%,#dcfce7 0,transparent 22%),linear-gradient(135deg,#f8fffa,#eef7f0)}
.block-container{max-width:1360px;padding-top:1.1rem;padding-bottom:3rem}#MainMenu,footer{visibility:hidden}
.hero{padding:1.8rem 2rem;border-radius:25px;background:linear-gradient(125deg,#103d27,#166534 52%,#16a34a);color:white;box-shadow:0 18px 48px rgba(20,83,45,.2);margin-bottom:1rem}.hero h1{margin:0}.hero p{margin:.4rem 0 0;opacity:.92}
.baseline{padding:1rem 1.15rem;border-radius:16px;background:#ecfeff;border:1px solid #67e8f9;margin:.8rem 0}
.insight{padding:.9rem 1rem;border-radius:14px;background:#eff6ff;border:1px solid #93c5fd;margin:.7rem 0}
.actionbar{display:flex;gap:8px;align-items:center;justify-content:center;margin:1.0rem 0 .8rem;padding:.8rem;border-radius:15px;background:white;border:1px solid #d9e8de}
.step{min-width:112px;text-align:center;padding:.65rem .75rem;border-radius:12px;background:#e2e8f0;color:#475569;font-weight:750}.step.done{background:#bbf7d0;color:#14532d}.step.current{background:#15803d;color:white;box-shadow:0 6px 16px rgba(21,128,61,.25)}
.activity{background:white;border:1px solid #d9e8de;border-radius:18px;padding:1rem;box-shadow:0 8px 22px rgba(20,83,45,.07);height:100%}.activity.selected{border:2px solid #15803d}.activity.unavailable{opacity:.48;filter:grayscale(.75)}.activity h3{font-size:1.02rem;margin:.15rem 0 .55rem}.ico{font-size:2rem}
.effect-table{width:100%;border-collapse:collapse;font-size:.79rem}.effect-table th{background:#166534;color:white;padding:6px;border:1px solid #d2ded6;text-align:center}.effect-table td{padding:6px;border:1px solid #d2ded6;text-align:center}.effect-table td:first-child{text-align:left;font-weight:700;background:#f8fafc}.profit-row td{background:#ecfdf5;font-weight:700}.total-profit{margin-top:.55rem;padding:.5rem;border-radius:9px;background:#f0fdf4;color:#166534;font-weight:800;text-align:center}
.process-wrap{background:white;border:1px solid #b9d8c1;border-radius:22px;padding:1rem;overflow-x:auto}.process-line{min-width:1000px;display:flex;align-items:center;gap:10px;position:relative;padding:20px 10px 50px}.unit{width:145px;min-height:80px;border:2px solid #15803d;border-radius:13px;background:#eefbf1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-weight:750}.unit span{font-size:1.8rem}.arrow{width:48px;height:12px;background:#15803d;position:relative}.arrow:after{content:"";position:absolute;right:-13px;top:-7px;border-left:14px solid #15803d;border-top:13px solid transparent;border-bottom:13px solid transparent}.belt{position:absolute;left:15px;right:15px;bottom:18px;height:10px;border-radius:6px;background:repeating-linear-gradient(90deg,#14532d 0 24px,#86efac 24px 38px);animation:belt .75s linear infinite}.tile{position:absolute;bottom:29px;width:34px;height:20px;background:#f59e0b;border:2px solid #9a5a06;border-radius:3px;animation:move 8s linear infinite}.tile.t2{animation-delay:-2.7s}.tile.t3{animation-delay:-5.4s}.flow-label{position:absolute;bottom:0;left:15px;color:#166534;font-size:.78rem;font-weight:700}@keyframes belt{to{background-position:38px 0}}@keyframes move{0%{left:2%}100%{left:95%}}
.stButton>button,.stFormSubmitButton>button{border-radius:12px;min-height:45px;font-weight:700}.stFormSubmitButton>button{background:#15803d!important;color:white!important;border:0!important}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# OPTIONAL GITHUB STORAGE
# =============================================================================
def github_configured():
    return all(str(st.secrets.get(k, "")).strip() for k in ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"])

def github_headers():
    return {"Authorization":f"Bearer {st.secrets['GITHUB_TOKEN']}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}

def github_url(path):
    return f"https://api.github.com/repos/{st.secrets['GITHUB_OWNER']}/{st.secrets['GITHUB_REPO']}/contents/{path}"

def read_remote_csv(path, columns):
    response=requests.get(github_url(path),headers=github_headers(),params={"ref":st.secrets.get("GITHUB_BRANCH","main")},timeout=30)
    if response.status_code==404:return pd.DataFrame(columns=columns),None
    response.raise_for_status();payload=response.json()
    try:frame=pd.read_csv(io.BytesIO(base64.b64decode(payload["content"])))
    except pd.errors.EmptyDataError:frame=pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame:frame[column]=""
    return frame[columns],payload["sha"]

def write_remote_csv(path,frame,columns,sha,message):
    body={"message":message,"content":base64.b64encode(frame[columns].to_csv(index=False).encode()).decode(),"branch":st.secrets.get("GITHUB_BRANCH","main")}
    if sha:body["sha"]=sha
    response=requests.put(github_url(path),headers=github_headers(),json=body,timeout=30);response.raise_for_status()

def append_remote_csv(path,row,columns,message):
    frame,sha=read_remote_csv(path,columns);frame=pd.concat([frame,pd.DataFrame([row])],ignore_index=True);write_remote_csv(path,frame,columns,sha,message)

def update_leaderboard(row):
    if github_configured():
        frame,sha=read_remote_csv(LEADERBOARD_PATH,LEADERBOARD_COLUMNS);frame=frame[~frame["Session ID"].astype(str).eq(str(row["Session ID"]))];frame=pd.concat([frame,pd.DataFrame([row])],ignore_index=True);write_remote_csv(LEADERBOARD_PATH,frame,LEADERBOARD_COLUMNS,sha,"Update profit optimization leaderboard")
    local=st.session_state.get("local_lb",pd.DataFrame(columns=LEADERBOARD_COLUMNS));local=local[~local["Session ID"].astype(str).eq(str(row["Session ID"]))];st.session_state.local_lb=pd.concat([local,pd.DataFrame([row])],ignore_index=True)

def get_leaderboard():
    if github_configured():
        try:return read_remote_csv(LEADERBOARD_PATH,LEADERBOARD_COLUMNS)[0]
        except Exception as error:st.caption(f"Shared leaderboard unavailable: {error}")
    return st.session_state.get("local_lb",pd.DataFrame(columns=LEADERBOARD_COLUMNS))

# =============================================================================
# MODEL FUNCTIONS
# ==============================================================================
def standalone_profit(activity_name, stage_index):
    activity=ACTIVITIES[activity_name]
    p=activity["productivity"][stage_index];q=activity["quality"][stage_index];c=activity["manufacturing_cost"][stage_index]
    fixed=activity["fixed_cost"] if stage_index==0 else 0
    return p*q*BASELINE["selling_price"]-p*c-fixed

def initial_state():
    return {"year":0,"budget":BASELINE["budget"],"selections":{},"productivity":BASELINE["productivity"],"quality":BASELINE["quality"],"manufacturing_cost":BASELINE["manufacturing_cost"],"cumulative_profit":0.0,"history":[]}

def compute_portfolio(selections,current_year,new_activity):
    active=dict(selections);active[current_year]=new_activity
    p=BASELINE["productivity"];q=BASELINE["quality"];c=BASELINE["manufacturing_cost"]
    stages=[]
    for selection_year,activity_name in sorted(active.items()):
        if selection_year<=current_year:
            stage=current_year-selection_year
            activity=ACTIVITIES[activity_name]
            p+=activity["productivity"][stage]-BASELINE["productivity"]
            q+=activity["quality"][stage]-BASELINE["quality"]
            c+=activity["manufacturing_cost"][stage]-BASELINE["manufacturing_cost"]
            stages.append(f"{activity_name}: R{stage+1}")
    q=max(0,min(1,q));c=max(0,c)
    fixed=ACTIVITIES[new_activity]["fixed_cost"]
    good=p*q
    landed=(p*c+fixed)/good if good else 0
    profit=good*BASELINE["selling_price"]-p*c-fixed
    return {"productivity":p,"quality":q,"manufacturing_cost":c,"fixed_cost":fixed,"landed_cost":landed,"annual_profit":profit,"stages":" | ".join(stages)}

def diagnose(metrics,previous=None):
    parts=[]
    parts.append(f"Productivity is {'above' if metrics['productivity']>BASELINE['productivity'] else 'at' if metrics['productivity']==BASELINE['productivity'] else 'below'} the baseline.")
    parts.append(f"Quality is {'above' if metrics['quality']>BASELINE['quality'] else 'at' if metrics['quality']==BASELINE['quality'] else 'below'} the 75% baseline.")
    parts.append(f"Manufacturing cost is {'lower than' if metrics['manufacturing_cost']<BASELINE['manufacturing_cost'] else 'equal to' if metrics['manufacturing_cost']==BASELINE['manufacturing_cost'] else 'higher than'} the baseline cost of 30/tile.")
    if previous:
        delta=metrics["annual_profit"]-previous["annual_profit"]
        parts.append(f"Annual profit {'increased' if delta>=0 else 'decreased'} by {abs(delta):.2f} versus the previous year.")
    return " ".join(parts)

def run_year():
    state=st.session_state.state.copy();state["selections"]=dict(state["selections"]);state["history"]=list(state["history"])
    year=state["year"]+1;selected=st.session_state.get("selected_activity")
    if not selected:st.error("Select one activity for this year.");return
    if selected in state["selections"].values():st.error("This activity was already selected in an earlier year.");return
    fixed=ACTIVITIES[selected]["fixed_cost"]
    if fixed>state["budget"]:st.error("The selected activity exceeds the remaining budget.");return
    metrics=compute_portfolio(state["selections"],year,selected);previous=state["history"][-1] if state["history"] else None;metrics.update({"year":year,"selected":selected,"diagnosis":diagnose(metrics,previous)})
    state["year"]=year;state["budget"]-=fixed;state["selections"][year]=selected;state["productivity"]=metrics["productivity"];state["quality"]=metrics["quality"];state["manufacturing_cost"]=metrics["manufacturing_cost"];state["cumulative_profit"]+=metrics["annual_profit"];state["history"].append(metrics);st.session_state.state=state
    row={"Session ID":st.session_state.session_id,"Team Name":st.session_state.team_name,"Team Members":st.session_state.team_members,"Year":year,"Selected Activity":selected,"Productivity":metrics["productivity"],"Quality %":metrics["quality"]*100,"Manufacturing Cost":metrics["manufacturing_cost"],"Landed Cost":metrics["landed_cost"],"Selling Price":BASELINE["selling_price"],"Annual Profit":metrics["annual_profit"],"Cumulative Profit":state["cumulative_profit"],"Budget Remaining":state["budget"],"Updated At":datetime.now().strftime("%Y-%m-%d %H:%M:%S")};update_leaderboard(row)
    if github_configured():
        log={"Session ID":st.session_state.session_id,"Team Name":st.session_state.team_name,"Team Members":st.session_state.team_members,"Year":year,"Selected Activity":selected,"Active Activity Stages":metrics["stages"],"Productivity":metrics["productivity"],"Quality %":metrics["quality"]*100,"Manufacturing Cost":metrics["manufacturing_cost"],"Fixed Cost":fixed,"Landed Cost":metrics["landed_cost"],"Selling Price":BASELINE["selling_price"],"Annual Profit":metrics["annual_profit"],"Cumulative Profit":state["cumulative_profit"],"Budget Remaining":state["budget"],"Diagnosis":metrics["diagnosis"],"Created At":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        try:append_remote_csv(LOG_PATH,log,LOG_COLUMNS,f"Add Year {year} result")
        except Exception as error:st.warning(f"Year completed; GitHub save failed: {error}")
    st.rerun()

# =============================================================================
# UI HELPERS
# =============================================================================
def hero():st.markdown("<div class='hero'><h1>🏆 Four-Year Profit Optimization Challenge</h1><p>Select one unique activity in each year. Previously selected activities continue to mature from R1 to R4.</p></div>",unsafe_allow_html=True)

def conveyor(productivity):
    duration=max(2.8,min(14,900/max(productivity,1)))
    st.markdown(f"""<div class='process-wrap'><div class='process-line'><div class='unit'><span>🧱</span>Inputs</div><div class='arrow'></div><div class='unit'><span>🏭</span>Production</div><div class='arrow'></div><div class='unit'><span>✅</span>Quality</div><div class='arrow'></div><div class='unit'><span>🚚</span>Landed Cost</div><div class='arrow'></div><div class='unit'><span>💰</span>Profit</div><div class='belt'></div><div class='tile' style='animation-duration:{duration}s'></div><div class='tile t2' style='animation-duration:{duration}s'></div><div class='tile t3' style='animation-duration:{duration}s'></div><div class='flow-label'>Conveyor speed linked to productivity: {productivity:.1f} tiles/day</div></div></div>""",unsafe_allow_html=True)

def action_bar(current_year):
    items=[]
    for year in range(1,5):
        css="done" if year<=current_year else "current" if year==current_year+1 else ""
        label="Completed" if year<=current_year else "Select Now" if year==current_year+1 else "Upcoming"
        items.append(f"<div class='step {css}'>Year {year}<br><small>{label}</small></div>")
    st.markdown("<div class='actionbar'>"+"".join(items)+"</div>",unsafe_allow_html=True)

def activity_table_html(name,activity,unavailable=False):
    profits=[standalone_profit(name,i) for i in range(4)];total=sum(profits)
    pct=lambda x:f"{x:.0%}"
    cls="activity unavailable" if unavailable else "activity"
    return f"""<div class='{cls}'><div class='ico'>{activity['icon']}</div><h3>{name}</h3><table class='effect-table'><tr><th>Impact</th><th>R1</th><th>R2</th><th>R3</th><th>R4</th></tr><tr><td>Productivity</td>{''.join(f'<td>{v:g}</td>' for v in activity['productivity'])}</tr><tr><td>Quality</td>{''.join(f'<td>{pct(v)}</td>' for v in activity['quality'])}</tr><tr><td>Cost</td>{''.join(f'<td>{v:g}</td>' for v in activity['manufacturing_cost'])}</tr><tr><td>Fixed Cost</td><td>{activity['fixed_cost']:g}</td><td>-</td><td>-</td><td>-</td></tr><tr class='profit-row'><td>Profit</td>{''.join(f'<td>{v:,.1f}</td>' for v in profits)}</tr></table><div class='total-profit'>Overall Profit if selected in Year 1: {total:,.1f}</div></div>"""

def trend(history):
    frame=pd.DataFrame(history);x=[f"Year {int(y)}" for y in frame["year"]];fig=go.Figure();fig.add_bar(x=x,y=frame["annual_profit"],name="Annual Profit",marker_color="#15803d");fig.add_scatter(x=x,y=frame["landed_cost"],name="Landed Cost",yaxis="y2",mode="lines+markers",line=dict(color="#f59e0b"));fig.update_layout(title="Annual Profit and Landed Cost",yaxis_title="Annual Profit",yaxis2=dict(title="Landed Cost",overlaying="y",side="right"));st.plotly_chart(fig,use_container_width=True)

def leaderboard_section():
    st.subheader("🏅 Live Leaderboard");lb=get_leaderboard()
    if lb.empty:st.info("Complete a year to populate the leaderboard.");return
    for col in ["Cumulative Profit","Budget Remaining"]:lb[col]=pd.to_numeric(lb[col],errors="coerce")
    lb=lb.sort_values(["Cumulative Profit","Budget Remaining"],ascending=[False,True]).reset_index(drop=True);lb.insert(0,"Rank",range(1,len(lb)+1));st.dataframe(lb[["Rank","Team Name","Team Members","Year","Selected Activity","Cumulative Profit","Budget Remaining"]],use_container_width=True,hide_index=True)

# =============================================================================
# PAGES
# =============================================================================
def registration_page():
    hero();conveyor(BASELINE["productivity"]);_,center,_=st.columns([1,1.5,1])
    with center:
        with st.form("registration"):
            st.subheader("Register Your Team");team=st.text_input("Team Name *");members=st.text_area("Team Members *",height=110);submitted=st.form_submit_button("Start Challenge →",use_container_width=True)
        if submitted:
            if not team.strip() or not members.strip():st.error("Enter both Team Name and Team Members.")
            else:st.session_state.update(registered=True,session_id=str(uuid.uuid4()),team_name=team.strip(),team_members=members.strip(),state=initial_state(),local_lb=pd.DataFrame(columns=LEADERBOARD_COLUMNS));st.rerun()

def dashboard_page():
    hero();state=st.session_state.state;conveyor(state["productivity"])
    with st.sidebar:
        st.success(f"Team: {st.session_state.team_name}");st.write("**Team Members**");st.write(st.session_state.team_members);st.metric("Year",f"{state['year']} / 4");st.metric("Budget Remaining",f"{state['budget']:.0f}");st.metric("Cumulative Profit",f"{state['cumulative_profit']:.1f}")
        if st.button("Restart Simulation",use_container_width=True):st.session_state.clear();st.rerun()
    if not state["history"]:
        st.markdown(f"<div class='baseline'><h3>Year 0 Baseline</h3><p><b>Productivity:</b> 80 tiles/day &nbsp; | &nbsp; <b>Quality:</b> 75% &nbsp; | &nbsp; <b>Manufacturing Cost:</b> 30/tile &nbsp; | &nbsp; <b>Selling Price:</b> 50/tile &nbsp; | &nbsp; <b>Budget:</b> 100</p><p>Baseline annual profit before any activity: {(80*.75*50)-(80*30):,.1f}</p></div>",unsafe_allow_html=True)
    else:
        latest=state["history"][-1];m1,m2,m3,m4,m5=st.columns(5);m1.metric("Productivity",f"{latest['productivity']:.1f}");m2.metric("Quality",f"{latest['quality']:.1%}");m3.metric("Manufacturing Cost",f"{latest['manufacturing_cost']:.1f}");m4.metric("Landed Cost",f"{latest['landed_cost']:.2f}");m5.metric("Annual Profit",f"{latest['annual_profit']:.1f}");st.markdown(f"<div class='insight'><b>Year {state['year']} diagnosis:</b> {latest['diagnosis']}<br><b>Active maturity:</b> {latest['stages']}</div>",unsafe_allow_html=True);trend(state["history"])

    # Required position: action bar at the bottom, immediately above activities.
    action_bar(state["year"])

    if state["year"]<4:
        year=state["year"]+1;used=set(state["selections"].values());available=[name for name,a in ACTIVITIES.items() if name not in used and a["fixed_cost"]<=state["budget"]]
        st.subheader(f"Year {year}: Select One Activity")
        st.caption("An activity can be selected only once. A selected activity continues in later years and advances from R1 to R4.")
        cols=st.columns(2)
        for idx,(name,activity) in enumerate(ACTIVITIES.items()):
            with cols[idx%2]:st.markdown(activity_table_html(name,activity,name in used or activity["fixed_cost"]>state["budget"]),unsafe_allow_html=True)
        selected=st.selectbox("Choose the Year activity",available,index=None,placeholder="Select one activity",key=f"selection_year_{year}");st.session_state.selected_activity=selected
        if selected:
            a=ACTIVITIES[selected];x,y,z=st.columns(3);x.metric("Current Budget",f"{state['budget']:.0f}");y.metric("Selected Fixed Cost",f"{a['fixed_cost']:.0f}");z.metric("Budget After",f"{state['budget']-a['fixed_cost']:.0f}")
        st.button(f"Run Year {year} ▶",type="primary",use_container_width=True,disabled=not selected,on_click=run_year)
    else:
        st.success(f"Simulation complete. Four-year cumulative profit: {state['cumulative_profit']:,.1f}. Budget remaining: {state['budget']:,.1f}.")
        st.info("Leaderboard ranking is based only on cumulative profit. Unspent budget does not reduce the final ranking score.")
    leaderboard_section()

if st.session_state.get("registered"):dashboard_page()
else:registration_page()
