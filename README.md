# 💖 TRUST BRIDGE HEARTS (TBH)

## Project Description
TRUST BRIDGE HEARTS is a transparent, secure, and user-centric web application built with Python's Flask framework. Its core mission is to **eliminate doubt in charitable giving** by providing verifiable proof of donation impact directly to the donor.

The application serves as a bridge between individual donors and local, high-impact charitable trusts, primarily focusing on causes like Education, Shelter, Healthcare, and Skill Development in the Chennai region.

---

## ✨ Key Features

* **Donor Registration & Login:** Secure registration with credentials emailed to the donor, including a first-time login process.
* **Intelligent Trust Recommendation (KNN):** Uses a K-Nearest Neighbors (KNN) algorithm to recommend trusts to donors based on similar donor profiles (gender, occupation, income).
* **UPI-Based Donation:** Facilitates donations via UPI QR code generation with a dedicated UPI ID.
* **Mandatory Expense Reporting (Zero Ambiguity):** Trusts log in to a dedicated dashboard to submit expense reports, including **actual receipts and photo proof**, which are automatically emailed to the respective donor.
* **Traceability and Confirmation:** Donors confirm their UPI payment, recording the UPI ID for secure traceability.
* **Dedicated Dashboards:** Separate protected dashboards for Donors (to view donation history) and Trust Representatives (to submit expense reports).

---

## 🛠️ Technology Stack

* **Backend Framework:** Flask (Python)
* **Database/Data Storage:** JSON files (`donors.json`)
* **Machine Learning:** `scikit-learn` for K-Nearest Neighbors (KNN) Recommendation
* **Email Service:** Google Gmail API (`google-api-python-client`) for sending automated credentials and expense proofs
* **Data Handling:** `pandas` and `numpy`
* **Virtual Environment:** Python 3.11.8

---

## ⚙️ Setup and Installation

### Prerequisites
* Python 3.11+
* A Google account with Gmail API enabled (requires `credentials.json` and `token.json`)

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone [your-repo-link]
    cd trust-bridge-hearts
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    .\venv\Scripts\activate   # On Windows
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables (CRITICAL):**
    The application requires securing sensitive data. Create a `.env` file or export the following:
    ```bash
    # Example (replace with your actual secret key and UPI ID)
    export SECRET_KEY='your_strong_flask_secret_key'
    export UPI_ID='abinayaruthirakotti@okicici'
    ```

5.  **Run the Application:**
    ```bash
    python app.py
    ```
    The application will run on `http://127.0.0.1:5000/`.

---
