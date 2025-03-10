from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Allow requests from your Netlify frontend
CORS(app, resources={r"/*": {"origins": ["https://dfic-fund.netlify.app", "https://api.degrootefinance.com/"]}})


@app.route('/api/data', methods=['GET'])
def get_data():
    # Replace with your actual data logic
    return jsonify({"message": "Hello from Flask API!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)