import streamlit as st
import datetime
import pandas as pd

st.title("🏡 Comprehensive Loan Calculator with Closing Costs and Comparison Table")

program = st.selectbox("Select loan program", ["Conventional", "FHA", "VA", "USDA"])
amount = st.number_input("Enter home purchase price", min_value=10000.0, value=300000.0, step=1000.0)

close_date = st.date_input("Estimated close date", datetime.date.today())
last_day = (close_date.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
interim_days = (last_day - close_date).days + 1

borrower_name = st.text_input("Borrower name")
credit_score = st.number_input("Borrower credit score", min_value=300, max_value=850, value=740, step=1)
escrow_waived = st.checkbox("Escrows waived? (Taxes/Insurance not included in monthly payment)")
taxes = st.number_input("Estimated monthly property taxes", min_value=0.0, value=300.0, step=10.0)
insurance = st.number_input("Estimated monthly homeowners insurance", min_value=0.0, value=100.0, step=5.0)

downs = []
if program == "FHA":
    num_downs = st.number_input("Number of down payment options (min 3.5%)", min_value=1, value=1, step=1)
    for i in range(num_downs):
        down = st.number_input(
            f"Down payment option {i+1} (%) (min 3.5%)",
            min_value=3.5, max_value=100.0, value=3.5, step=0.1
        )
        downs.append(down)
elif program == "VA" or program == "USDA":
    num_downs = st.number_input(f"Number of down payment options ({program} allows 0%+)", min_value=1, value=1, step=1)
    for i in range(num_downs):
        down = st.number_input(
            f"Down payment option {i+1} (%)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.1
        )
        downs.append(down)
else:  # Conventional
    first_time = st.checkbox("Is borrower first-time homebuyer?")
    min_down = 3.0 if first_time else 5.0
    num_downs = st.number_input("Number of down payment options", min_value=1, value=1, step=1)
    for i in range(num_downs):
        down = st.number_input(
            f"Down payment option {i+1} (%) (min {min_down:.1f}%)",
            min_value=min_down, max_value=100.0, value=min_down, step=0.1
        )
        downs.append(down)

num_rates = st.number_input("How many interest rate options?", min_value=1, value=1, step=1)
rates = []
credits = []

for i in range(num_rates):
    rate = st.number_input(f"Interest rate option {i+1} (%)", min_value=0.01, max_value=20.0, value=6.5, step=0.01)
    rates.append(rate)
    credit = st.number_input(f"Lender credit for rate option {i+1}", value=0.0, step=500.0)
    credits.append(credit)

if program == "VA":
    exempt_fee = st.checkbox("Is borrower exempt from VA funding fee?")
    first_use = st.checkbox("Is this first use of VA?")

if st.button("Calculate Loan Options"):
    results = []

    for down in downs:
        down_amt = amount * (down / 100.0)
        base_loan = amount - down_amt
        ltv = base_loan / amount * 100

        for idx, rate in enumerate(rates):
            loan_amt = base_loan
            monthly_mi, uf_fee = 0.0, 0.0

            if program == "FHA":
                uf_fee = base_loan * 0.0175
                loan_amt += uf_fee
                annual_mip = 0.0055 if ltv >= 90 else 0.0050
                monthly_mi = (loan_amt * annual_mip) / 12
            elif program == "VA" and not exempt_fee:
                uf_fee = base_loan * (0.0215 if first_use and down < 5 else 0.015 if first_use else 0.033)
                loan_amt += uf_fee
            elif program == "USDA":
                uf_fee = base_loan * 0.01
                loan_amt += uf_fee
                monthly_mi = (loan_amt * 0.0035) / 12
            elif program == "Conventional" and ltv > 80:
                pmi_factor = 0.0062
                if credit_score >= 740:
                    pmi_factor *= 0.85
                monthly_mi = (loan_amt * pmi_factor) / 12

            n, r_m = 30 * 12, rate / 100 / 12
            pi = loan_amt * (r_m * (1 + r_m) ** n) / ((1 + r_m) ** n - 1)
            monthly_escrow = 0 if escrow_waived else (taxes + insurance)
            total_payment = pi + monthly_mi + monthly_escrow

            interim_int = ((loan_amt * rate / 100) / 12 / 30) * interim_days
            homeowners_prem = insurance * 12
            prop_tax_res = taxes * 6
            prepaids = interim_int + homeowners_prem + prop_tax_res

            closing_costs = sum([120, 1250, 76, 625, 985.20, 925, 351.86])
            cash_close = down_amt + closing_costs + prepaids - credits[idx]

            results.append({
                "Down %": down,
                "Rate": rate,
                "Loan Amount": loan_amt,
                "Monthly P&I": pi,
                "Monthly MI/MIP/USDA": monthly_mi,
                "Taxes": taxes if not escrow_waived else 0.0,
                "Insurance": insurance if not escrow_waived else 0.0,
                "Total Payment": total_payment,
                "Lender Credit": credits[idx],
                "Cash to Close": cash_close,
            })

    df = pd.DataFrame(results)
    st.dataframe(df.style.format({
        "Down %": "{:.1f}%", "Rate": "{:.3f}%", "Loan Amount": "${:,.2f}",
        "Monthly P&I": "${:,.2f}", "Monthly MI/MIP/USDA": "${:,.2f}",
        "Taxes": "${:,.2f}", "Insurance": "${:,.2f}", "Total Payment": "${:,.2f}",
        "Lender Credit": "${:,.2f}", "Cash to Close": "${:,.2f}",
    }))

    filename = f"{borrower_name.replace(' ', '_')}_loan_options.xlsx"
    df.to_excel(filename, index=False)
    st.success(f"✅ Table exported as '{filename}'")


