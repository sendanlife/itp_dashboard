# Optitrack LRT: Maintenance Dashboard 🚈

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-SIT-green)

## 📌 Overview
The Optitrack LRT Maintenance Dashboard is an administrative web interface designed to monitor the health and performance of a Light Rail Transit network. It provides systems engineers with a centralized platform to track hardware states, log system anomalies, and optimize the deployment of maintenance crews across the transit grid.

## ✨ Core Features
* **Real-Time Fault Tracking:** Centralized logging of rolling stock and trackside hardware states to flag system anomalies.
* **Algorithmic Crew Dispatch:** Leverages local search heuristics and advanced tree configurations within the Python backend to calculate path optimization for maintenance crews, minimizing response times.
* **Execution Efficiency:** Data structures are structured for rapid traversal, ensuring the dashboard updates efficiently even when processing large volumes of transit data.
* **Interactive UI:** Clean, responsive frontend built with native HTML and CSS to visualize transit lines and fault locations without heavy client-side frameworks.

## 🛠️ Tech Stack
* **Frontend:** HTML5, CSS3
* **Backend & API:** Python 
* **Algorithm Engine:** Python (Handling route optimization heuristics and data structure management)

## 🚀 Getting Started

### Prerequisites
Before running the dashboard locally, ensure you have the following installed:
* [Python](https://www.python.org/) (3.8 or higher)
* [Git](https://git-scm.com/)

### ⚙️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-organization/optitrack-lrt-dashboard.git](https://github.com/your-organization/optitrack-lrt-dashboard.git)
    cd optitrack-lrt-dashboard
    ```

2.  **Set up a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    
    # On Windows:
    venv\Scripts\activate
    
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    *(If you are using a framework like Flask or specific Python libraries, install them here)*
    ```bash
    pip install -r requirements.txt
    ```

### 🖥️ Running the Application

To spin up the dashboard locally, execute the main Python script to start the local web server:

```bash
python app.py
