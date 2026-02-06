import os
from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.errorhandler(404)
def not_found_error(error):
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, port=5000)
