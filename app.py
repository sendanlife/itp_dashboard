import os
import random
from flask import Flask, json, redirect, render_template, request, url_for

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

#testing data
history_1012 = MaintenanceHistoryLinkedList()
history_1012.add_scan("22 May 2026", "120k km Bogie Overhaul Reached", "120,050")

history_1088 = MaintenanceHistoryLinkedList()
history_1088.add_scan("22 May 2026", "13k km Preventive Cycle", "13,015")

history_3021 = MaintenanceHistoryLinkedList()
history_3021.add_scan("15 May 2026", "Routine Status Update", "45,200")

#store data in a hashmap (dynamic)
lrv_hash_map = {}

def load_database(filepath="database.json"):
    global lrv_hash_map
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            lrv_hash_map = json.load(file)
            print("✅ Database loaded successfully!")
    else:
        print("🚨 database.json not found!")

def save_database(filepath="database.json"):
    with open(filepath, 'w') as file:
        #indent=4 makes the JSON file neat
        json.dump(lrv_hash_map, file, indent=4) 
        print("💾 Database saved to disk!")

def maintenance_logic_engine(mileage_int):
    """
    Compares the mileage against the preventive cycles.
    Returns the appropriate (status_color, issue_text).
    """
    if mileage_int >= 360000:
        return "red", "360k km System Overhaul"
    elif mileage_int >= 120000:
        return "red", "120k km Bogie Overhaul Reached"
    elif mileage_int >= 40000:
        return "orange", "40k km Bogie Inspection"
    elif mileage_int >= 13000:
        return "orange", "13k km Preventive Cycle"
    elif mileage_int >= 2000:
        return "green", "2k km Visual Inspection"
    else:
        return "green", "Routine Status Update"
    

def calculate_forecast(mileage_int):
    """
    Calculates the next maintenance target, percentage progress, 
    and estimated days left based on the current mileage.
    """
    thresholds = [
        (2000, "2k km Visual Inspection"),
        (13000, "13k km Preventive Cycle"),
        (40000, "40k km Bogie Inspection"),
        (120000, "120k km Bogie Overhaul"),
        (360000, "360k km System Overhaul")
    ]
    
    next_target = "System End of Life"
    next_threshold_km = 360000
    prev_threshold_km = 0
    
    for km, label in thresholds:
        if mileage_int < km:
            next_target = label
            next_threshold_km = km
            break
        prev_threshold_km = km
        
    if mileage_int >= 360000:
        pct = 100
        days_left = "0"
    else:
        cycle_length = next_threshold_km - prev_threshold_km
        km_into_cycle = mileage_int - prev_threshold_km
        
        pct = int((km_into_cycle / cycle_length) * 100)
        
        km_left = next_threshold_km - mileage_int
        days_left = str(int(km_left / 150))
        
    return {
        "target": next_target,
        "days_left": days_left,
        "pct": pct
    }

def process_ocr_reading(lrv_id, file_path="ocr_output.txt"):
    """
    Reads the 6-digit OCR output from a text file and updates the LRV Hash Map.
    """
    if not os.path.exists(file_path):
        print(f"🚨 File not found: {file_path}")
        return False
        
    try:

        with open(file_path, 'r') as file:

            raw_reading = file.read().strip() 
            
        mileage_int = int(raw_reading)
        
        formatted_mileage = f"{mileage_int:,}" 
        
        new_status, new_issue = maintenance_logic_engine(mileage_int)
        
        #update the hash map with the new values
        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["mileage"] = formatted_mileage
            lrv_hash_map[lrv_id]["status"] = new_status
            lrv_hash_map[lrv_id]["issue"] = new_issue
            
            lrv_hash_map[lrv_id]["forecast"] = generate_forecast(formatted_mileage, 130)

            save_database()
            print(f"✅ SUCCESS: {lrv_id} updated to {formatted_mileage} km! Status: {new_status}")
            return True
        else:
            print(f"⚠️ LRV {lrv_id} not found in database.")
            return False
            
    except ValueError:
        print("🚨 OCR Parsing Failed: The text file contains non-number characters.")
        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["status"] = "orange"
            lrv_hash_map[lrv_id]["issue"] = "OCR Parsing Failed - Manual Review Needed"
            lrv_hash_map[lrv_id]["mileage"] = "Unknown"
        return False
    

def process_hardware_files(qr_file_path="qr_output.txt", ocr_file_path="ocr_output.txt"):
    """
    Reads multiple LRV IDs and mileages line-by-line.
    Later entries naturally override earlier ones in the Hash Map.
    """
    if not os.path.exists(qr_file_path) or not os.path.exists(ocr_file_path):
        print("🚨 Waiting for hardware files...")
        return False

    try:
        with open(qr_file_path, 'r') as q_file:
            qr_lines = [line.strip().upper() for line in q_file.readlines() if line.strip()]

        with open(ocr_file_path, 'r') as o_file:
            ocr_lines = [line.strip() for line in o_file.readlines() if line.strip()]

        #check both files have the exact same number of lines
        if len(qr_lines) != len(ocr_lines):
            print("🚨 Error: Mismatch in number of lines between QR and OCR files.")
            return False

        updates_made = False

        #loop through both files line by line simultaneously
        for lrv_id, raw_reading in zip(qr_lines, ocr_lines):
            try:
                mileage_int = int(raw_reading)
                formatted_mileage = f"{mileage_int:,}"

                new_status, new_issue = maintenance_logic_engine(mileage_int)
                new_forecast = generate_forecast(formatted_mileage, 130)

                if lrv_id in lrv_hash_map:
                    lrv_hash_map[lrv_id]["mileage"] = formatted_mileage
                    lrv_hash_map[lrv_id]["status"] = new_status
                    lrv_hash_map[lrv_id]["issue"] = new_issue
                    lrv_hash_map[lrv_id]["forecast"] = new_forecast

                    lrv_hash_map[lrv_id]["ocr_confidence"] = random.randint(88, 99) #simulate a successful confidence score for the OCR reading
                    
                    
                    updates_made = True
                    print(f"✅ Hardware Sync: {lrv_id} updated to {formatted_mileage} km!")
                else:
                    print(f"⚠️ LRV {lrv_id} not found in database.")

            except ValueError:
                print(f"🚨 OCR Parsing Failed for {lrv_id}: Non-number characters detected.")
                if lrv_id in lrv_hash_map:
                    lrv_hash_map[lrv_id]["status"] = "orange"
                    lrv_hash_map[lrv_id]["issue"] = "OCR Parsing Failed - Manual Review Needed"
                    lrv_hash_map[lrv_id]["mileage"] = "Unknown"
                    lrv_hash_map[lrv_id]["forecast"] = {"target": "Manual Review Required", "days_left": "N/A", "pct": 0}

                    lrv_hash_map[lrv_id]["ocr_confidence"] = random.randint(10, 45) #simulate a failed confidence score for the OCR reading
                    updates_made = True

        if updates_made:
            save_database()

        #remove the temporary files after processing    
        #os.remove(qr_file_path)
        #os.remove(ocr_file_path)
        return True

    except Exception as e:
        print(f"🚨 Unexpected Error during sync: {e}")
        return False
    
@app.route('/')

def dashboard():
    status_counts = {
        "total": len(lrv_hash_map),
        "red": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "red"),
        "green": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "green"),
        "orange": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "orange")
    }
    return render_template('index.html', lrv_data=lrv_hash_map, counts=status_counts)

@app.route('/trigger_hardware_sync', methods=['GET'])
def trigger_hardware_sync():
    #looks for the files dropped by the camera/QR prototype
    process_hardware_files("qr_output.txt", "ocr_output.txt")
    
    #refreshes the dashboard to show the new data
    return redirect(url_for('dashboard'))

@app.route('/update_mileage', methods=['POST'])
def update_mileage():
    lrv_id = request.form.get('lrv_id')
    raw_reading = request.form.get('mileage')

    if not lrv_id or not raw_reading:
        return redirect(url_for('dashboard'))

    try:
        mileage_int = int(raw_reading.strip())
        formatted_mileage = f"{mileage_int:,}"
        
        new_status, new_issue = maintenance_logic_engine(mileage_int)

        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["mileage"] = formatted_mileage
            lrv_hash_map[lrv_id]["status"] = new_status
            lrv_hash_map[lrv_id]["issue"] = new_issue
            
            lrv_hash_map[lrv_id]["forecast"] = calculate_forecast(mileage_int)
            lrv_hash_map[lrv_id]["ocr_confidence"] = 100
            
            save_database()
            
    except ValueError:
        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["status"] = "orange"
            lrv_hash_map[lrv_id]["issue"] = "OCR Parsing Failed - Manual Review Needed"
            lrv_hash_map[lrv_id]["mileage"] = "Unknown"
            save_database()

    return redirect(url_for('dashboard')) #refresh the page after updating

if __name__ == '__main__':
    load_database()
    app.run(debug=True)