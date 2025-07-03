import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Comprehensive Loan Officer Calculator", layout="wide")
st.title("Ultimate Loan Program-Specific Loan Cost & Payment Calculator")

st.markdown("""
Welcome to the **Ultimate Loan Officer Calculator**. This tool lets you:
- Select a loan purpose and program.
- Dynamically adjust down payments, interest rates, and lender credits.
- See detailed explanations specific to the loan program you pick.
- Calculate exact cash-to-close and monthly payments across multiple scenarios.
- Download your results for records or client presentation.
""")

# --- LOAN PURPOSE ---
loan_purpose = st.selectbox(
    "What is the loan purpose?",
    ["Purchase", "Rate/Term Refinance", "Cash-Out Refinance"]
)

# --- LOAN PROGRAM (single selection; dictates all logic) ---
loan_program = st.selectbox(
    "Choose Loan Program",
    ["Conventional", "FHA", "VA", "USDA"]
)

# --- PROGRAM-SPECIFIC EXPLANATIONS ---
with st.expander(f"📘 {loan_program} Program Guidelines"):
    if loan_program == "Conventional":
        st.markdown("""
        - **Minimum Down Payment**:
            - 3% if first-time homebuyer.
            - 5% otherwise.
        - **PMI**: Required if LTV > 80%.
        - **Seller Concession Limits**:
            - 3% if DP <10%, 6% if 10–25%, 9% if >25%.
        - No upfront mortgage insurance premium.
        """)
    elif loan_program == "FHA":
        st.markdown("""
        - **Minimum Down Payment**: 3.5%.
        - **MIP**: Upfront premium of 1.75% of base loan amount + monthly MIP ~0.85%.
        - **Seller Concession Limit**: 6%.
        """)
    elif loan_program == "VA":
        st.markdown("""
        - **Minimum Down Payment**: 0%.
        - **Funding Fee**: Typically 2.15% first use; higher on subsequent uses or cash-out.
        - **Seller Concession Limit**: 4%.
        """)
    elif loan_program == "USDA":
        st.markdown("""
        - **Minimum Down Payment**: 0%.
        - **Guarantee Fee**: 1% upfront; annual premium ~0.35%.
        - **Seller Concession Limit**: 6%.
        - **Eligibility**: Property must be in USDA-eligible rural area; borrower income limits apply.
        """)

# --- FIRST-TIME HOMEBUYER STATUS (Conventional only) ---
first_time_homebuyer = False
if loan_program == "Conventional":
    first_time_homebuyer = st.checkbox("Is the borrower a first-time homebuyer? (Enables 3% down)")

# --- PURCHASE PRICE or LOAN AMOUNT ---
if loan_purpose == "Purchase":
    purchase_price = st.number_input(
        "Enter Purchase Price ($)",
        min_value=10000.0,
        max_value=10000000.0,
        value=300000.0,
        step=1000.0,
        format="%.2f"
    )
else:
    purchase_price = st.number_input(
        "Enter Loan Amount ($)",
        min_value=10000.0,
        max_value=10000000.0,
        value=300000.0,
        step=1000.0,
        format="%.2f"
    )
    with st.expander("📘 Loan Amount Explanation"):
        st.markdown("""
        For refinances, this calculator uses the loan amount in place of purchase price, since there is no property sale.
        """)

# --- CASH-OUT AMOUNT (Cash-Out Refinance only) ---
cash_out_amount = 0.0
if loan_purpose == "Cash-Out Refinance":
    st.markdown("## Cash-Out Refinance Details")
    cash_out_amount = st.number_input(
        "Desired Cash-Out Amount ($)",
        min_value=0.0,
        max_value=2000000.0,
        value=0.0,
        step=1000.0,
        format="%.2f"
    )
    with st.expander("📘 Cash-Out Explanation"):
        st.markdown("""
        Cash-out amount will be added to the loan amount, but will reduce cash-to-close (shown as negative cash to close).
        """)

# --- WAIVE ESCROWS ---
waive_escrows = st.checkbox("Waive Escrows? (If checked, taxes & insurance not included in monthly payment or cash to close)")

# --- CONDO QUESTIONNAIRE FEE ---
condo_questionnaire_fee = 0.0
if st.checkbox("Is the property a condo? (Adds $300 Condo Questionnaire Fee)"):
    condo_questionnaire_fee = 300.0

# --- SELLER CONCESSION INPUT (only for purchases) ---
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
    with st.expander("📘 Seller Concessions Explanation"):
        st.markdown("""
        Seller concessions reduce the borrower’s cash to close, but cannot exceed the program’s max allowed percentage.
        Excess seller credits beyond allowed limits will not reduce cash to close.
        """)

# --- DOWN PAYMENT SCENARIOS ---
st.markdown("## Down Payment Scenarios")
num_dp = st.number_input(
    "How many down payment options would you like to model?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)
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

# --- INTEREST RATE & LENDER CREDIT SCENARIOS ---
st.markdown("## Interest Rate and Lender Credit/Cost Scenarios")
num_rates = st.number_input(
    "How many interest rate scenarios do you want to model?",
    min_value=1,
    max_value=5,
    value=1,
    step=1
)
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
        f"Lender Credit/Cost for Rate #{i+1} ($ — positive = credit to borrower, negative = points paid)",
        min_value=-50000.0,
        max_value=50000.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        key=f"credit_{i}"
    )
    rate_credit_pairs.append((rate, credit))
if st.button("Submit"):
    st.markdown("## 🔎 Calculation Details")

    # --- FIXED COSTS (your detailed list) ---
    fixed_costs = {
        "Origination Fee": 1495.0,
        "Processing Fee": 995.0,
        "Underwriting Fee": 1095.0,
        "Credit Report Fee": 85.0,
        "Flood Certificate Fee": 14.0,
        "Tax Service Fee": 90.0,
        "Appraisal Fee": 650.0,
        "Title – Closing/Escrow Fee": 500.0,
        "Title – Lender’s Title Insurance": 1200.0,
        "Title – Recording Fee": 125.0,
        "Title – Courier Fee": 75.0,
        "Title – Title Exam/Abstract": 225.0,
        "Title – Settlement/Closing Fee": 350.0
    }

    with st.expander("📘 Fixed Costs Explanation"):
        st.markdown("""
        Fixed costs include lender fees, credit reports, appraisal, and standard title/settlement fees.
        These costs are typically unavoidable and vary by lender, title company, and local regulations.
        This calculator uses your detailed list of fees as you provided earlier.
        """)

    # --- PREPAIDS & ESCROWS ---
    today = datetime.date.today()
    months_until_year_end = max(0, 12 - today.month)
    estimated_annual_taxes = 3600.0
    monthly_tax = estimated_annual_taxes / 12
    escrowed_taxes = monthly_tax * months_until_year_end

    prepaids_escrows = {}
    if not waive_escrows:
        prepaids_escrows["Homeowners Insurance (12 mo)"] = 1200.0
        prepaids_escrows[f"Property Taxes (thru Dec 31)"] = round(escrowed_taxes, 2)
    prepaids_escrows["Interim Interest"] = 500.0

    with st.expander("📘 Prepaids & Escrows Explanation"):
        st.markdown("""
        Prepaids include homeowners insurance and property taxes paid upfront into escrow accounts.
        Interim interest is the daily interest from closing date to first payment.
        If escrows are waived, insurance and tax reserves are excluded.
        """)

    monthly_homeowners = 0.0 if waive_escrows else 1200.0 / 12
    monthly_prop_taxes = 0.0 if waive_escrows else monthly_tax

    # --- UPFRONT FEES: FHA UFMIP, VA Funding Fee, USDA Guarantee Fee ---
    def upfront_fee(loan_amt):
        if loan_program == "FHA":
            return loan_amt * 0.0175
        elif loan_program == "VA":
            return loan_amt * 0.0215
        elif loan_program == "USDA":
            return loan_amt * 0.01
        else:
            return 0.0

    with st.expander("📘 Upfront Fees Explanation"):
        st.markdown("""
        Depending on the loan program:
        - **FHA**: Upfront Mortgage Insurance Premium (UFMIP) = 1.75%.
        - **VA**: Funding Fee = ~2.15% first-time use.
        - **USDA**: Guarantee Fee = 1%.
        - **Conventional**: No upfront fees.
        These are financed into the loan balance and increase the total loan amount.
        """)

    # --- PMI/MIP CALCULATION ---
    def monthly_mi(loan_amt, ltv):
        if loan_program == "Conventional" and ltv > 80:
            return (loan_amt * 0.0055) / 12
        if loan_program == "FHA":
            return (loan_amt * 0.0085) / 12
        return 0.0

    with st.expander("📘 PMI/MIP Explanation"):
        st.markdown("""
        PMI or MIP is required on loans with <20% down (Conventional) or on all FHA loans:
        - **PMI (Private Mortgage Insurance)** applies to Conventional >80% LTV, ~0.55% annual rate.
        - **MIP (Mortgage Insurance Premium)** applies to all FHA loans, ~0.85% annual rate.
        VA and USDA have no monthly mortgage insurance but instead charge upfront fees.
        """)

    # --- SELLER CONCESSION LIMITS ---
    def max_seller_concession(dp):
        if loan_program == "Conventional":
            return 0.03 if dp < 10 else 0.06 if dp <= 25 else 0.09
        if loan_program == "FHA": return 0.06
        if loan_program == "VA": return 0.04
        if loan_program == "USDA": return 0.06
        return 0.0

    with st.expander("📘 Seller Concessions Explanation"):
        st.markdown("""
        Seller concessions reduce cash-to-close but have program-specific max limits:
        - **Conventional**: 3% (<10% DP), 6% (10–25% DP), 9% (>25% DP).
        - **FHA**: 6%.
        - **VA**: 4%.
        - **USDA**: 6%.
        Exceeding these limits won’t reduce cash to close further.
        """)

    scenario_data = {}  # Holds results across down payments and rates

    for dp in down_payments:
        # --- Determine required minimum DP for program ---
        min_dp = 3.0 if first_time_homebuyer else 5.0 if loan_program == "Conventional" else 3.5 if loan_program == "FHA" else 0.0
        if dp < min_dp:
            scenario_data[f"{dp:.0f}%"] = {"Error": f"Below minimum {min_dp:.1f}% for {loan_program}"}
            continue

        dp_amount = purchase_price * (dp / 100) if loan_purpose == "Purchase" else 0.0
        loan_amt_base = purchase_price - dp_amount if loan_purpose == "Purchase" else purchase_price
        upfront = upfront_fee(loan_amt_base)
        loan_amt = loan_amt_base + upfront

        max_concession_allowed = (purchase_price if loan_purpose == "Purchase" else loan_amt_base) * max_seller_concession(dp)
        allowed_seller_credit = min(seller_concession, max_concession_allowed)

        total_fixed = sum(fixed_costs.values()) + condo_questionnaire_fee
        total_prepaids = sum(prepaids_escrows.values())

        cash_to_close_base = dp_amount + total_fixed + total_prepaids + upfront - allowed_seller_credit
        for rate, lender_credit in rate_credit_pairs:
            # --- Calculate monthly principal & interest payment ---
            monthly_rate = rate / 100 / 12
            n_payments = 360  # 30-year term fixed

            monthly_pi = (
                loan_amt * (monthly_rate * (1 + monthly_rate) ** n_payments) /
                ((1 + monthly_rate) ** n_payments - 1)
            ) if monthly_rate > 0 else loan_amt / n_payments

            ltv = (loan_amt_base / purchase_price) * 100 if loan_purpose == "Purchase" else (loan_amt_base / loan_amt_base) * 100
            mi_monthly = monthly_mi(loan_amt_base, ltv)

            total_monthly = monthly_pi + monthly_homeowners + monthly_prop_taxes + mi_monthly

            final_cash_to_close = cash_to_close_base - lender_credit

            if loan_purpose == "Cash-Out Refinance" and cash_out_amount > 0:
                final_cash_to_close -= cash_out_amount  # Net cash to borrower

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
                "Upfront Fees": round(upfront, 2),
                "Condo Questionnaire Fee": condo_questionnaire_fee,
                "Fixed Costs": round(total_fixed, 2),
                "Prepaids & Escrows": round(total_prepaids, 2),
                "Cash-Out Requested": -round(cash_out_amount, 2) if loan_purpose == "Cash-Out Refinance" else 0.0
            }

    # --- Scenario Table Output ---
    df = pd.DataFrame(scenario_data).rename_axis("Category").reset_index()
    st.subheader(f"{loan_program} Detailed Loan Scenario Comparison")
    styled_df = df.style.format(precision=2).background_gradient(cmap="Blues", subset=df.columns[1:])
    st.dataframe(styled_df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(f"Download {loan_program} Scenarios CSV", csv, f"{loan_program}_scenarios.csv", "text/csv")

    # --- Fixed Costs Table Output ---
    st.subheader("Detailed Fixed Costs Breakdown")
    fixed_df = pd.DataFrame(
        list(fixed_costs.items()) + [["Condo Questionnaire Fee", condo_questionnaire_fee]],
        columns=["Description", "Amount ($)"]
    )
    styled_fixed_df = fixed_df.style.background_gradient(cmap="Greens", subset=["Amount ($)"])
    st.table(styled_fixed_df)

    # --- Prepaids & Escrows Table Output ---
    st.subheader("Detailed Prepaids & Escrows Breakdown")
    prepaids_df = pd.DataFrame(list(prepaids_escrows.items()), columns=["Description", "Amount ($)"])
    styled_prepaids_df = prepaids_df.style.background_gradient(cmap="Oranges", subset=["Amount ($)"])
    st.table(styled_prepaids_df)

    # --- Explanation of Cash to Close Calculation ---
    with st.expander("📘 Cash to Close Explanation"):
        st.markdown("""
        Cash to close includes:
        - Down payment (if purchase).
        - Fixed lender/title fees.
        - Prepaid items & escrows.
        - Upfront insurance or funding fees.
        - Less seller concessions (up to program limit).
        - Adjusted by lender credits (positive reduces cash to close; negative increases it).
        - If a cash-out refi, cash-out amount reduces cash to close (shows negative net).
        """)
    # --- Client-Friendly Summary Toggle ---
    if st.checkbox("Generate Client-Friendly Summary"):
        st.markdown("## 📝 Client Summary")
        st.markdown(f"""
        **Loan Program:** {loan_program}  
        **Loan Purpose:** {loan_purpose}  
        **Purchase Price / Loan Amount:** ${purchase_price:,.2f}  
        **Escrows Waived:** {"Yes" if waive_escrows else "No"}  
        **Condo Fee Applied:** {"Yes ($300)" if condo_questionnaire_fee > 0 else "No"}  
        **Seller Concession Requested:** ${seller_concession:,.2f}  
        **Cash-Out Amount:** ${cash_out_amount:,.2f}  
        """)

        st.markdown("### Top Scenario Breakdown")
        top_label = list(scenario_data.keys())[0]
        top_scenario = scenario_data[top_label]
        st.markdown(f"""
        **Scenario:** {top_label}  
        - Down Payment: ${top_scenario['Down Payment']:,.2f}  
        - Loan Amount: ${top_scenario['Loan Amount']:,.2f}  
        - Monthly Payment: ${top_scenario['Total Monthly Payment']:,.2f}  
        - Estimated Cash to Close: ${top_scenario['Cash to Close']:,.2f}  
        """)

        with st.expander("📘 Disclaimer & Next Steps"):
            st.markdown("""
            These figures are estimates based on the information provided. Final terms, costs, and payments are subject to underwriting, appraisal, and lender approval. Rates may change without notice. Contact your loan officer for an updated Loan Estimate.
            """)

    # --- Footer: Thank You Note ---
    st.markdown("---")
    st.markdown("""
    ✅ **Calculation Complete**  
    Thank you for using the Ultimate Loan Officer Calculator.
    Use the download buttons above to save your results, or click the boxes to generate a client-friendly summary.
    """)
