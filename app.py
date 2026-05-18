from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

lrv_hash_map = {
    "LRV-1012": {"issue": "120k km Bogie Overhaul Reached", "mileage": "120,050", "status": "red", "assignee": "Syafiq Y.", "file": "hubometer_1012.png"},
    "LRV-2044": {"issue": "OCR Parsing Failed (Manual Review)", "mileage": "Unknown", "status": "orange", "assignee": "Javier S.", "file": "raw_cam_2044.png"},
    "LRV-1088": {"issue": "13k km Preventive Cycle", "mileage": "13,015", "status": "red", "assignee": "Huizhong L.", "file": "hubometer_1088.png"},
    "LRV-3021": {"issue": "Routine Status Update", "mileage": "45,200", "status": "green", "assignee": "Si Kai O.", "file": "hubometer_3021.png"},
    "LRV-1055": {"issue": "2k km Visual Inspection", "mileage": "2,050", "status": "red", "assignee": "Charissa K.", "file": "hubometer_1055.png"}
}

@app.route('/')
def dashboard():
    return render_template('index.html', lrv_data=lrv_hash_map)

if __name__ == '__main__':
    app.run(debug=True)