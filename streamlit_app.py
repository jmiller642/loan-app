import streamlit as st
import datetime

st.title("🏡 Loan Option Calculator (Conventional, FHA, VA, USDA)")

# Loan program
program = st.selectbox("Loan program", ["Conventional", "FHA", "VA", "USDA"]).lower()

# Purchase price & shared details
amount = st.number_input("Home purchase price", min_value=10000.0, step=1000.0, value=400000.0)

close_date = st.date_input("Estimated close date", value=datetime.date.today())
today = datetime.date.today()
if close_date < today:
    st.warning("Close date is in the past!")

borrower_name = st.text_input("Borrower name")
credit_score = st.number_input("Credit score", min_value=300, max_value=850, value=740)

escrow_waived = st.checkbox("Escrows waived? (taxes & insurance excluded from monthly payment)", key="escrows")
taxes = st.number_input("Estimated monthly property taxes", min_value=0.0, step=50.0, value=300.0, key="taxes")
insurance = st.number_input("Estimated monthly homeowners insurance", min_value=0.0, step=10.0, value=100.0, key="insurance")

# Down payments with unique keys
downs = []
first_time_flags = []
num_downs = st.number_input("Number of down payment options", min_value=1, max_value=5, value=2, step=1, key="num_downs")
for i in range(1, num_downs + 1):
    down = st.number_input(
        f"Down payment option {i} (%)",
        min_value=0.0, max_value=100.0, step=0.1, value=5.0,
        key=f"down_{i}"
    )

    if program == "fha" and down < 3.5:
        st.warning(f"❌ FHA requires ≥3.5% down on option {i}.")
    elif program == "conventional":
        first_time = st.checkbox(
            f"First-time homebuyer for option {i}?", key=f"fthb_{i}"
        )
        min_down = 3 if first_time else 5
        if down < min_down:
            st.warning(f"❌ Conventional requires ≥{min_down}% down on option {i}.")
        first_time_flags.append(first_time)
    downs.append(down)

# Rates & credits with unique keys
num_rates = st.number_input("Number of interest rate options", min_value=1, max_value=5, value=1, step=1, key="num_rates")
rates, credits = [], []
for i in range(1, num_rates + 1):
    rate = st.number_input(
        f"Interest rate option {i} (%)", min_value=0.01, step=0.01, value=6.5,
        key=f"rate_{i}"
    )
    credit = st.number_input(
        f"Lender credit for rate option {i}", value=0.0, step=100.0,
        key=f"credit_{i}"
    )
    rates.append(rate)
    credits.append(credit)

# VA-specific questions with unique keys
exempt_fee, first_use = False, True
if program == "va":
    exempt_fee = st.radio(
        "Is borrower exempt from VA funding fee?", ["No", "Yes"],
        key="va_exempt"
    ) == "Yes"
    first_use = st.radio(
        "Is this the borrower's first use of VA?", ["Yes", "No"],
        key="va_first_use"
    ) == "Yes"

if st.button("Calculate", key="calc"):
    st.success("Calculating loan options...")

    # Calculate interim interest days
    last_day = datetime.date(close_date.year, close_date.month, 28) + datetime.timedelta(days=4)
    last_day = last_day - datetime.timedelta(days=last_day.day)
    interim_days = (last_day - close_date).days + 1

    results = []
    for idx, down in enumerate(downs):
        down_amt = amount * (down / 100)
        base_loan = amount - down_amt
        ltv = base_loan / amount * 100

        for jdx, rate in enumerate(rates):
            loan_amt = base_loan
            monthly_mi, uf_fee = 0, 0

            if program == "fha":
                uf_fee = base_loan * 0.0175
                loan_amt += uf_fee
                annual_mip = 0.0055 if ltv >= 90 else 0.0050
                monthly_mi = (loan_amt * annual_mip) / 12
            elif program == "va" and not exempt_fee:
                if first_use:
                    uf_fee = base_loan * (0.0215 if down < 5 else 0.015 if down < 10 else 0.0125)
                else:
                    uf_fee = base_loan * (0.033 if down < 5 else 0.015 if down < 10 else 0.0125)
                loan_amt += uf_fee
            elif program == "usda":
                uf_fee = base_loan * 0.01
                loan_amt += uf_fee
                monthly_mi = (loan_amt * 0.0035) / 12
            elif program == "conventional" and ltv > 80:
                pmi_factor = 0.0062
                if credit_score >= 740:
                    pmi_factor *= 0.85
                monthly_mi = (loan_amt * pmi_factor) / 12

            n, r = 30 * 12, rate / 100 / 12
            pi = loan_amt * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
            monthly_escrow = 0 if escrow_waived else (taxes + insurance)
            total_payment = pi + monthly_mi + monthly_escrow

            interim_int = ((loan_amt * rate / 100) / 12 / 30) * interim_days
            homeowners_prem = insurance * 12
            prop_tax_res = taxes * 6
            prepaids = interim_int + homeowners_prem + prop_tax_res

            closing_costs = {
                "Credit Report": 120,
                "Underwriter Fee": 1250,
                "Flood/Tax Cert": 76,
                "Appraisal Fee": 625,
                "Lenders Title Insurance": 985.20,
                "Closing Attorney": 925,
                "Recording Fee": 351.86,
            }

            cash_close = down_amt + sum(closing_costs.values()) + prepaids - credits[jdx]

            results.append({
                "Option": f"Down {down:.1f}% @ {rate:.3f}%",
                "Loan Amount": loan_amt,
                "Monthly P&I": pi,
                "Monthly MI/MIP/USDA": monthly_mi,
                "Taxes": taxes if not escrow_waived else 0,
                "Insurance": insurance if not escrow_waived else 0,
                "Total Payment": total_payment,
                "Lender Credit": credits[jdx],
                "Cash to Close": cash_close,
            })

    st.write("### Loan Options")
    st.dataframe(results)
