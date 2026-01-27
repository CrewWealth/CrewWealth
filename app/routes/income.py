from flask import Blueprint, render_template, request

income_bp = Blueprint('income', __name__, url_prefix='/income')

@income_bp.route('/calculate-income', methods=['POST'])
def calculate_income():
    """Calculate income based on form submission"""
    monthly_salary = float(request.form.get('monthly_salary', 0))
    contract_months = int(request.form.get('contract_months', 1))
    position = request.form.get('position', 'Other')
    allowances = float(request.form.get('allowances', 0))
    bonus = float(request.form.get('bonus', 0))
    tax_rate = float(request.form.get('tax_rate', 19))
    
    # Calculations
    gross_monthly = monthly_salary + allowances
    gross_contract_income = (gross_monthly * contract_months) + bonus
    taxes = (gross_contract_income * tax_rate) / 100
    net_contract_income = gross_contract_income - taxes
    
    results = {
        'monthly_salary': monthly_salary,
        'monthly_allowances': allowances,
        'gross_monthly': gross_monthly,
        'contract_months': contract_months,
        'contract_bonus': bonus,
        'gross_contract_income': gross_contract_income,
        'taxes': taxes,
        'net_contract_income': net_contract_income,
        'position': position,
        'tax_rate': tax_rate
    }
    
    return render_template('income.html', results=results)

@income_bp.route('/', methods=['GET'])
def income_form():
    """Display income calculation form"""
    return render_template('income.html')
