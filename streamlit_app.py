import streamlit as st
import pandas as pd
import datetime

st.title("Comprehensive Loan Program-Specific Loan Cost & Payment Calculator")

# --- LOAN PURPOSE ---
loan_purpose = st.selectbox(
    "What is the loan purpose?",
    ["Purchase", "Rate/Term Refinance", "Cash-Out Refinance"]
)

# --- LOAN PROGRAM (single choice, applies guidelines) ---
loan_program = st.selectbox(
    "Choose Loan Program",
    ["Conventional", "FHA", "VA", "USDA"]
)

# --- FIRST-TIME HOMEBUYER STATUS (for Conventional only) ---
first_time_homebuyer = False
if loan_program == "Conventional":
    first_time_homebuyer = st.checkbox("Is the borrower a first-time homebuyer?", value=False)

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
waive_escrows = st.checkbox("Waive Escrows? (If checked, taxes & insurance not included in monthly payment or cash to close)")

# --- CONDO QUESTIONNAIRE FEE ---
condo_questionnaire_fee = 0.0
if st.checkbox("Is this property a condo? If yes, add $300 Condo Questionnaire Fee"):
    condo_questionnaire_fee = 300.0

# --- SELLER CONCESSION (only for purchases) ---
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
    "How many different down payment options do you want to model?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)

# --- DOWN PAYMENT SCENARIOS (REQUIRED) ---
st.markdown("## Enter Down Payment Percentages")
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

# --- NUM OF RATE SCENARIOS ---
num_rates = st.number_input(
    "How many different interest rate scenarios do you want to model?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)

# --- RATE & LENDER CREDIT SCENARIOS (REQUIRED) ---
st.markdown("## Enter Rate & Lender Credit/Cost Options")
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
        f"Lender Credit/Cost for Rate #{i+1} ($ – positive=credit; negative=points paid)",
        min_value=-50000.0,
        max_value=50000.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        key=f"credit_{i}"
    )
    rate_credit_pairs.append((rate, credit))
if st.button("Submit"):
    # --- FIXED COSTS FULL LIST ---
    fixed_costs = {
        "Origination Fee": 1400.0,
        "Processing Fee": 995.0,
        "Underwriting Fee": 795.0,
        "Credit Report Fee": 50.0,
        "Flood Certificate Fee": 15.0,
        "Tax Service Fee": 75.0,
        "Appraisal Fee": 550.0,
        "Title Search Fee": 300.0,
        "Attorney Fee": 500.0,
        "Recording Fee": 125.0,
        "Courier Fee": 40.0
    }
    
    today = datetime.date.today()
    months_until_year_end = max(0, 12 - today.month)
    estimated_annual_taxes = 3600.0
    monthly_tax = estimated_annual_taxes / 12
    escrowed_taxes = monthly_tax * months_until_year_end

    # --- PREPAIDS & ESCROWS ---
    prepaids_escrows = {}
    if not waive_escrows:
        prepaids_escrows["Homeowners Insurance (12 mo)"] = 1200.0
        prepaids_escrows[f"Property Taxes (thru Dec 31)"] = round(escrowed_taxes, 2)
    prepaids_escrows["Interim Interest"] = 500.0

    monthly_homeowners = 0.0 if waive_escrows else 1200.0 / 12
    monthly_prop_taxes = 0.0 if waive_escrows else monthly_tax

    # --- UPFRONT FEES (Funding fees/UFMIP/Guarantee) ---
    def upfront_fee(loan_amt):
        if loan_program == "FHA": return loan_amt * 0.0175
        if loan_program == "VA": return loan_amt * 0.0215
        if loan_program == "USDA": return loan_amt * 0.01
        return 0.0

    # --- MONTHLY PMI/MIP CALC ---
    def monthly_mi(loan_amt, ltv):
        if loan_program == "Conventional" and ltv > 80:
            return (loan_amt * 0.0055) / 12
        if loan_program == "FHA": return (loan_amt * 0.0085) / 12
        return 0.0

    # --- MAX SELLER CONCESSION ENFORCEMENT ---
    def max_seller_concession(dp):
        if loan_program == "Conventional":
            return 0.03 if dp < 10 else 0.06 if dp <= 25 else 0.09
        if loan_program == "FHA": return 0.06
        if loan_program == "VA": return 0.04
        if loan_program == "USDA": return 0.06
        return 0.0

    scenario_data = {}
    for dp in down_payments:
        # --- Enforce program-specific minimum down payments ---
        min_dp = 3.0 if first_time_homebuyer else 5.0 if loan_program == "Conventional" else 3.5 if loan_program == "FHA" else 0.0
        if dp < min_dp:
            scenario_data[f"{dp:.0f}%"] = {"Error": f"Below min {min_dp:.1f}% for {loan_program}"}
            continue

        dp_amount = purchase_price * (dp / 100)
        loan_amt_base = purchase_price - dp_amount
        upfront = upfront_fee(loan_amt_base)
        loan_amt = loan_amt_base + upfront

        allowed_seller_credit = min(seller_concession, purchase_price * max_seller_concession(dp))
        total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
        total_prepaids = sum(prepaids_escrows.values())
        cash_to_close_base = dp_amount + total_fixed + total_prepaids + upfront - allowed_seller_credit

        for rate, lender_credit in rate_credit_pairs:
            monthly_rate = rate / 100 / 12
            n_payments = 360
            monthly_pi = loan_amt * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1) if monthly_rate > 0 else loan_amt / n_payments
            ltv = 100 - dp
            mi_monthly = monthly_mi(loan_amt_base, ltv)
            total_monthly = monthly_pi + monthly_homeowners + monthly_prop_taxes + mi_monthly
            final_cash_to_close = cash_to_close_base - lender_credit

            label = f"{dp:.0f}% @ {rate:.2f}%"
            scenario_data[label] = {
                "Down Payment": round(dp_amount, 2),
                "Loan Amount": round(loan_amt, 2),
                "P&I": round(monthly_pi, 2),
                "Taxes": round(monthly_prop_taxes, 2),
                "Insurance": round(monthly_homeowners, 2),
                "PMI/MIP": round(mi_monthly, 2),
                "Total Monthly Payment": round(total_monthly, 2),
                "Cash to Close": round(final_cash_to_close, 2),
                "Seller Credit Applied": round(allowed_seller_credit, 2),
                "Lender Credit/Cost": round(lender_credit, 2),
                "Upfront Fees (Funding/UFMIP/etc.)": round(upfront, 2)
            }

    # --- SCENARIO COMPARISON TABLE ---
    df = pd.DataFrame(scenario_data).rename_axis("Category").reset_index()
    st.subheader(f"{loan_program} Detailed Loan Scenario Comparison")
    st.dataframe(df.style.format(precision=2), use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(f"Download {loan_program} CSV", csv, f"{loan_program}_scenarios.csv", "text/csv")

    # --- FIXED COSTS BREAKDOWN TABLE ---
    st.subheader("Detailed Fixed Costs Breakdown")
    fixed_df = pd.DataFrame(list(fixed_costs.items()) + [["Condo Questionnaire Fee", condo_questionnaire_fee]], columns=["Description", "Amount ($)"])
    st.table(fixed_df)

    # --- PREPAIDS & ESCROWS TABLE ---
    st.subheader("Prepaids & Escrows Breakdown")
    prepaids_df = pd.DataFrame(list(prepaids_escrows.items()), columns=["Description", "Amount ($)"])
    st.table(prepaids_df)
