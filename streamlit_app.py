import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

print("🏡 Comprehensive Loan Calculator with Closing Costs and Comparison Table")

# Loan program selection
program = input("Enter loan program (Conventional, FHA, VA, USDA): ").strip().lower()
amount = float(input("Enter home purchase price: "))
close_date_str = input("Enter estimated close date (MM/DD/YYYY): ").strip()
close_date = datetime.datetime.strptime(close_date_str, "%m/%d/%Y")
last_day = datetime.datetime(close_date.year, close_date.month, 28) + datetime.timedelta(days=4)
last_day -= datetime.timedelta(days=last_day.day)
interim_days = (last_day - close_date).days + 1

borrower_name = input("Enter borrower name: ").strip()
credit_score = int(input("Enter borrower credit score: "))
escrow_waived = input("Are escrows waived? (yes/no): ").strip().lower() == "yes"
taxes = float(input("Estimated monthly property taxes: "))
insurance = float(input("Estimated monthly homeowners insurance: "))

# Down payment options
downs = []
if program == "fha":
    num_downs = int(input("How many down payment options? (min 3.5%): "))
    for i in range(num_downs):
        down = float(input(f"Down payment option {i+1} (%): "))
        if down < 3.5:
            print("❌ FHA requires at least 3.5% down.")
            continue
        downs.append(down)
elif program == "va":
    num_downs = int(input("How many down payment options? (VA allows 0%+): "))
    downs = [float(input(f"Down payment option {i+1} (%): ")) for i in range(num_downs)]
elif program == "usda":
    num_downs = int(input("How many down payment options? (USDA allows 0%+): "))
    downs = [float(input(f"Down payment option {i+1} (%): ")) for i in range(num_downs)]
else:  # Conventional
    first_time = input("Is the borrower a first-time homebuyer? (yes/no): ").strip().lower() == "yes"
    num_downs = int(input("How many down payment options? "))
    for i in range(num_downs):
        down = float(input(f"Down payment option {i+1} (%): "))
        min_down = 3 if first_time else 5
        if down < min_down:
            print(f"❌ Conventional requires at least {min_down}% down.")
            continue
        downs.append(down)

num_rates = int(input("How many interest rate options? "))
rates = [float(input(f"Interest rate option {i+1} (%): ")) for i in range(num_rates)]
credits = [float(input(f"Lender credit for rate option {i+1}: ")) for i in range(num_rates)]

if program == "va":
    exempt_fee = input("Is borrower exempt from VA funding fee? (yes/no): ").strip().lower() == "yes"
    first_use = input("Is this the borrower's first use of VA? (yes/no): ").strip().lower() == "yes"

results = []

for down in downs:
    down_amt = amount * (down / 100)
    base_loan = amount - down_amt
    ltv = base_loan / amount * 100

    for idx, rate in enumerate(rates):
        loan_amt = base_loan
        monthly_mi, uf_fee = 0, 0

        # PMI/MIP/Funding Fee
        if program == "fha":
            uf_fee = base_loan * 0.0175
            loan_amt += uf_fee
            annual_mip = 0.0055 if ltv >= 90 else 0.0050
            monthly_mi = (loan_amt * annual_mip) / 12
        elif program == "va" and not exempt_fee:
            uf_fee = base_loan * (0.0215 if first_use and down < 5 else 0.015 if first_use else 0.033)
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

        # Monthly P&I calculation
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

        cash_close = down_amt + sum(closing_costs.values()) + prepaids - credits[idx]

        results.append({
            "Down %": down,
            "Rate": rate,
            "Loan Amount": loan_amt,
            "Monthly P&I": pi,
            "Monthly MI/MIP/USDA": monthly_mi,
            "Taxes": taxes if not escrow_waived else 0,
            "Insurance": insurance if not escrow_waived else 0,
            "Total Payment": total_payment,
            "Lender Credit": credits[idx],
            "Cash to Close": cash_close,
        })

# Excel export
wb = Workbook()
ws = wb.active
ws.title = "Loan Comparison"
bold = Font(bold=True)
yellow = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
currency_fmt = '"$"#,##0.00'
percent_fmt = '0.000%'

labels = [
    "Down Payment %", "Rate", "Loan Amount", "Monthly P&I",
    "Monthly MI/MIP/USDA", "Taxes", "Insurance", "Total Payment",
    "Lender Credit", "Cash to Close"
]

for row, label in enumerate(labels, start=1):
    cell = ws.cell(row=row, column=1, value=label)
    cell.font = bold

for col_idx, option in enumerate(results, start=2):
    ws.cell(row=1, column=col_idx, value=f"Option {col_idx-1}").font = bold
    ws.cell(row=2, column=col_idx, value=option["Down %"]/100).number_format = percent_fmt
    ws.cell(row=3, column=col_idx, value=option["Rate"]/100).number_format = percent_fmt
    ws.cell(row=4, column=col_idx, value=option["Loan Amount"]).number_format = currency_fmt
    ws.cell(row=5, column=col_idx, value=option["Monthly P&I"]).number_format = currency_fmt
    ws.cell(row=6, column=col_idx, value=option["Monthly MI/MIP/USDA"]).number_format = currency_fmt
    ws.cell(row=7, column=col_idx, value=option["Taxes"]).number_format = currency_fmt
    ws.cell(row=8, column=col_idx, value=option["Insurance"]).number_format = currency_fmt
    ws.cell(row=9, column=col_idx, value=option["Total Payment"]).number_format = currency_fmt
    ws.cell(row=10, column=col_idx, value=option["Lender Credit"]).number_format = currency_fmt
    ws.cell(row=11, column=col_idx, value=option["Cash to Close"]).number_format = currency_fmt

for col in ws.columns:
    max_len = max(len(str(cell.value or "")) for cell in col)
    ws.column_dimensions[col[0].column_letter].width = max_len + 2

filename = f"{borrower_name.replace(' ', '_')}_loan_options.xlsx"
wb.save(filename)
print(f"\n✅ Table exported as '{filename}'")
