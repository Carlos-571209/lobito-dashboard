import streamlit as st
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Lobito Refinery Dashboard", layout="wide", initial_sidebar_state="expanded")

# 2. Sidebar: Inputs & Stress Tests (Defaults matched to Excel Base Case)
st.sidebar.header("Macroeconomic Inputs (WACC)")
rf = st.sidebar.slider("US 10-Year Treasury Yield (%)", 0.0, 10.0, 4.30, 0.1) / 100
beta = st.sidebar.slider("Refining Industry Beta", 0.5, 2.0, 1.10, 0.01)
erp = st.sidebar.slider("Equity Risk Premium (%)", 0.0, 10.0, 5.50, 0.1) / 100
crp = st.sidebar.slider("Angola Country Risk Premium (%)", 0.0, 15.0, 7.20, 0.1) / 100

st.sidebar.divider()

st.sidebar.header("Project Stress Tests")
capex_stress = st.sidebar.slider("CAPEX Overrun/Savings (%)", -30, 50, 0, 1) / 100
rev_stress = st.sidebar.slider("Refining Margin Stress (%)", -30, 30, 0, 1) / 100

# 3. Base Project Parameters
base_capex = 4305.8
base_rev = 11050.0
base_opex = 10260.0

# Apply Stress Tests
live_capex = base_capex * (1 + capex_stress)
live_rev = base_rev * (1 + rev_stress)

debt_ratio = 0.70
cost_of_debt = 0.05
debt_term = 15
tax_rate = 0.25
tax_holiday = 15

# Calculate WACC - Target: 8.765%
cost_of_equity = rf + (beta * erp) + crp
wacc = ((1 - debt_ratio) * cost_of_equity) + (debt_ratio * cost_of_debt)

# 4. Cash Flow Timeline Array Generation (32 Years: 2025-2056)
years = np.arange(2025, 2057)
n_years = len(years)

capex_schedule = np.zeros(n_years)
capex_schedule[0], capex_schedule[1], capex_schedule[2] = live_capex*0.20, live_capex*0.40, live_capex*0.40

capacity = np.zeros(n_years)
capacity[3], capacity[4], capacity[5:] = 0.90, 0.95, 1.00 

revenues = capacity * live_rev
opex = capacity * base_opex
ebitda = revenues - opex

depreciation = np.zeros(n_years)
depreciation[3:3+20] = live_capex / 20

# Debt Schedule
total_debt = live_capex * debt_ratio
debt_service = np.zeros(n_years)
interest = np.zeros(n_years)

pmt = total_debt * (cost_of_debt * (1 + cost_of_debt)**debt_term) / ((1 + cost_of_debt)**debt_term - 1)

balance = total_debt
for i in range(n_years):
    if i >= 3 and i < (3 + debt_term):
        interest[i] = balance * cost_of_debt
        debt_service[i] = pmt
        balance -= (pmt - interest[i])

# Tax & CFADS Schedule - Corrected Tax Holiday Logic
ebt = ebitda - depreciation - interest
taxes = np.zeros(n_years)
for i in range(n_years):
    # Year 3 is start of ops; holiday ends after Year 15 of ops (i=18)
    if i >= (3 + tax_holiday) and ebt[i] > 0:
        taxes[i] = ebt[i] * tax_rate

cfads = ebitda - taxes
fcff = ebitda - capex_schedule - taxes

# DSCR Calculation
dscr_array = np.zeros(n_years)
for i in range(n_years):
    if debt_service[i] > 0:
        dscr_array[i] = cfads[i] / debt_service[i]
min_dscr = np.min(dscr_array[dscr_array > 0]) if np.any(dscr_array > 0) else 0

# Valuation - Reconciled to $2,639.3 MM NPV
project_npv = npf.npv(wacc, fcff) 
project_irr = npf.irr(fcff)

# 5. Main Dashboard Interface
st.title("Lobito Refinery: Project Finance Dashboard")

# Top KPI Banner
col1, col2, col3, col4 = st.columns(4)
col1.metric("Calculated WACC", f"{wacc*100:.2f}%")
col2.metric("Project IRR (Unlevered)", f"{project_irr*100:.2f}%")
col3.metric("Project NPV (MM USD)", f"${project_npv:,.1f}")

if min_dscr >= 1.25:
    col4.metric("Minimum DSCR", f"{min_dscr:.2f}x", "Bankable")
else:
    col4.metric("Minimum DSCR", f"{min_dscr:.2f}x", "High Risk")

st.divider()

# 6. Interactive Visualizations - Full Project Life
st.subheader("Cash Flow Available for Debt Service (CFADS) vs. Debt Obligations")
st.write("**Full Timeline (2025-2056) visualizing Tax Holiday Step-Down**")

chart_years = years[3:] # Operating years
chart_cfads = cfads[3:]
chart_debt = debt_service[3:]

fig = go.Figure()
fig.add_trace(go.Bar(x=chart_years, y=chart_cfads, name='CFADS', marker_color='#2CA02C'))
fig.add_trace(go.Scatter(x=chart_years, y=chart_debt, name='Total Debt Service', mode='lines', line=dict(color='#FF0000', width=3)))

fig.update_layout(
    xaxis_title="Operating Year",
    yaxis_title="Cash Flow (MM USD)",
    barmode='group',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor='white'
)
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

st.plotly_chart(fig, use_container_width=True)
