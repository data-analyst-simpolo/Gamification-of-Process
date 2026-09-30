import base64
import io
import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Profit Optimization Challenge",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# MODEL CONFIGURATION
# Exact magnitudes remain internal. Participant-facing activity cards show only
# Increase, Decrease, or No change.
# -----------------------------------------------------------------------------
MODEL = {
    "starting_budget": 100,
    "selling_price": 50,
    "baseline": {
        "productivity": 80,
        "quality": 0.75,
        "manufacturing_cost": 30,
    },
    "repeat_multipliers": [1.0, 0.4, 0.15],
    "activities": {
        "Statistical Process Control": {
            "icon": "📊",
            "investment": 15,
            "productivity_gain": [0, 1, 2, 2],
            "quality_gain": [0.03, 0.04, 0.05, 0.05],
            "cost_reduction": [1, 2, 3, 3],
        },
        "Preventive Maintenance": {
            "icon": "🔧",
            "investment": 15,
            "productivity_gain": [2, 3, 4, 5],
            "quality_gain": [0.01, 0.02, 0.03, 0.03],
            "cost_reduction": [1, 2, 2.5, 3],
        },
        "SMED Changeover Optimization": {
            "icon": "⏱️",
            "investment": 20,
            "productivity_gain": [8, 10, 12, 13],
            "quality_gain": [0, 0.01, 0.02, 0.02],
            "cost_reduction": [1.5, 2.5, 3, 3.5],
        },
        "Operator Training & Performance Management": {
            "icon": "👷",
            "investment": 10,
            "productivity_gain": [3, 4, 5, 6],
            "quality_gain": [0.02, 0.03, 0.04, 0.04],
            "cost_reduction": [0.5, 1, 1.5, 2],
        },
        "Additional Equipment Installation": {
            "icon": "🏗️",
            "investment": 30,
            "productivity_gain": [4, 7, 10, 15],
            "quality_gain": [0, 0, 0.01, 0.01],
            "cost_reduction": [0.5, 1, 1.5, 2],
        },
        "Increase Bottleneck Speed": {
            "icon": "⚙️",
            "investment": 20,
            "productivity_gain": [10, 12, 12, 10],
            "quality_gain": [-0.04, -0.04, -0.03, -0.03],
            "cost_reduction": [0.5, 0.5, 1, 1],
        },
    },
    "optimal_benchmark": {
        "year_1": {
            "productivity": 83,
            "quality": 0.80,
            "manufacturing_cost": 28.5,
            "profit": 929.5,
        },
        "year_2": {
            "productivity": 96,
            "quality": 0.83,
            "manufacturing_cost": 24,
            "profit": 1645,
        },
        "year_3": {
            "productivity": 98.4,
            "quality": 0.862,
            "manufacturing_cost": 21.8,
            "profit": 2065.92,
        },
        "year_4": {
            "productivity": 100.8,
            "quality": 0.878,
            "manufacturing_cost": 21,
            "profit": 2298.32,
        },
    },
}

BASE = MODEL["baseline"]
ACTIVITIES = MODEL["activities"]
LEADERBOARD_PATH = "data/leaderboard.csv"
LOG_PATH = "data/simulation_log.csv"

LEADERBOARD_COLUMNS = [
    "Session ID",
    "Team Name",
    "Team Members",
    "Year",
    "Productivity",
    "Quality %",
    "Landed Cost",
    "Selling Price",
    "Annual Net Profit",
    "Cumulative Net Profit",
    "Budget Remaining",
    "Eligible Score",
    "Updated At",
]

LOG_COLUMNS = [
    "Session ID",
    "Team Name",
    "Team Members",
    "Year",
    "Activity 1",
    "Activity 2",
    "Deployment Counts",
    "Productivity",
    "Quality %",
    "Manufacturing Cost",
    "Investment",
    "Landed Cost",
    "Selling Price",
    "Annual Net Profit",
    "Cumulative Net Profit",
    "Budget Remaining",
    "Diagnosis",
    "Created At",
]

# -----------------------------------------------------------------------------
# UI STYLE
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
.stApp {
    background: radial-gradient(circle at 8% 4%, #dcfce7 0, transparent 22%),
                linear-gradient(135deg, #f8fffa, #eef7f0);
}
.block-container {
    max-width: 1320px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}
#MainMenu, footer {visibility: hidden;}
.hero {
    padding: 1.8rem 2rem;
    border-radius: 25px;
    background: linear-gradient(125deg, #103d27, #166534 52%, #16a34a);
    color: white;
    box-shadow: 0 18px 48px rgba(20, 83, 45, .20);
    margin-bottom: 1rem;
}
.hero h1 {margin: 0;}
.hero p {margin: .4rem 0 0; opacity: .9;}
.baseline {
    padding: 1rem;
    border-radius: 16px;
    background: #ecfeff;
    border: 1px solid #67e8f9;
    margin: .8rem 0;
}
.activity {
    background: white;
    border: 1px solid #d9e8de;
    border-radius: 17px;
    padding: .9rem;
    height: 100%;
    box-shadow: 0 8px 22px rgba(20, 83, 45, .07);
}
.activity.locked {opacity: .42; filter: grayscale(.8);}
.activity .ico {font-size: 2rem;}
.activity h4 {margin: .25rem 0;}
.activity p {font-size: .84rem; color: #64748b; margin: .2rem 0;}
.impact {
    margin-top: .55rem;
    padding: .65rem;
    border-radius: 10px;
    background: #f8fafc;
    border: 1px solid #dbe5df;
    font-size: .82rem;
    line-height: 1.55;
}
.gain {color: #166534; font-weight: 700;}
.loss {color: #b91c1c; font-weight: 700;}
.neutral {color: #475569; font-weight: 700;}
.insight {
    padding: .9rem 1rem;
    border-radius: 14px;
    background: #eff6ff;
    border: 1px solid #93c5fd;
    margin: .7rem 0;
}
.yearbox {
    padding: 1rem;
    border-radius: 16px;
    background: #fff7ed;
    border: 1px solid #fdba74;
    margin: .8rem 0;
}
.process-wrap {
    background: white;
    border: 1px solid #b9d8c1;
    border-radius: 22px;
    padding: 1rem;
    overflow-x: auto;
}
.process-line {
    min-width: 1000px;
    display: flex;
    align-items: center;
    gap: 10px;
    position: relative;
    padding: 20px 10px 48px;
}
.unit {
    width: 145px;
    min-height: 80px;
    border: 2px solid #15803d;
    border-radius: 13px;
    background: #eefbf1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-weight: 750;
}
.unit span {font-size: 1.8rem;}
.arrow {width: 48px; height: 12px; background: #15803d; position: relative;}
.arrow:after {
    content: "";
    position: absolute;
    right: -13px;
    top: -7px;
    border-left: 14px solid #15803d;
    border-top: 13px solid transparent;
    border-bottom: 13px solid transparent;
}
.belt {
    position: absolute;
    left: 15px;
    right: 15px;
    bottom: 18px;
    height: 10px;
    border-radius: 6px;
    background: repeating-linear-gradient(90deg, #14532d 0 24px, #86efac 24px 38px);
    animation: belt .75s linear infinite;
}
.tile {
    position: absolute;
    bottom: 29px;
    width: 34px;
    height: 20px;
    background: #f59e0b;
    border: 2px solid #9a5a06;
    border-radius: 3px;
    animation: move 8s linear infinite;
}
.tile.t2 {animation-delay: -2.7s;}
.tile.t3 {animation-delay: -5.4s;}
@keyframes belt {to {background-position: 38px 0;}}
@keyframes move {0% {left: 2%;} 100% {left: 95%;}}
.stButton > button, .stFormSubmitButton > button {
    border-radius: 12px;
    min-height: 45px;
    font-weight: 700;
}
.stFormSubmitButton > button {
    background: #15803d !important;
    color: white !important;
    border: 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# OPTIONAL GITHUB STORAGE
# -----------------------------------------------------------------------------
def github_configured():
    return all(
        str(st.secrets.get(key, "")).strip()
        for key in ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"]
    )


def github_headers():
    return {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_url(path):
    return (
        f"https://api.github.com/repos/{st.secrets['GITHUB_OWNER']}/"
        f"{st.secrets['GITHUB_REPO']}/contents/{path}"
    )


def read_remote_csv(path, columns):
    response = requests.get(
        github_url(path),
        headers=github_headers(),
        params={"ref": st.secrets.get("GITHUB_BRANCH", "main")},
        timeout=30,
    )
    if response.status_code == 404:
        return pd.DataFrame(columns=columns), None
    response.raise_for_status()
    payload = response.json()
    try:
        frame = pd.read_csv(io.BytesIO(base64.b64decode(payload["content"])))
    except pd.errors.EmptyDataError:
        frame = pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame:
            frame[column] = ""
    return frame[columns], payload["sha"]


def write_remote_csv(path, frame, columns, sha, message):
    body = {
        "message": message,
        "content": base64.b64encode(
            frame[columns].to_csv(index=False).encode("utf-8")
        ).decode(),
        "branch": st.secrets.get("GITHUB_BRANCH", "main"),
    }
    if sha:
        body["sha"] = sha
    response = requests.put(
        github_url(path), headers=github_headers(), json=body, timeout=30
    )
    response.raise_for_status()


def append_remote_csv(path, row, columns, message):
    frame, sha = read_remote_csv(path, columns)
    frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    write_remote_csv(path, frame, columns, sha, message)


def update_leaderboard(row):
    if github_configured():
        frame, sha = read_remote_csv(LEADERBOARD_PATH, LEADERBOARD_COLUMNS)
        frame = frame[
            ~frame["Session ID"].astype(str).eq(str(row["Session ID"]))
        ]
        frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
        write_remote_csv(
            LEADERBOARD_PATH,
            frame,
            LEADERBOARD_COLUMNS,
            sha,
            "Update profit optimization leaderboard",
        )

    local = st.session_state.get(
        "local_leaderboard", pd.DataFrame(columns=LEADERBOARD_COLUMNS)
    )
    local = local[
        ~local["Session ID"].astype(str).eq(str(row["Session ID"]))
    ]
    st.session_state.local_leaderboard = pd.concat(
        [local, pd.DataFrame([row])], ignore_index=True
    )


def leaderboard_data():
    if github_configured():
        try:
            return read_remote_csv(LEADERBOARD_PATH, LEADERBOARD_COLUMNS)[0]
        except Exception as error:
            st.caption(f"Shared leaderboard unavailable: {error}")
    return st.session_state.get(
        "local_leaderboard", pd.DataFrame(columns=LEADERBOARD_COLUMNS)
    )

# -----------------------------------------------------------------------------
# SIMULATION ENGINE
# -----------------------------------------------------------------------------
def initial_state():
    return {
        "year": 0,
        "budget": float(MODEL["starting_budget"]),
        "productivity": float(BASE["productivity"]),
        "quality": float(BASE["quality"]),
        "manufacturing_cost": float(BASE["manufacturing_cost"]),
        "cumulative_profit": 0.0,
        "deployment_counts": {},
        "history": [],
    }


def repeat_multiplier(previous_deployments):
    multipliers = MODEL["repeat_multipliers"]
    return multipliers[min(previous_deployments, len(multipliers) - 1)]


def calculate_activity_effect(activity_name, year, previous_deployments):
    activity = ACTIVITIES[activity_name]
    year_index = year - 1
    multiplier = repeat_multiplier(previous_deployments)
    return {
        "productivity": activity["productivity_gain"][year_index] * multiplier,
        "quality": activity["quality_gain"][year_index] * multiplier,
        "cost_reduction": activity["cost_reduction"][year_index] * multiplier,
        "multiplier": multiplier,
    }


def diagnosis(metrics, year, previous=None):
    benchmark = MODEL["optimal_benchmark"][f"year_{year}"]
    messages = []

    comparisons = [
        ("Productivity", "productivity", benchmark["productivity"], True),
        ("Quality", "quality", benchmark["quality"], True),
        (
            "Manufacturing cost",
            "manufacturing_cost",
            benchmark["manufacturing_cost"],
            False,
        ),
    ]

    for label, key, target, higher_is_better in comparisons:
        actual = metrics[key]
        is_good = actual >= target if higher_is_better else actual <= target
        messages.append(
            f"{'Gaining' if is_good else 'Lacking'}: {label} is "
            f"{actual:.2f} versus the optimized benchmark {target:.2f}."
        )

    if previous:
        difference = metrics["annual_profit"] - previous["annual_profit"]
        messages.append(
            f"Annual net profit {'increased' if difference >= 0 else 'decreased'} "
            f"by {abs(difference):.2f} versus the previous year."
        )

    return " ".join(messages)


def run_year():
    state = st.session_state.simulation_state.copy()
    state["deployment_counts"] = state["deployment_counts"].copy()
    state["history"] = list(state["history"])
    year = state["year"] + 1

    action_1 = st.session_state.get("selected_activity_1", "None")
    action_2 = st.session_state.get("selected_activity_2", "None")
    selected = [a for a in [action_1, action_2] if a != "None"]

    required = 2 if year <= 3 else 1
    if len(selected) < required:
        st.error(
            f"Year {year} requires {'exactly two activities' if year <= 3 else 'at least one activity'}."
        )
        return
    if len(set(selected)) != len(selected):
        st.error("Select two different activities in the same year.")
        return

    current_investment = sum(ACTIVITIES[a]["investment"] for a in selected)
    if current_investment > state["budget"]:
        st.error("Selected activities exceed the remaining budget.")
        return

    effects = []
    deployment_notes = []
    for activity_name in selected:
        previous_count = state["deployment_counts"].get(activity_name, 0)
        activity_effect = calculate_activity_effect(
            activity_name, year, previous_count
        )
        effects.append(activity_effect)
        state["deployment_counts"][activity_name] = previous_count + 1
        deployment_notes.append(
            f"{activity_name}: deployment {previous_count + 1}"
        )

    productivity = state["productivity"] + sum(e["productivity"] for e in effects)
    quality = max(
        0.0,
        min(1.0, state["quality"] + sum(e["quality"] for e in effects)),
    )
    manufacturing_cost = max(
        0.0,
        state["manufacturing_cost"]
        - sum(e["cost_reduction"] for e in effects),
    )

    good_tiles = productivity * quality
    landed_cost = (
        productivity * manufacturing_cost + current_investment
    ) / good_tiles
    annual_profit = (
        good_tiles * MODEL["selling_price"]
        - productivity * manufacturing_cost
        - current_investment
    )

    previous = state["history"][-1] if state["history"] else None
    metrics = {
        "year": year,
        "productivity": productivity,
        "quality": quality,
        "manufacturing_cost": manufacturing_cost,
        "landed_cost": landed_cost,
        "annual_profit": annual_profit,
        "investment": current_investment,
        "selected": selected,
        "deployment_notes": " | ".join(deployment_notes),
    }
    metrics["diagnosis"] = diagnosis(metrics, year, previous)

    state["year"] = year
    state["budget"] -= current_investment
    state["productivity"] = productivity
    state["quality"] = quality
    state["manufacturing_cost"] = manufacturing_cost
    state["cumulative_profit"] += annual_profit
    state["history"].append(metrics)
    st.session_state.simulation_state = state

    eligible_score = (
        state["cumulative_profit"]
        if year == 4 and state["budget"] == 0
        else state["cumulative_profit"]
        - (state["budget"] * 100 if year == 4 else 0)
    )

    leaderboard_row = {
        "Session ID": st.session_state.session_id,
        "Team Name": st.session_state.team_name,
        "Team Members": st.session_state.team_members,
        "Year": year,
        "Productivity": productivity,
        "Quality %": quality * 100,
        "Landed Cost": landed_cost,
        "Selling Price": MODEL["selling_price"],
        "Annual Net Profit": annual_profit,
        "Cumulative Net Profit": state["cumulative_profit"],
        "Budget Remaining": state["budget"],
        "Eligible Score": eligible_score,
        "Updated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    update_leaderboard(leaderboard_row)

    if github_configured():
        log_row = {
            "Session ID": st.session_state.session_id,
            "Team Name": st.session_state.team_name,
            "Team Members": st.session_state.team_members,
            "Year": year,
            "Activity 1": action_1,
            "Activity 2": action_2,
            "Deployment Counts": " | ".join(
                f"{name}:{count}"
                for name, count in state["deployment_counts"].items()
            ),
            "Productivity": productivity,
            "Quality %": quality * 100,
            "Manufacturing Cost": manufacturing_cost,
            "Investment": current_investment,
            "Landed Cost": landed_cost,
            "Selling Price": MODEL["selling_price"],
            "Annual Net Profit": annual_profit,
            "Cumulative Net Profit": state["cumulative_profit"],
            "Budget Remaining": state["budget"],
            "Diagnosis": metrics["diagnosis"],
            "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            append_remote_csv(
                LOG_PATH,
                log_row,
                LOG_COLUMNS,
                f"Add Year {year} result",
            )
        except Exception as error:
            st.warning(f"Year completed; GitHub save failed: {error}")

    st.rerun()

# -----------------------------------------------------------------------------
# PRESENTATION HELPERS
# -----------------------------------------------------------------------------
def hero():
    st.markdown(
        """
<div class="hero">
<h1>🏆 Four-Year Profit Optimization Challenge</h1>
<p>Deploy two activities in Years 1–3 and at least one in Year 4. Spend the full budget and maximize profit.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def live_conveyor(productivity):
    duration = max(2.7, min(14, 900 / max(productivity, 1)))
    st.markdown(
        f"""
<div class="process-wrap"><div class="process-line">
<div class="unit"><span>🧱</span>Inputs</div><div class="arrow"></div>
<div class="unit"><span>🏭</span>Production</div><div class="arrow"></div>
<div class="unit"><span>✅</span>Quality</div><div class="arrow"></div>
<div class="unit"><span>🚚</span>Landed Cost</div><div class="arrow"></div>
<div class="unit"><span>💰</span>Profit</div>
<div class="belt"></div>
<div class="tile" style="animation-duration:{duration}s"></div>
<div class="tile t2" style="animation-duration:{duration}s"></div>
<div class="tile t3" style="animation-duration:{duration}s"></div>
</div></div>
""",
        unsafe_allow_html=True,
    )


def qualitative_direction(value, beneficial_when_positive=True):
    """Return qualitative participant-facing text without revealing magnitude."""
    if abs(value) < 1e-12:
        return "neutral", "•", "No change"

    is_beneficial = value > 0 if beneficial_when_positive else value < 0
    if is_beneficial:
        return "gain", "▲", "Increase" if beneficial_when_positive else "Decrease"
    return "loss", "▼", "Decrease" if beneficial_when_positive else "Increase"


def activity_effect_html(activity_name, year, previous_deployments):
    """Show direction only. Exact numerical values remain hidden."""
    effect = calculate_activity_effect(
        activity_name, year, previous_deployments
    )

    p_class, p_arrow, p_text = qualitative_direction(
        effect["productivity"], beneficial_when_positive=True
    )
    q_class, q_arrow, q_text = qualitative_direction(
        effect["quality"], beneficial_when_positive=True
    )

    # Cost reduction > 0 means manufacturing cost decreases.
    if abs(effect["cost_reduction"]) < 1e-12:
        c_class, c_arrow, c_text = "neutral", "•", "No change"
    elif effect["cost_reduction"] > 0:
        c_class, c_arrow, c_text = "gain", "▲", "Decrease"
    else:
        c_class, c_arrow, c_text = "loss", "▼", "Increase"

    return f"""
<div class="{p_class}">{p_arrow} Productivity: {p_text}</div>
<div class="{q_class}">{q_arrow} Quality: {q_text}</div>
<div class="{c_class}">{c_arrow} Manufacturing Cost: {c_text}</div>
"""


def activity_cards(state, year):
    columns = st.columns(3)

    for index, (name, activity) in enumerate(ACTIVITIES.items()):
        previous_count = state["deployment_counts"].get(name, 0)
        locked = (
            activity["investment"] > state["budget"]
            or previous_count >= 3
        )
        card_class = "activity locked" if locked else "activity"

        with columns[index % 3]:
            st.markdown(
                f"""
<div class="{card_class}">
<div class="ico">{activity['icon']}</div>
<h4>{name}</h4>
<p><b>Proposed deployment: {previous_count + 1}</b></p>
<div class="impact">
{activity_effect_html(name, year, previous_count)}
</div>
<p><b>Budget required: {activity['investment']} points</b></p>
</div>
""",
                unsafe_allow_html=True,
            )

    available = [
        name
        for name, activity in ACTIVITIES.items()
        if activity["investment"] <= state["budget"]
        and state["deployment_counts"].get(name, 0) < 3
    ]

    left, right = st.columns(2)
    action_1 = left.selectbox(
        "Activity 1",
        ["None"] + available,
        key=f"activity_1_year_{year}",
    )

    remaining_after_first = state["budget"] - (
        ACTIVITIES[action_1]["investment"] if action_1 != "None" else 0
    )
    second_options = [
        name
        for name in available
        if name != action_1
        and ACTIVITIES[name]["investment"] <= remaining_after_first
    ]
    action_2 = right.selectbox(
        "Activity 2",
        ["None"] + second_options,
        key=f"activity_2_year_{year}",
    )

    st.session_state.selected_activity_1 = action_1
    st.session_state.selected_activity_2 = action_2

    selected = [a for a in [action_1, action_2] if a != "None"]
    selected_cost = sum(ACTIVITIES[a]["investment"] for a in selected)

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Current Budget", f"{state['budget']:.0f}")
    metric_2.metric("Selected Investment", f"{selected_cost:.0f}")
    metric_3.metric("Budget After", f"{state['budget'] - selected_cost:.0f}")

    required = 2 if year <= 3 else 1
    valid_count = len(selected) == 2 if year <= 3 else len(selected) >= 1
    st.caption(
        "Selection requirement: exactly two different activities."
        if year <= 3
        else "Selection requirement: at least one activity."
    )
    st.button(
        f"Run Year {year} ▶",
        type="primary",
        use_container_width=True,
        disabled=(not valid_count or selected_cost > state["budget"]),
        on_click=run_year,
    )


def result_trend(history):
    frame = pd.DataFrame(history)
    x_values = [f"Year {int(year)}" for year in frame["year"]]

    figure = go.Figure()
    figure.add_bar(
        x=x_values,
        y=frame["annual_profit"],
        name="Annual Net Profit",
        marker_color="#15803d",
    )
    figure.add_scatter(
        x=x_values,
        y=frame["landed_cost"],
        name="Landed Cost",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color="#f59e0b"),
    )
    figure.update_layout(
        title="Profit and Landed Cost Trend",
        yaxis_title="Annual Net Profit",
        yaxis2=dict(
            title="Landed Cost per Good Tile",
            overlaying="y",
            side="right",
        ),
    )
    st.plotly_chart(figure, use_container_width=True)


def leaderboard_section():
    st.subheader("🏅 Live Leaderboard")
    leaderboard = leaderboard_data()
    if leaderboard.empty:
        st.info("Complete a year to populate the leaderboard.")
        return

    for column in [
        "Eligible Score",
        "Cumulative Net Profit",
        "Budget Remaining",
    ]:
        leaderboard[column] = pd.to_numeric(
            leaderboard[column], errors="coerce"
        )

    leaderboard = leaderboard.sort_values(
        ["Eligible Score", "Cumulative Net Profit"],
        ascending=[False, False],
    ).reset_index(drop=True)
    leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))

    st.dataframe(
        leaderboard[
            [
                "Rank",
                "Team Name",
                "Team Members",
                "Year",
                "Cumulative Net Profit",
                "Budget Remaining",
                "Eligible Score",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------------------------------------------------------
# PAGES
# -----------------------------------------------------------------------------
def registration_page():
    hero()
    live_conveyor(BASE["productivity"])
    _, center, _ = st.columns([1, 1.5, 1])

    with center:
        with st.form("team_registration"):
            st.subheader("Register Your Team")
            team_name = st.text_input(
                "Team Name *",
                placeholder="Enter a unique team name",
            )
            team_members = st.text_area(
                "Team Members *",
                placeholder="Enter team-member names separated by commas",
                height=120,
            )
            submitted = st.form_submit_button(
                "Start Challenge →",
                use_container_width=True,
            )

        if submitted:
            if not team_name.strip():
                st.error("Please enter the Team Name.")
            elif not team_members.strip():
                st.error("Please enter at least one Team Member.")
            else:
                st.session_state.update(
                    registered=True,
                    session_id=str(uuid.uuid4()),
                    team_name=team_name.strip(),
                    team_members=team_members.strip(),
                    simulation_state=initial_state(),
                    local_leaderboard=pd.DataFrame(
                        columns=LEADERBOARD_COLUMNS
                    ),
                )
                st.rerun()


def dashboard_page():
    hero()
    state = st.session_state.simulation_state
    live_conveyor(state["productivity"])

    with st.sidebar:
        st.success(f"Team: {st.session_state.team_name}")
        st.write("**Team Members**")
        st.write(st.session_state.team_members)
        st.metric("Year", f"{state['year']} / 4")
        st.metric("Budget", f"{state['budget']:.0f}")
        st.metric(
            "Cumulative Profit",
            f"{state['cumulative_profit']:.2f}",
        )
        if st.button("Restart Simulation", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if not state["history"]:
        st.markdown(
            """
<div class="baseline">
<h3>Year 0 Fixed Baseline</h3>
<p>Productivity: 80 tiles/day | Quality: 75% | Manufacturing Cost: 30/tile | Selling Price: 50/tile</p>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        latest = state["history"][-1]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Productivity", f"{latest['productivity']:.1f}")
        m2.metric("Quality", f"{latest['quality']:.1%}")
        m3.metric("Landed Cost", f"{latest['landed_cost']:.2f}")
        m4.metric("Selling Price", f"{MODEL['selling_price']:.2f}")
        m5.metric("Annual Net Profit", f"{latest['annual_profit']:.2f}")

        st.markdown(
            f"<div class='insight'><b>Year {state['year']} diagnosis:</b> "
            f"{latest['diagnosis']}</div>",
            unsafe_allow_html=True,
        )
        result_trend(state["history"])

    with st.expander("📐 Model logic"):
        st.markdown(
            """
The exact mathematical effects are applied internally, but participants see only the direction of impact on the activity cards.

```text
Productivity_y = Productivity_(y-1)
                 + Σ Internal Productivity Effect

Quality_y = MIN(100%, Quality_(y-1)
                + Σ Internal Quality Effect)

Manufacturing Cost_y = MAX(0, Manufacturing Cost_(y-1)
                           - Σ Internal Cost Reduction)

Good Tiles = Productivity_y × Quality_y

Landed Cost = (Productivity_y × Manufacturing Cost_y
               + Annual Investment) / Good Tiles

Annual Net Profit = Good Tiles × Selling Price
                    - Productivity_y × Manufacturing Cost_y
                    - Annual Investment
```

Repeated improvement waves have diminishing returns internally, but the magnitude is intentionally hidden from participants.
"""
        )

    if state["year"] < 4:
        year = state["year"] + 1
        instruction = (
            "Select exactly two different activities."
            if year <= 3
            else "Select at least one activity."
        )
        st.markdown(
            f"""
<div class="yearbox">
<h3>Year {year} Decision</h3>
<p>{instruction} Activity cards show only whether productivity, quality, and manufacturing cost will increase, decrease, or remain unchanged.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        activity_cards(state, year)
    else:
        if state["budget"] == 0:
            st.success(
                f"Challenge complete. Full budget used. Cumulative profit: "
                f"{state['cumulative_profit']:.2f}"
            )
        else:
            st.warning(
                f"Challenge complete with {state['budget']:.0f} unspent budget. "
                "The eligible score includes an unspent-budget penalty."
            )

    leaderboard_section()


if st.session_state.get("registered"):
    dashboard_page()
else:
    registration_page()
