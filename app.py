from flask import Flask, render_template

app = Flask(__name__)

# --- SINGLY LINKED LIST ARCHITECTURE ---
class Node:
    def __init__(self, date, issue, mileage, next_node=None):
        self.date = date
        self.issue = issue
        self.mileage = mileage
        self.next_node = next_node  # The pointer to the previous historical record

class MaintenanceHistoryLinkedList:
    def __init__(self):
        self.head = None

    # Insert a new scan at the front (head) of the list
    def add_scan(self, date, issue, mileage):
        new_node = Node(date, issue, mileage, self.head)
        self.head = new_node

    # Convert the linked list to a standard Python list so HTML/Jinja can read it
    def to_list(self):
        history = []
        current = self.head
        while current:
            history.append({"date": current.date, "issue": current.issue, "mileage": current.mileage})
            current = current.next_node
        return history

# --- MOCK DATA GENERATION ---
# Create histories for our trains
history_1012 = MaintenanceHistoryLinkedList()
history_1012.add_scan("10 May 2026", "40k km Bogie Inspection", "40,010")
history_1012.add_scan("20 May 2026", "Routine Status Update", "85,400")
history_1012.add_scan("22 May 2026", "120k km Bogie Overhaul Reached", "120,050") # Current Head

history_1088 = MaintenanceHistoryLinkedList()
history_1088.add_scan("01 May 2026", "2k km Visual Inspection", "2,015")
history_1088.add_scan("22 May 2026", "13k km Preventive Cycle", "13,015") # Current Head

history_3021 = MaintenanceHistoryLinkedList()
history_3021.add_scan("15 May 2026", "Routine Status Update", "45,200") # Current Head

# O(1) Hash Map now contains the Linked List history
lrv_hash_map = {
    "LRV-1012": {"issue": "120k km Bogie Overhaul Reached", "mileage": "120,050", "status": "red", "assignee": "Syafiq Y.", "file": "hubometer_1012.png", "history": history_1012.to_list()},
    "LRV-2044": {"issue": "OCR Parsing Failed (Manual Review)", "mileage": "Unknown", "status": "orange", "assignee": "Javier S.", "file": "raw_cam_2044.png", "history": []},
    "LRV-1088": {"issue": "13k km Preventive Cycle", "mileage": "13,015", "status": "red", "assignee": "Huizhong L.", "file": "hubometer_1088.png", "history": history_1088.to_list()},
    "LRV-3021": {"issue": "Routine Status Update", "mileage": "45,200", "status": "green", "assignee": "Si Kai O.", "file": "hubometer_3021.png", "history": history_3021.to_list()}
}

@app.route('/')
def dashboard():
    return render_template('index.html', lrv_data=lrv_hash_map)

if __name__ == '__main__':
    app.run(debug=True)