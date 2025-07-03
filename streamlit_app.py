import streamlit as st
import datetime
import pandas as pd

st.title("🏡 Comprehensive Loan Calculator with Full Closing Costs Table")

# Borrower Info
borrower_name = st.text_input("Borrower Name")
credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=740)

# Loan Program
program = st.selectbox("Loan Program", ["Conventional", "FHA", "VA", "USDA"])

# Property Info
purchase_price = st.number_input("Home Purchase Price ($)", min_value=10000.0, step=1000.0)
close_date = st.date_input("Estimated Close Date", value=datetime.date.today())

property_type = st.selectbox("Property Type", ["Detached", "Attached", "Manufactured", "Condo"])
is_condo_fee = 300 if property_type == "Condo" else 0

escrow_waived = st.checkbox("Escrows Waived?")
monthly_taxes = st.number_input("Estimated Monthly Taxes ($)", min_value=0.0, step=10.0)
monthly_insurance = st.number_input("Estimated Monthly Homeowners Insurance ($)", min_value=0.0, step=10.0)

# Rates & Down Payments
num_rates = st.number_input("How many interest rate options?", min_value=1, step=1, value=1)
rates, credits = [], []
for i in range(num_rates):
    rate = st.number_input(f"Interest Rate Option {i+1} (%)", min_value=0.0, step=0.01)
    lender_credit = st.number_input(f"Lender Credit for Rate Option {i+1} ($)", step=100.0)
    rates.append(rate)
    credits.append(lender_credit)

num_downs = st.number_input("How many down payment options?", min_value=1, step=1, value=1)
downs = []
min_down = 3.5 if program == "FHA" else (0 if program in ["VA", "USDA"] else 3)
for i in range(num_downs):
    down = st.number_input(f"Down Payment Option {i+1} (%) (min {min_down}%)", min_value=min_down, step=0.1)
    downs.append(down)

# Closing Costs
fixed_closing_costs = {
    "Credit Report": 120,
    "Underwriter Fee": 1250,
    "Flood/Tax Cert": 76,
    "Appraisal Fee": 625,
    "Lenders Title Insurance": 985.20,
    "Closing Attorney": 925,
    "Recording Fee": 351.86,
}
if is_condo_fee:
    fixed_closing_costs["Condo Questionnaire Fee"] = is_condo_fee

# Prepaids
last_day = datetime.date(close_date.year, close_date.month, 28) + datetime.timedelta(days=4)
last_day -= datetime.timedelta(days=last_day.day)
interim_days = (last_day - close_date).days + 1

results = []

for down in downs:
    down_amt = purchase_price * (down / 100)
    base_loan = purchase_price - down_amt
    ltv = base_loan / purchase_price * 100

    for idx, rate in enumerate(rates):
        loan_amt = base_loan
        monthly_mi, uf_fee = 0, 0

        # PMI/MIP/Funding Fee calculations
        if program == "FHA":
            uf_fee = base_loan * 0.0175
            loan_amt += uf_fee
            annual_mip = 0.0055 if ltv >= 90 else 0.0050
            monthly_mi = (loan_amt * annual_mip) / 12
        elif program == "VA":
            uf_fee = base_loan * 0.0215
            loan_amt += uf_fee
        elif program == "USDA":
            uf_fee = base_loan * 0.01
            loan_amt += uf_fee
            monthly_mi = (loan_amt * 0.0035) / 12
        elif program == "Conventional" and ltv > 80:
            pmi_factor = 0.0062 * (0.85 if credit_score >= 740 else 1)
            monthly_mi = (loan_amt * pmi_factor) / 12

        # Monthly Payment
        n, r = 30 * 12, rate / 100 / 12
        pi = loan_amt * (r * (1 + r)**n) / ((1 + r)**n - 1)
        monthly_escrow = 0 if escrow_waived else (monthly_taxes + monthly_insurance)
        total_payment = pi + monthly_mi + monthly_escrow

        # Prepaids
        interim_int = ((loan_amt * rate / 100) / 12 / 30) * interim_days
        homeowners_prem = monthly_insurance * 12
        prop_tax_res = monthly_taxes * 6
        prepaids = interim_int + homeowners_prem + prop_tax_res

        cash_close = down_amt + sum(fixed_closing_costs.values()) + prepaids - credits[idx]

        results.append({
            "Option": f"Down {down:.1f}% @ {rate:.3f}%",
            "Down Payment": down_amt,
            "Loan Amount": loan_amt,
            "Monthly P&I": pi,
            "Monthly MI/MIP/USDA": monthly_mi,
            "Monthly Taxes": monthly_taxes if not escrow_waived else 0,
            "Monthly Insurance": monthly_insurance if not escrow_waived else 0,
            "Total Monthly Payment": total_payment,
            "Lender Credit": credits[idx],
            "Interim Interest": interim_int,
            "Homeowners Insurance (12mo)": homeowners_prem,
            "Property Tax Reserve (6mo)": prop_tax_res,
            **fixed_closing_costs,
            "Total Closing Costs": sum(fixed_closing_costs.values()),
            "Total Prepaids": prepaids,
            "Cash to Close": cash_close,
        })

if st.button("Show Results"):
    df = pd.DataFrame(results).set_index("Option").T
    for col in df.columns:
        for row in df.index:
            val = df.at[row, col]
            if isinstance(val, (float, int)):
                if "Monthly" in row or "Loan Amount" in row or "Cash" in row or "Credit" in row or "Fee" in row or "Prepaids" in row or "Closing" in row or "Down" in row:
                    df.at[row, col] = f"${val:,.2f}"
    st.dataframe(df)
