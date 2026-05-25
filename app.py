from flask import Flask, render_template

app = Flask(__name__)

class Node:
    def __init__(self, date, issue, mileage, next_node=None):
        self.date = date
        self.issue = issue
        self.mileage = mileage
        self.next_node = next_node

class MaintenanceHistoryLinkedList:
    def __init__(self):
        self.head = None
    def add_scan(self, date, issue, mileage):
        self.head = Node(date, issue, mileage, self.head)
    def to_list(self):
        history = []
        current = self.head
        while current:
            history.append({"date": current.date, "issue": current.issue, "mileage": current.mileage})
            current = current.next_node
        return history

THRESHOLDS = {
    2000: "2k km Visual Inspection",
    13000: "13k km Preventive Cycle",
    40000: "40k km Bogie Inspection",
    120000: "120k km Bogie Overhaul",
    360000: "360k km System Overhaul"
}

def generate_forecast(current_mileage_str, daily_avg_km):
    if current_mileage_str == "Unknown":
        return {"days_left": "N/A", "target": "Manual Review Required", "pct": 0}
        
    current_km = int(current_mileage_str.replace(",", ""))
    
    #find the next maintenance threshold
    prev_target = 0
    next_target = None
    target_name = ""
    
    for limit, name in sorted(THRESHOLDS.items()):
        if current_km < limit:
            next_target = limit
            target_name = name
            break
        prev_target = limit
            
    if not next_target:
        return {"days_left": 0, "target": "End of Lifecycle", "pct": 100}
        
    #calculate days remaining and progress percentage
    remaining_km = next_target - current_km
    days_left = remaining_km // daily_avg_km
    
    tier_range = next_target - prev_target
    km_into_tier = current_km - prev_target
    progress_pct = int((km_into_tier / tier_range) * 100)
    
    return {
        "days_left": days_left,
        "target": target_name,
        "pct": progress_pct
    }

#testing dataa
history_1012 = MaintenanceHistoryLinkedList()
history_1012.add_scan("22 May 2026", "120k km Bogie Overhaul Reached", "120,050")

history_1088 = MaintenanceHistoryLinkedList()
history_1088.add_scan("22 May 2026", "13k km Preventive Cycle", "13,015")

history_3021 = MaintenanceHistoryLinkedList()
history_3021.add_scan("15 May 2026", "Routine Status Update", "45,200")

#hashmap foer data (fixed values now... change later to be dynamic from DB or OCR input)
lrv_hash_map = {
    "LRV-1012": {"issue": "120k km Overhaul Reached", "mileage": "120,050", "status": "red", "assignee": "Syafiq Y.", "file": "hubometer_1012.png", "ocr_confidence": 98, "history": history_1012.to_list(), "forecast": generate_forecast("120,050", 120)},
    "LRV-2044": {"issue": "OCR Parsing Failed", "mileage": "Unknown", "status": "orange", "assignee": "Javier S.", "file": "raw_cam_2044.png", "ocr_confidence": 14, "history": [], "forecast": generate_forecast("Unknown", 120)},
    "LRV-1088": {"issue": "13k km Preventive Cycle", "mileage": "13,015", "status": "red", "assignee": "Huizhong L.", "file": "hubometer_1088.png", "ocr_confidence": 89, "history": history_1088.to_list(), "forecast": generate_forecast("13,015", 140)},
    "LRV-3021": {"issue": "Routine Status Update", "mileage": "45,200", "status": "green", "assignee": "Si Kai O.", "file": "hubometer_3021.png", "ocr_confidence": 99, "history": history_3021.to_list(), "forecast": generate_forecast("45,200", 135)}
}

@app.route('/')
def dashboard():
    status_counts = {
        "total": len(lrv_hash_map),
        "red": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "red"),
        "green": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "green"),
        "orange": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "orange")
    }
    return render_template('index.html', lrv_data=lrv_hash_map, counts=status_counts)

if __name__ == '__main__':
    app.run(debug=True)