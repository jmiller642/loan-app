import streamlit as st
import pandas as pd
import datetime
import numpy as np

st.title("Comprehensive Loan Cost & Payment Calculator")

# --- LOAN PURPOSE ---
loan_purpose = st.selectbox(
    "What is the loan purpose?",
    ["Purchase", "Rate/Term Refinance", "Cash-Out Refinance"]
)

# --- PROPERTY TYPE ---
property_type = st.selectbox(
    "Select Property Type",
    ["Attached", "Detached", "Manufactured", "Condo"]
)

# --- LOAN PROGRAM ---
loan_program = st.selectbox(
    "Select Loan Program",
    ["Conventional", "FHA", "VA", "USDA"]
)

# --- PURCHASE PRICE ---
purchase_price = st.number_input(
    "Enter Purchase Price ($)",
    min_value=10000.0,
    max_value=10000000.0,
    value=300000.0,
    step=1000.0,
    format="%.2f"
)

# --- WAIVE ESCROWS ---
waive_escrows = st.checkbox("Waive Escrows? (Taxes & Insurance not included in monthly payment or cash to close)")

# --- CONDO QUESTIONNAIRE ---
condo_questionnaire_fee = 0.0
if property_type == "Condo":
    if st.checkbox("Add $300 Condo Questionnaire Fee?"):
        condo_questionnaire_fee = 300.0

# --- SELLER CONCESSION (PURCHASE ONLY) ---
seller_concession = 0.0
if loan_purpose == "Purchase":
    st.markdown("## Seller Concession")
    seller_concession = st.number_input(
        "Seller Concession ($)",
        min_value=0.0,
        max_value=purchase_price,
        value=0.0,
        step=500.0,
        format="%.2f"
    )

# --- NUM OF DOWN PAYMENT SCENARIOS ---
num_dp = st.number_input(
    "How many different down payment scenarios would you like to run?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)

# --- NUM OF RATE SCENARIOS ---
num_rates = st.number_input(
    "How many different interest rate scenarios would you like to run?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)

# --- DOWN PAYMENT INPUTS ---
st.markdown("## Down Payment Scenarios")
down_payments = []
for i in range(num_dp):
    dp = st.number_input(
        f"Down Payment #{i+1} (%)",
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        format="%.2f",
        key=f"dp_{i}"
    )
    down_payments.append(dp)

# --- INTEREST RATE & LENDER CREDIT INPUTS ---
st.markdown("## Interest Rate and Lender Credit Scenarios")
rate_credit_pairs = []
for i in range(num_rates):
    rate = st.number_input(
        f"Interest Rate #{i+1} (%)",
        min_value=0.0,
        max_value=20.0,
        step=0.01,
        format="%.3f",
        key=f"rate_{i}"
    )
    credit = st.number_input(
        f"Lender Credit for Rate #{i+1} ($)",
        min_value=0.0,
        max_value=50000.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        key=f"credit_{i}"
    )
    rate_credit_pairs.append((rate, credit))

# --- FIXED COSTS ---
fixed_costs = {
    "Origination Fee": 1400.0,
    "Processing Fee": 995.0,
    "Underwriting Fee": 795.0,
    "Credit Report Fee": 50.0,
    "Flood Certificate Fee": 15.0,
    "Tax Service Fee": 75.0,
    "Appraisal Fee": 550.0,
}

# --- PREPAIDS ---
today = datetime.date.today()
months_until_year_end = max(0, 12 - today.month)
estimated_annual_taxes = 3600.0
monthly_tax = estimated_annual_taxes / 12
escrowed_taxes = monthly_tax * months_until_year_end

prepaids_escrows = {}
if not waive_escrows:
    prepaids_escrows["Homeowners Insurance (12 mo)"] = 1200.0
    prepaids_escrows[f"Property Taxes (through Dec 31)"] = round(escrowed_taxes, 2)
prepaids_escrows["Interim Interest"] = 500.0

monthly_homeowners = 0.0 if waive_escrows else 1200.0 / 12
monthly_prop_taxes = 0.0 if waive_escrows else monthly_tax

# --- PMI & UPFRONT FEES ---
def upfront_fee(loan_amt, program):
    if program == "FHA":
        return loan_amt * 0.0175
    elif program == "VA":
        return loan_amt * 0.023
    elif program == "USDA":
        return loan_amt * 0.01
    else:
        return 0.0

def monthly_pmi(loan_amt, ltv):
    if loan_program == "Conventional" and ltv > 80:
        return (loan_amt * 0.0055) / 12  # e.g., 0.55% annual PMI
    return 0.0

# --- SELLER CONCESSION LIMITS ---
def max_seller_concession(dp, program):
    if program == "Conventional":
        if dp < 10: return 0.03
        elif dp <= 25: return 0.06
        else: return 0.09
    elif program == "FHA": return 0.06
    elif program == "VA": return 0.04
    elif program == "USDA": return 0.06
    else: return 0.0

scenario_data = {}

for dp in down_payments:
    dp_amount = purchase_price * (dp / 100)
    loan_amt_base = purchase_price - dp_amount
    
    max_concession_allowed = purchase_price * max_seller_concession(dp, loan_program)
    allowed_seller_credit = min(seller_concession, max_concession_allowed)
    
    upfront = upfront_fee(loan_amt_base, loan_program)
    total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
    total_prepaids = sum(prepaids_escrows.values())
    cash_to_close_base = dp_amount + total_fixed + total_prepaids + upfront - allowed_seller_credit

    for rate, lender_credit in rate_credit_pairs:
        monthly_rate = rate / 100 / 12
        n_payments = 360

        loan_amt = loan_amt_base + (upfront if loan_program in ["FHA","VA","USDA"] else 0)
        if monthly_rate > 0:
            monthly_pi = loan_amt * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        else:
            monthly_pi = loan_amt / n_payments

        ltv = 100 - dp
        pmi_monthly = monthly_pmi(loan_amt_base, ltv)

        total_monthly = monthly_pi + monthly_homeowners + monthly_prop_taxes + pmi_monthly
        final_cash_to_close = cash_to_close_base - lender_credit

        label = f"{dp:.0f}% @ {rate:.2f}%"
        scenario_data[label] = {
            "Loan Amount": round(loan_amt, 2),
            "P&I": round(monthly_pi, 2),
            "Taxes": round(monthly_prop_taxes, 2),
            "Insurance": round(monthly_homeowners, 2),
            "PMI": round(pmi_monthly, 2),
            "Total Monthly": round(total_monthly, 2),
            "Cash to Close": round(final_cash_to_close, 2)
        }

df_scenarios = pd.DataFrame(scenario_data).rename_axis("Category").reset_index()

st.subheader("Scenario Comparison Table (Excel-Style)")
styled_df = df_scenarios.style.format(precision=2).set_properties(**{
    'text-align': 'center'
}).set_table_styles([{
    'selector': 'th',
    'props': [('text-align', 'center'), ('font-weight', 'bold')]
}])

st.dataframe(styled_df, use_container_width=True)

# --- DETAILED COSTS FOR FIRST SCENARIO ---
dp_first = down_payments[0]
dp_amount_first = purchase_price * (dp_first / 100)
loan_amt_first = purchase_price - dp_amount_first
upfront_first = upfront_fee(loan_amt_first, loan_program)
max_concession_allowed = purchase_price * max_seller_concession(dp_first, loan_program)
allowed_seller_credit_first = min(seller_concession, max_concession_allowed)
cash_to_close_first = dp_amount_first + sum(fixed_costs.values()) + condo_questionnaire_fee + sum(prepaids_escrows.values()) + upfront_first - allowed_seller_credit_first - rate_credit_pairs[0][1]

costs_table = {
    "Description": [],
    "Amount ($)": []
}

costs_table["Description"].append("Down Payment")
costs_table["Amount ($)"].append(round(dp_amount_first, 2))
for desc, amount in fixed_costs.items():
    costs_table["Description"].append(desc)
    costs_table["Amount ($)"].append(amount)
if condo_questionnaire_fee:
    costs_table["Description"].append("Condo Questionnaire Fee")
    costs_table["Amount ($)"].append(condo_questionnaire_fee)
for desc, amount in prepaids_escrows.items():
    costs_table["Description"].append(desc)
    costs_table["Amount ($)"].append(amount)
if upfront_first > 0:
    insurance_label = {
        "FHA": "FHA UFMIP",
        "VA": "VA Funding Fee",
        "USDA": "USDA Guarantee Fee"
    }.get(loan_program, "Upfront Insurance")
    costs_table["Description"].append(insurance_label)
    costs_table["Amount ($)"].append(round(upfront_first, 2))
if allowed_seller_credit_first > 0:
    costs_table["Description"].append("Seller Concession")
    costs_table["Amount ($)"].append(-round(allowed_seller_credit_first, 2))
if rate_credit_pairs[0][1] > 0:
    costs_table["Description"].append("Lender Credit")
    costs_table["Amount ($)"].append(-round(rate_credit_pairs[0][1], 2))
costs_table["Description"].append("TOTAL CASH TO CLOSE")
costs_table["Amount ($)"].append(round(cash_to_close_first, 2))

df_costs = pd.DataFrame(costs_table)
st.subheader("Detailed Costs Breakdown (First Scenario)")
st.table(df_costs)
