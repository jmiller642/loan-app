import streamlit as st
import pandas as pd
import datetime
import numpy as np

st.title("Comprehensive Loan Cost & Payment Calculator")

# --- Property Type Selection ---
property_type = st.selectbox(
    "Select Property Type",
    ["Attached", "Detached", "Manufactured", "Condo"]
)

# --- Loan Program Selection ---
loan_program = st.selectbox(
    "Select Loan Program",
    ["Conventional", "FHA", "VA", "USDA"]
)

# --- Purchase Price ---
purchase_price = st.number_input(
    "Purchase Price ($)",
    min_value=10000.0,
    max_value=10000000.0,
    value=300000.0,
    step=1000.0,
    format="%.2f"
)

# --- Multiple Down Payments & Interest Rates ---
st.subheader("Compare Multiple Scenarios")
down_payment_options = st.text_input(
    "Enter Down Payments (%) separated by commas",
    "5,10,20"
)
interest_rate_options = st.text_input(
    "Enter Interest Rates (%) separated by commas",
    "6.5,7.0,7.5"
)

# --- Lender Credit ---
lender_credit = st.number_input(
    "Lender Credit ($ - enter positive number, will be subtracted)",
    min_value=0.0,
    max_value=50000.0,
    value=0.0,
    step=500.0,
    format="%.2f"
)

# --- Condo Questionnaire Fee ---
condo_questionnaire_fee = 0.0
if property_type == "Condo":
    if st.checkbox("Add $300 Condo Questionnaire Fee?"):
        condo_questionnaire_fee = 300.0

# --- Waive Escrows Option ---
waive_escrows = st.checkbox("Waive Escrows? (Taxes & Insurance not included in monthly payment or cash to close)")

# --- Fixed Costs ---
fixed_costs = {
    "Origination Fee": 1400.0,
    "Processing Fee": 995.0,
    "Underwriting Fee": 795.0,
    "Credit Report Fee": 50.0,
    "Flood Certificate Fee": 15.0,
    "Tax Service Fee": 75.0,
    "Appraisal Fee": 550.0,
}

# --- Property Taxes through Dec 31 ---
today = datetime.date.today()
months_until_year_end = max(0, 12 - today.month)
estimated_annual_taxes = 3600.0
monthly_tax = estimated_annual_taxes / 12
escrowed_taxes = monthly_tax * months_until_year_end

# --- Prepaids & Escrows ---
prepaids_escrows = {}
if not waive_escrows:
    prepaids_escrows["Homeowners Insurance (12 mo)"] = 1200.0
    prepaids_escrows[f"Property Taxes (through Dec 31)"] = round(escrowed_taxes, 2)
# Interim interest always collected
prepaids_escrows["Interim Interest"] = 500.0

# --- Monthly Taxes & Insurance (or $0 if waiving) ---
monthly_homeowners = 0.0 if waive_escrows else 1200.0 / 12
monthly_prop_taxes = 0.0 if waive_escrows else monthly_tax

# --- Upfront Insurance Costs ---
if loan_program == "FHA":
    upfront_insurance = lambda loan_amt: loan_amt * 0.0175
elif loan_program == "VA":
    upfront_insurance = lambda loan_amt: loan_amt * 0.023
elif loan_program == "USDA":
    upfront_insurance = lambda loan_amt: loan_amt * 0.01
else:
    upfront_insurance = lambda loan_amt: 0.0

# --- Multiple Scenario Calculations ---
dp_values = [float(x.strip()) for x in down_payment_options.split(",")]
ir_values = [float(x.strip()) for x in interest_rate_options.split(",")]

scenario_data = {}

for dp in dp_values:
    down_payment_amount = purchase_price * (dp / 100.0)
    loan_amount = purchase_price - down_payment_amount
    
    upfront_fee = upfront_insurance(loan_amount)
    total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
    total_prepaids = sum(prepaids_escrows.values())
    cash_to_close = down_payment_amount + total_fixed + total_prepaids + upfront_fee - lender_credit

    for ir in ir_values:
        monthly_rate = ir / 100 / 12
        n_payments = 360

        if monthly_rate > 0:
            monthly_pi = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        else:
            monthly_pi = loan_amount / n_payments

        total_monthly = monthly_pi + monthly_homeowners + monthly_prop_taxes
        
        scenario_label = f"{dp:.0f}% @ {ir:.2f}%"
        scenario_data[scenario_label] = {
            "Loan Amount": round(loan_amount, 2),
            "P&I": round(monthly_pi, 2),
            "Taxes": round(monthly_prop_taxes, 2),
            "Insurance": round(monthly_homeowners, 2),
            "Total Monthly": round(total_monthly, 2),
            "Cash to Close": round(cash_to_close, 2)
        }

# Create DataFrame with vertical categories and scenarios across columns
df_scenarios = pd.DataFrame(scenario_data).rename_axis("Category").reset_index()

st.subheader("Scenario Comparison Table (Excel-Style View)")
styled_df = df_scenarios.style.format(precision=2).set_properties(**{
    'text-align': 'center'
}).set_table_styles([{
    'selector': 'th',
    'props': [('text-align', 'center'), ('font-weight', 'bold')]
}])

st.dataframe(styled_df, use_container_width=True)

# --- Detailed Costs Table for First Scenario ---
dp_first = dp_values[0]
loan_amount_first = purchase_price - purchase_price * (dp_first / 100.0)
ufmip_first = upfront_insurance(loan_amount_first)
total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
total_prepaids = sum(prepaids_escrows.values())
cash_to_close_first = purchase_price * (dp_first / 100.0) + total_fixed + total_prepaids + ufmip_first - lender_credit

costs_table = {
    "Description": [],
    "Amount ($)": []
}

costs_table["Description"].append("Down Payment")
costs_table["Amount ($)"].append(round(purchase_price * (dp_first / 100.0), 2))

for desc, amount in fixed_costs.items():
    costs_table["Description"].append(desc)
    costs_table["Amount ($)"].append(amount)

if condo_questionnaire_fee:
    costs_table["Description"].append("Condo Questionnaire Fee")
    costs_table["Amount ($)"].append(condo_questionnaire_fee)

for desc, amount in prepaids_escrows.items():
    costs_table["Description"].append(desc)
    costs_table["Amount ($)"].append(amount)

if ufmip_first > 0:
    insurance_label = {
        "FHA": "FHA UFMIP (1.75%)",
        "VA": "VA Funding Fee (2.3%)",
        "USDA": "USDA Guarantee Fee (1%)"
    }.get(loan_program, "Upfront Insurance")
    costs_table["Description"].append(insurance_label)
    costs_table["Amount ($)"].append(round(ufmip_first, 2))

if lender_credit > 0:
    costs_table["Description"].append("Lender Credit")
    costs_table["Amount ($)"].append(-lender_credit)

costs_table["Description"].append("TOTAL CASH TO CLOSE")
costs_table["Amount ($)"].append(round(cash_to_close_first, 2))

df_costs = pd.DataFrame(costs_table)
st.subheader("Detailed Costs Breakdown (First Scenario)")
st.table(df_costs)
