import os
import random
from flask import Flask, json, redirect, render_template, request, url_for
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

# Initialise the rich console
console = Console()

rejected_lrvs = []

app = Flask(__name__)

available_technicians = ["Charissa K.", "Javier S.", "Hui Zhong L.", "Si Kai O.", "Syafiq Y."]

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

#store data in a hashmap (dynamic)
lrv_hash_map = {}

def load_database(filepath="database.json"):
    global lrv_hash_map
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            lrv_hash_map = json.load(file)
            console.print("[bold green]✅ Database loaded successfully![/bold green]")
    else:
        console.print("[bold red]🚨 database.json not found![/bold red]")

def save_database(filepath="database.json"):
    with open(filepath, 'w') as file:
        #indent=4 makes the JSON file neat
        json.dump(lrv_hash_map, file, indent=4) 
        console.print("[bold blue]💾 Database saved to disk![/bold blue]")

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
    

def process_hardware_files(qr_file_path="../logs/qr_log.txt", ocr_file_path="../logs/ocr_log.txt"):
    """
    Reads multiple LRV IDs and mileages line-by-line.
    Later entries naturally override earlier ones in the Hash Map.
    """
    global rejected_lrvs

    if not os.path.exists(qr_file_path) or not os.path.exists(ocr_file_path):
        console.print("[bold red]🚨 Waiting for hardware files...[/bold red]")
        return False

    try:
        with open(qr_file_path, 'r') as q_file:
            qr_lines = [line.strip().upper() for line in q_file.readlines() if line.strip()]

        with open(ocr_file_path, 'r') as o_file:
            ocr_lines = [line.strip() for line in o_file.readlines() if line.strip()]

        # Check both files have the exact same number of lines
        if len(qr_lines) != len(ocr_lines) or len(qr_lines) == 0:
            console.print(f"[bold red]🚨 Error: Mismatch in number of lines. QR: {len(qr_lines)}, OCR: {len(ocr_lines)}[/bold red]")
            return False

        updates_made = False

        # Loop through both files line by line simultaneously
        for lrv_id, ocr_payload in zip(qr_lines, ocr_lines):

            clean_lrv_id = lrv_id.strip()

            # 1. QR SANITISATION & FORMAT VALIDATION
            if not clean_lrv_id or clean_lrv_id.upper() in ["ERROR", "UNKNOWN", "NULL"]:
                console.print("[bold red]🚨 QR Scanner Error: Failed to extract a valid LRV ID. Skipping entry.[/bold red]")
                continue

            if not (clean_lrv_id.startswith("LRV-") and clean_lrv_id[4:].isdigit()):
                console.print(f"[bold dark_orange]🚨 QR Format Error:[/bold dark_orange] '{clean_lrv_id}' is invalid. Skipping entry.")
                rejected_lrvs.append(clean_lrv_id)
                continue

            # Unpack the OCR payload into mileage and confidence
            try:
                raw_reading, raw_conf = ocr_payload.split(',')
            except ValueError:
                console.print(f"[bold red]🚨 Format Error: OCR payload '{ocr_payload}' is missing a comma.[/bold red]")
                continue

            # 2. INITIALISE NEW VEHICLES IMMEDIATELY
            if clean_lrv_id not in lrv_hash_map:
                assigned_tech = random.choice(available_technicians)
                
                lrv_hash_map[clean_lrv_id] = {
                    "technician": assigned_tech,
                    "mileage": "0",
                    "status": "green",
                    "issue": "Routine Status Update",
                    "forecast": {"target": "Pending", "days_left": "N/A", "pct": 0},
                    "consecutive_failures": 0,
                    "hardware_fault": False,
                    "ocr_confidence": 0
                }
                console.print(Panel(f"Registering {clean_lrv_id} to technician {assigned_tech}.", title="🆕 New Vehicle Detected", style="bold blue"))
            
            # Fallback for old database entries that might be missing a technician
            elif "technician" not in lrv_hash_map[clean_lrv_id]:
                lrv_hash_map[clean_lrv_id]["technician"] = random.choice(available_technicians)

            # 3. ATTEMPT OCR VALIDATION
            try:
                mileage_int = int(raw_reading)

                # Confidence Parsing and Conversion
                try:
                    conf_float = float(raw_conf.strip())
                    # If EasyOCR exports a decimal (e.g. 0.95), convert to 95. Otherwise keep as is.
                    conf_pct = int(conf_float * 100) if conf_float <= 1.0 else int(conf_float)
                except ValueError:
                    conf_pct = 0
                # Logical Bounds Validation
                if mileage_int < 0 or mileage_int > 1000000:
                    raise ValueError("Out of bounds") 
                    
                # Monotonicity Validation (check that mileage doesn't decrease)
                current_mileage_str = lrv_hash_map[clean_lrv_id].get("mileage", "Unknown")
                if current_mileage_str != "Unknown":
                    current_mileage_int = int(current_mileage_str.replace(",", ""))
                    if mileage_int < current_mileage_int:
                        raise ValueError("Mileage anomaly") 
                
                # SUCCESS: Reset the failure counter because we got a good read!
                lrv_hash_map[clean_lrv_id]["consecutive_failures"] = 0
                lrv_hash_map[clean_lrv_id]["hardware_fault"] = False

                formatted_mileage = f"{mileage_int:,}"
                new_status, new_issue = maintenance_logic_engine(mileage_int)
                new_forecast = generate_forecast(formatted_mileage, 130)

                # Update the Hash Map with the new validated data
                lrv_hash_map[clean_lrv_id]["mileage"] = formatted_mileage
                lrv_hash_map[clean_lrv_id]["status"] = new_status
                lrv_hash_map[clean_lrv_id]["issue"] = new_issue
                lrv_hash_map[clean_lrv_id]["forecast"] = new_forecast
                lrv_hash_map[clean_lrv_id]["ocr_confidence"] = conf_pct
                
                updates_made = True
                console.print(f"[bold green]✅ Hardware Sync:[/bold green] [cyan]{clean_lrv_id}[/cyan] updated to [bold]{formatted_mileage} km[/bold]!")

            except ValueError as e:
                # 4. FAILURE HANDLING
                console.print(f"[bold yellow]⚠️ Scan failed for {clean_lrv_id}. Reason: {e}[/bold yellow]")

                # Increment the consecutive failure counter
                lrv_hash_map[clean_lrv_id]["consecutive_failures"] += 1
                strikes = lrv_hash_map[clean_lrv_id]["consecutive_failures"]

                # Update the status and issue in the Hash Map
                lrv_hash_map[clean_lrv_id]["status"] = "orange"
                lrv_hash_map[clean_lrv_id]["issue"] = f"OCR Parsing Failed ({strikes}/3) - Manual Review Needed"
                
                # If it fails 3 times in a row, trigger the manual review
                if strikes >= 3:
                    console.print(f"[bold red]🚨 Chronic Failure Alert: {clean_lrv_id} has failed 3 consecutive scans.[/bold red]")
                    lrv_hash_map[clean_lrv_id]["hardware_fault"] = True
                    lrv_hash_map[clean_lrv_id]["issue"] = "Chronic Scanner Failure - Manual Review Needed"
                    lrv_hash_map[clean_lrv_id]["ocr_confidence"] = random.randint(10, 45)
                
                updates_made = True

        if updates_made:
            save_database()

        return True

    except Exception as e:
        console.print(f"[bold red]🚨 Unexpected Error during sync: {e}[/bold red]")
        return False
    
@app.route('/')

def dashboard():
    status_counts = {
        "total": len(lrv_hash_map),
        "red": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "red"),
        "green": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "green"),
        "orange": sum(1 for lrv in lrv_hash_map.values() if lrv["status"] == "orange")
    }
    return render_template('index.html', lrv_hash_map=lrv_hash_map, lrv_data = lrv_hash_map, rejected_lrvs = rejected_lrvs, counts=status_counts)

@app.route('/trigger_hardware_sync', methods=['GET'])
def trigger_hardware_sync():
    #looks for the files dropped by the camera/QR prototype
    process_hardware_files("../logs/qr_log.txt", "../logs/ocr_log.txt")
    
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
            lrv_hash_map[lrv_id]["ocr_confidence"] = 100 #simulate a successful confidence score for the OCR reading
            lrv_hash_map[lrv_id]["forecast"] = generate_forecast(formatted_mileage, 130)
            
            save_database()
            
    except ValueError:
        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["status"] = "orange"
            lrv_hash_map[lrv_id]["issue"] = "OCR Parsing Failed - Manual Review Needed"
            lrv_hash_map[lrv_id]["mileage"] = "Unknown"
            lrv_hash_map[lrv_id]["ocr_confidence"] = 0 #simulate a failed confidence score for the OCR reading
            save_database()

    return redirect(url_for('dashboard')) #refresh the page after updating

# Global variable to track the last time the files were modified
last_known_mtime = 0

@app.route('/check_updates', methods=['GET'])
def check_updates():
    """
    Checks the hard drive timestamps of the 2 hardware logs.
    Returns True only if the files have been modified since the last check.
    """
    global last_known_mtime
    hardware_files = ["../logs/qr_log.txt", "../logs/ocr_log.txt"]
    
    latest_mtime = 0
    
    # Check the modification time (mtime) of all existing files
    for file_path in hardware_files:
        if os.path.exists(file_path):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime > latest_mtime:
                latest_mtime = file_mtime
                
    # If the files are newer than our last check, tell the frontend to update!
    if latest_mtime > last_known_mtime:
        last_known_mtime = latest_mtime
        return {"changed": True}
        
    return {"changed": False}

if __name__ == '__main__':
    load_database()

    startup_message = """
    [bold cyan]OptiTrack LRT[/bold cyan] - Trackside Edge Node Server
    Status: [bold green]Online and Listening[/bold green]
    Database: [yellow]database.json[/yellow] (O(1) Hash Map Active)
    """

    rprint(Panel.fit(startup_message, border_style="cyan"))
    app.run(debug=True)