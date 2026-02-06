from flask import Flask, Blueprint, render_template, request
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# Income Blueprint
income_bp = Blueprint('income', __name__, url_prefix='/income')

def validate_float(value, field_name):
    """Validate and convert input to float"""
    try:
        return max(0, float(value))  # Zorg dat het niet-negatief is
    except ValueError:
        raise BadRequest(f"Invalid value for {field_name}. Must be a positive number.")

def validate_int(value, field_name):
    """Validate and convert input to int"""
    try:
        return max(0, int(value))  # Zorg dat het niet-negatief is
    except ValueError:
        raise BadRequest(f"Invalid value for {field_name}. Must be a positive integer.")

@income_bp.route('/calculate-income', methods=['POST'])
def calculate_income():
    """Calculate income based on form submission"""
    try:
        # Validated input values
        monthly_salary = validate_float(request.form.get('monthly_salary', 0), 'Monthly Salary')
        contract_months = validate_int(request.form.get('contract_months', 1), 'Contract Months')
        position = request.form.get('position', 'Other')
        allowances = validate_float(request.form.get('allowances', 0), 'Allowances')
        bonus = validate_float(request.form.get('bonus', 0), 'Bonus')
        tax_rate = validate_float(request.form.get('tax_rate', 19), 'Tax Rate')
        
        if tax_rate > 100:
            raise BadRequest("Tax rate must be between 0 and 100.")

        # Calculations
        gross_monthly = monthly_salary + allowances
        gross_contract_income = (gross_monthly * contract_months) + bonus
        taxes = (gross_contract_income * tax_rate) / 100
        net_contract_income = gross_contract_income - taxes

        # Results object
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

        # Render the results on the same page
        return render_template('income.html', results=results, error=None)

    except BadRequest as e:
        # Render template with error message
        return render_template('income.html', results=None, error=str(e))

@income_bp.route('/', methods=['GET'])
def income_form():
    """Display income calculation form"""
    return render_template('income.html', results=None, error=None)

# Goals route
@app.route('/goals', methods=['GET', 'POST'])
def goals():
    return render_template('goals.html')

# Register Blueprint
app.register_blueprint(income_bp)

# Run app
if __name__ == '__main__':
    app.run(debug=True)