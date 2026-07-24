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
    

def calculate_forecast(mileage_int):
    """
    Calculates the next maintenance target, percentage progress, 
    and estimated days left based on the current mileage.
    """
    # 1. Define our maintenance thresholds in ascending order
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
    
    # 2. Find which cycle the train is currently in
    for km, label in thresholds:
        if mileage_int < km:
            next_target = label
            next_threshold_km = km
            break
        prev_threshold_km = km
        
    # 3. Calculate the math for the UI progress bar and days left
    if mileage_int >= 360000:
        pct = 100
        days_left = "0"
    else:
        cycle_length = next_threshold_km - prev_threshold_km
        km_into_cycle = mileage_int - prev_threshold_km
        
        # Calculate percentage (0 to 100)
        pct = int((km_into_cycle / cycle_length) * 100)
        
        # Estimate days left (Assuming ~150km traveled per day)
        km_left = next_threshold_km - mileage_int
        days_left = str(int(km_left / 150))
        
    return {
        "target": next_target,
        "days_left": days_left,
        "pct": pct
    }
    

def process_hardware_files(qr_file_path="qr_log.txt", ocr_file_path="ocr_log.txt"):
    """
    Reads multiple LRV IDs and mileages line-by-line.
    Later entries naturally override earlier ones in the Hash Map.
    """
    rejected_lrvs = []

    if not os.path.exists(qr_file_path) or not os.path.exists(ocr_file_path):
        console.print("[bold red]🚨 Waiting for hardware files...[/bold red]")
        return False

    try:
        with open(qr_file_path, 'r') as q_file:
            qr_lines = [line.strip().upper() for line in q_file.readlines() if line.strip()]

        with open(ocr_file_path, 'r') as o_file:
            ocr_lines = [line.strip() for line in o_file.readlines() if line.strip()]

        #check both files have the exact same number of lines
        if len(qr_lines) != len(ocr_lines):
            console.print("[bold red]🚨 Error: Mismatch in number of lines between QR and OCR files.[/bold red]")
            return False

        updates_made = False

        
            # loop through both files line by line simultaneously
        for lrv_id, raw_reading in zip(qr_lines, ocr_lines):

            clean_lrv_id = lrv_id.strip()

            # 1. QR VALIDATION & SANITISATION
            if not clean_lrv_id or clean_lrv_id.upper() in ["ERROR", "UNKNOWN", "NULL"]:
                console.print("[bold red]🚨 QR Scanner Error: Failed to extract a valid LRV ID. Skipping entry.[/bold red]")
                continue

            if not (clean_lrv_id.startswith("LRV-") and clean_lrv_id[4:].isdigit()):
                console.print(f"[bold dark_orange]🚨 QR Format Error:[/bold dark_orange] '{clean_lrv_id}' is invalid. Skipping entry.")
                rejected_lrvs.append(clean_lrv_id)
                continue

            # 2. INITIALISE NEW VEHICLES IMMEDIATELY
            # We do this BEFORE the try block so the vehicle exists even if the OCR scan fails
            if clean_lrv_id not in lrv_hash_map:
                lrv_hash_map[clean_lrv_id] = {
                    "mileage": "0",
                    "status": "green",
                    "issue": "Routine Status Update",
                    "forecast": {"target": "Pending", "days_left": "N/A", "pct": 0},
                    "consecutive_failures": 0,
                    "hardware_fault": False,
                    "ocr_confidence": 0
                }
                console.print(Panel(f"Registering {clean_lrv_id} to database.", title="🆕 New Vehicle Detected", style="bold blue"))

            # 3. ATTEMPT OCR VALIDATION
            try:
                mileage_int = int(raw_reading)
                
                # Logical Bounds Validation
                if mileage_int < 0 or mileage_int > 1000000:
                    raise ValueError("Out of bounds") 
                    
                # Monotonicity Validation
                current_mileage_str = lrv_hash_map[clean_lrv_id].get("mileage", "Unknown")
                if current_mileage_str != "Unknown":
                    current_mileage_int = int(current_mileage_str.replace(",", ""))
                    if mileage_int < current_mileage_int:
                        raise ValueError("Mileage anomaly") 
                
                # SUCCESS: Reset the failure counter and update data
                lrv_hash_map[clean_lrv_id]["consecutive_failures"] = 0
                lrv_hash_map[clean_lrv_id]["hardware_fault"] = False
                
                formatted_mileage = f"{mileage_int:,}"
                new_status, new_issue = maintenance_logic_engine(mileage_int)
                new_forecast = generate_forecast(formatted_mileage, 130)
                
                lrv_hash_map[clean_lrv_id]["mileage"] = formatted_mileage
                lrv_hash_map[clean_lrv_id]["status"] = new_status
                lrv_hash_map[clean_lrv_id]["issue"] = new_issue
                lrv_hash_map[clean_lrv_id]["forecast"] = new_forecast
                lrv_hash_map[clean_lrv_id]["ocr_confidence"] = random.randint(88, 99) 
                
                updates_made = True
                console.print(f"[bold green]✅ Hardware Sync:[/bold green] [cyan]{clean_lrv_id}[/cyan] updated to [bold]{formatted_mileage} km[/bold]!")

            except ValueError as e:
                # 4. FAILURE LOGIC FOR ALL STRIKES
                console.print(f"[bold yellow]⚠️ Scan failed for {clean_lrv_id}. Reason: {e}[/bold yellow]")
                
                # Because we initialized above, it is guaranteed to be in the Hash Map
                lrv_hash_map[clean_lrv_id]["consecutive_failures"] += 1
                strikes = lrv_hash_map[clean_lrv_id]["consecutive_failures"]
                
                # Always update the status to orange for strikes 1 and 2
                lrv_hash_map[clean_lrv_id]["status"] = "orange"
                lrv_hash_map[clean_lrv_id]["issue"] = f"OCR Parsing Failed ({strikes}/3) - Manual Review Needed"
                
                # Check for critical 3-strike failure
                if strikes >= 3:
                    console.print(f"[bold red]🚨 Chronic Failure Alert: {clean_lrv_id} has failed 3 consecutive scans.[/bold red]")
                    lrv_hash_map[clean_lrv_id]["hardware_fault"] = True
                    lrv_hash_map[clean_lrv_id]["issue"] = "Chronic Scanner Failure - Manual Review Needed"
                    lrv_hash_map[clean_lrv_id]["ocr_confidence"] = random.randint(10, 45)
                
                # We MUST set this to True so the database saves the strike!
                updates_made = True
            else:
                console.print(f"[bold yellow]⚠️ Strike {strikes}/3. Ignoring minor glitch.[/bold yellow]")
                continue # Skip updating the dashboard for Strikes 1 and 2

        if updates_made:
            save_database()

        #remove the temporary files after processing    
        #os.remove(qr_file_path)
        #os.remove(ocr_file_path)
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
    process_hardware_files("qr_log.txt", "ocr_log.txt")
    
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
            lrv_hash_map[lrv_id]["forecast"] = calculate_forecast(mileage_int)
            
            save_database()
            
    except ValueError:
        if lrv_id in lrv_hash_map:
            lrv_hash_map[lrv_id]["status"] = "orange"
            lrv_hash_map[lrv_id]["issue"] = "OCR Parsing Failed - Manual Review Needed"
            lrv_hash_map[lrv_id]["mileage"] = "Unknown"
            lrv_hash_map[lrv_id]["ocr_confidence"] = 0 #simulate a failed confidence score for the OCR reading
            save_database()

    return redirect(url_for('dashboard')) #refresh the page after updating

if __name__ == '__main__':
    load_database()

    startup_message = """
    [bold cyan]OptiTrack LRT[/bold cyan] - Trackside Edge Node Server
    Status: [bold green]Online and Listening[/bold green]
    Database: [yellow]database.json[/yellow] (O(1) Hash Map Active)
    """

    rprint(Panel.fit(startup_message, border_style="cyan"))
    app.run(debug=True)