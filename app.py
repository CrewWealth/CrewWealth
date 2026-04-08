import os
from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, port=5000)
