import streamlit as st
import pandas as pd
import datetime

st.title("Full Loan Program-Aware Loan Cost & Payment Calculator")

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

# --- FIRST-TIME HOMEBUYER STATUS (for Conventional) ---
first_time_homebuyer = st.checkbox("First-time homebuyer?", value=False)

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
st.markdown("## Interest Rate and Lender Credit/Cost Scenarios")
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
        f"Lender Credit/Cost for Rate #{i+1} ($ — positive = credit, negative = points/cost)",
        min_value=-50000.0,
        max_value=50000.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        key=f"credit_{i}"
    )
    rate_credit_pairs.append((rate, credit))

if st.button("Submit"):
    fixed_costs = {
        "Origination Fee": 1400.0,
        "Processing Fee": 995.0,
        "Underwriting Fee": 795.0,
        "Credit Report Fee": 50.0,
        "Flood Certificate Fee": 15.0,
        "Tax Service Fee": 75.0,
        "Appraisal Fee": 550.0,
    }

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

    def upfront_fee(loan_amt, program, va_first_use=True):
        if program == "FHA":
            return loan_amt * 0.0175
        elif program == "VA":
            return loan_amt * (0.0215 if va_first_use else 0.033)
        elif program == "USDA":
            return loan_amt * 0.01
        else:
            return 0.0

    def monthly_pmi(loan_amt, ltv):
        if ltv > 80:
            return (loan_amt * 0.0055) / 12
        return 0.0

    def max_seller_concession(dp, program):
        if program == "Conventional":
            if dp < 10: return 0.03
            elif dp <= 25: return 0.06
            else: return 0.09
        elif program == "FHA": return 0.06
        elif program == "VA": return 0.04
        elif program == "USDA": return 0.06
        else: return 0.0

    programs = ["Conventional", "FHA", "VA", "USDA"]
    full_results = {}

    for program in programs:
        scenario_data = {}

        for dp in down_payments:
            # Determine minimum down payment
            if program == "Conventional":
                min_dp = 3.0 if first_time_homebuyer else 5.0
            elif program == "FHA": min_dp = 3.5
            elif program in ["VA","USDA"]: min_dp = 0.0
            else: min_dp = 0.0

            if dp < min_dp:
                scenario_data[f"{dp:.0f}%"] = {"Error": f"Below min {min_dp:.1f}% for {program}"}
                continue

            dp_amount = purchase_price * (dp / 100)
            loan_amt_base = purchase_price - dp_amount
            upfront = upfront_fee(loan_amt_base, program)
            loan_amt = loan_amt_base + upfront
            max_concession_allowed = purchase_price * max_seller_concession(dp, program)
            allowed_seller_credit = min(seller_concession, max_concession_allowed)
            total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
            total_prepaids = sum(prepaids_escrows.values())
            cash_to_close_base = dp_amount + total_fixed + total_prepaids + upfront - allowed_seller_credit

            for rate, lender_credit in rate_credit_pairs:
                monthly_rate = rate / 100 / 12
                n_payments = 360
                monthly_pi = loan_amt * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1) if monthly_rate > 0 else loan_amt / n_payments
                ltv = 100 - dp
                pmi_monthly = 0.0
                if program == "Conventional":
                    pmi_monthly = monthly_pmi(loan_amt_base, ltv)
                elif program == "FHA":
                    pmi_monthly = (loan_amt * 0.0085) / 12
                total_monthly = monthly_pi + monthly_homeowners + monthly_prop_taxes + pmi_monthly
                final_cash_to_close = cash_to_close_base - lender_credit

                label = f"{dp:.0f}% @ {rate:.2f}%"
                scenario_data[label] = {
                    "Loan Amount": round(loan_amt, 2),
                    "P&I": round(monthly_pi, 2),
                    "Taxes": round(monthly_prop_taxes, 2),
                    "Insurance": round(monthly_homeowners, 2),
                    "PMI/MIP": round(pmi_monthly, 2),
                    "Total Monthly": round(total_monthly, 2),
                    "Cash to Close": round(final_cash_to_close, 2)
                }

        df = pd.DataFrame(scenario_data).rename_axis("Category").reset_index()
        full_results[program] = df
        st.subheader(f"{program} Loan Scenario Comparison")
        st.dataframe(df.style.format(precision=2), use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(f"Download {program} CSV", csv, f"{program}_scenarios.csv", "text/csv")
