import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Comprehensive Loan Officer Calculator", layout="wide")
st.title("Ultimate Loan Program-Specific Loan Cost & Payment Calculator")

st.markdown("""
Welcome to the **Ultimate Loan Officer Calculator**. This tool lets you:
- Select a loan purpose and program.
- Model multiple down payments, rates, lender credits.
- Automatically apply program-specific rules for down payments, PMI/MIP, seller concessions, etc.
- Calculate exact cash-to-close and monthly payments across scenarios.
- Generate a client-friendly summary and download CSV results.
""")

# --- LOAN PURPOSE ---
loan_purpose = st.selectbox(
    "What is the loan purpose?",
    ["Purchase", "Rate/Term Refinance", "Cash-Out Refinance"]
)

# --- LOAN PROGRAM ---
loan_program = st.selectbox(
    "Choose Loan Program",
    ["Conventional", "FHA", "VA", "USDA"]
)

# --- PROGRAM-SPECIFIC EXPLANATIONS ---
with st.expander(f"📘 {loan_program} Program Guidelines"):
    if loan_program == "Conventional":
        st.markdown("""
        - **Min Down Payment**: 3% (first-time buyer) or 5% (otherwise).
        - **PMI** required if LTV >80%.
        - **Seller Concession**: 3-9% depending on down payment.
        """)
    elif loan_program == "FHA":
        st.markdown("""
        - **Min Down Payment**: 3.5%.
        - **MIP**: 1.75% upfront + 0.85% annual.
        - **Seller Concession Limit**: 6%.
        """)
    elif loan_program == "VA":
        st.markdown("""
        - **Min Down Payment**: 0%.
        - **Funding Fee**: ~2.15%.
        - **Seller Concession Limit**: 4%.
        """)
    elif loan_program == "USDA":
        st.markdown("""
        - **Min Down Payment**: 0%.
        - **Guarantee Fee**: 1% upfront; 0.35% annual.
        - **Seller Concession Limit**: 6%.
        """)

# --- FIRST-TIME HOMEBUYER FLAG ---
first_time_homebuyer = loan_program == "Conventional" and st.checkbox(
    "First-time homebuyer? (Allows 3% min down)"
)

# --- PURCHASE PRICE OR LOAN AMOUNT ---
if loan_purpose == "Purchase":
    purchase_price = st.number_input("Purchase Price ($)", 10000.0, 1e7, 300000.0, 1000.0)
else:
    purchase_price = st.number_input("Loan Amount ($)", 10000.0, 1e7, 300000.0, 1000.0)
    st.markdown("For refinances, this calculator uses the loan amount directly.")

# --- CASH-OUT AMOUNT (CASH-OUT REFI) ---
cash_out_amount = 0.0
if loan_purpose == "Cash-Out Refinance":
    cash_out_amount = st.number_input("Desired Cash-Out Amount ($)", 0.0, 2e6, 0.0, 1000.0)
    with st.expander("📘 Cash-Out Explanation"):
        st.markdown("Cash-out reduces cash to close (net cash back to borrower).")

# --- WAIVE ESCROWS ---
waive_escrows = st.checkbox("Waive Escrows? (Taxes & insurance excluded from monthly payment and cash to close)")

# --- CONDO QUESTIONNAIRE ---
condo_questionnaire_fee = 0.0
if st.checkbox("Property is a condo? (Adds $300 Condo Questionnaire Fee)"):
    condo_questionnaire_fee = 300.0

# --- SELLER CONCESSION (PURCHASE ONLY) ---
seller_concession = 0.0
if loan_purpose == "Purchase":
    seller_concession = st.number_input("Seller Concession ($)", 0.0, purchase_price, 0.0, 500.0)
    with st.expander("📘 Seller Concession Explanation"):
        st.markdown("Seller concessions reduce cash to close but are limited per loan program.")

# --- DOWN PAYMENT SCENARIOS ---
num_dp = st.number_input("How many down payment scenarios?", 1, 5, 1, 1)
down_payments = [st.number_input(f"Down Payment #{i+1} (%)", 0.0, 100.0, 0.0, 0.1, key=f"dp_{i}") for i in range(num_dp)]

# --- RATE & LENDER CREDIT SCENARIOS ---
num_rates = st.number_input("How many interest rate scenarios?", 1, 5, 1, 1)
rate_credit_pairs = [
    (
        st.number_input(f"Rate #{i+1} (%)", 0.0, 20.0, 0.0, 0.01, key=f"rate_{i}"),
        st.number_input(f"Lender Credit/Cost #{i+1} ($)", -50000.0, 50000.0, 0.0, 500.0, key=f"credit_{i}")
    ) for i in range(num_rates)
]

if st.button("Submit"):
    # --- FIXED & PREPAIDS ---
    fixed_costs = {"Origination Fee":1495.0,"Processing Fee":995.0,"Underwriting Fee":1095.0,"Credit Report Fee":85.0,
        "Flood Certificate Fee":14.0,"Tax Service Fee":90.0,"Appraisal Fee":650.0,"Title – Closing/Escrow Fee":500.0,
        "Title – Lender’s Title Insurance":1200.0,"Title – Recording Fee":125.0,"Title – Courier Fee":75.0,
        "Title – Title Exam/Abstract":225.0,"Title – Settlement/Closing Fee":350.0}
    today=datetime.date.today()
    months_until_year_end=max(0,12-today.month)
    monthly_tax=3600.0/12
    escrowed_taxes=monthly_tax*months_until_year_end
    prepaids={"Interim Interest":500.0}
    if not waive_escrows:
        prepaids["Homeowners Insurance (12 mo)"]=1200.0
        prepaids["Property Taxes (thru Dec 31)"]=round(escrowed_taxes,2)
    monthly_homeowners=0.0 if waive_escrows else 100.0
    monthly_prop_taxes=0.0 if waive_escrows else monthly_tax

    def upfront_fee(amt): return amt*(0.0175 if loan_program=="FHA" else 0.0215 if loan_program=="VA" else 0.01 if loan_program=="USDA" else 0.0)
    def monthly_mi(amt,ltv): return (amt*0.0055/12 if loan_program=="Conventional" and ltv>80 else amt*0.0085/12 if loan_program=="FHA" else 0)
    def max_concession(dp): return 0.03 if loan_program=="Conventional" and dp<10 else 0.06 if loan_program in ["Conventional","FHA","USDA"] else 0.04 if loan_program=="VA" else 0

    scenario_data={}
    for dp in down_payments:
        min_dp=3.0 if first_time_homebuyer else 5.0 if loan_program=="Conventional" else 3.5 if loan_program=="FHA" else 0.0
        if dp<min_dp: scenario_data[f"{dp:.0f}%"]={"Error":f"Below min {min_dp:.1f}%"}; continue
        dp_amt=purchase_price*dp/100 if loan_purpose=="Purchase" else 0.0
        loan_base=purchase_price-dp_amt if loan_purpose=="Purchase" else purchase_price
        upfront=upfront_fee(loan_base); loan_amt=loan_base+upfront
        max_allowed=(purchase_price if loan_purpose=="Purchase" else loan_amt)*max_concession(dp)
        seller_credit_applied=min(seller_concession,max_allowed)
        total_fixed=sum(fixed_costs.values())+condo_questionnaire_fee; total_prepaids=sum(prepaids.values())
        cash_close=dp_amt+total_fixed+total_prepaids+upfront-seller_credit_applied
        for rate,credit in rate_credit_pairs:
            m_rate=rate/1200; n=360
            monthly_pi=loan_amt*((m_rate*(1+m_rate)**n)/((1+m_rate)**n-1)) if m_rate else loan_amt/n
            ltv=100-dp if loan_purpose=="Purchase" else 100
            mi=monthly_mi(loan_base,ltv)
            total_monthly=monthly_pi+monthly_homeowners+monthly_prop_taxes+mi
            final_cash=cash_close-credit; final_cash-=cash_out_amount if loan_purpose=="Cash-Out Refinance" else 0
            label=f"{dp:.0f}% @ {rate:.2f}%"
            scenario_data[label]={"Down Payment":dp_amt,"Loan Amount":loan_amt,"P&I":monthly_pi,"Taxes":monthly_prop_taxes,
                "Insurance":monthly_homeowners,"PMI/MIP":mi,"Total Monthly Payment":total_monthly,"Cash to Close":final_cash,
                "Seller Credit Applied":seller_credit_applied,"Lender Credit/Cost":credit,"Upfront Fees":upfront,"Condo Questionnaire Fee":condo_questionnaire_fee,
                "Fixed Costs":total_fixed,"Prepaids & Escrows":total_prepaids,"Cash-Out Requested":-cash_out_amount if loan_purpose=="Cash-Out Refinance" else 0}
    df=pd.DataFrame(scenario_data).rename_axis("Category").reset_index()
    st.subheader(f"{loan_program} Detailed Loan Scenario Comparison")
    st.dataframe(df.style.format(precision=2),use_container_width=True)
    st.download_button(f"Download {loan_program} CSV",df.to_csv(index=False).encode("utf-8"),f"{loan_program}_scenarios.csv","text/csv")
