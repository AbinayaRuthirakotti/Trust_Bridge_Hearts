from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, random, string, json, base64, qrcode
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# --- Configuration ---
UPI_ID = "abinayaruthirakotti@okicici"
UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Donor Dataset ----------------
if os.path.exists('donors.json'):
    with open('donors.json') as f:
        donors = json.load(f)
else:
    donors = {}

# ---------------- Trust Login Credentials ----------------
TRUST_CREDENTIALS = {
    "trust1user": {"password": "trust1pass", "name": "Udhavum Ullangal Public Charitable Trust"},
    "trust2user": {"password": "trust2pass", "name": "Hope Public Charitable Trust"},
    "udavum_rep": {"password": "uda_pass", "name": "Udavum Ullangal"},
    "hearts_rep": {"password": "heart_pass", "name": "Helping Hearts Home"},
}

# ---------------- Trust Dataset (with full details for Contact Page) ----------------
trusts_chennai = [
    {
        "name": "Udhavum Ullangal Public Charitable Trust", 
        "email": "trust1@example.com", 
        "focus": "Education & Shelter",
        "phone": "+91-9876543210",
        "address": "123, Gandhi Road, Mylapore, Chennai, Tamil Nadu - 600004",
        "map_link": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15545.922849887752!2d80.2588102!3d13.0450502!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a52661d99903799%3A0x6b45a6c8e3b5e7d5!2sMylapore%2C%20Chennai%2C%20Tamil%20Nadu!5e0!3m2!1sen!2sin!4v1633512345678!5m2!1sen!2sin"
    },
    {
        "name": "Hope Public Charitable Trust", 
        "email": "trust2@example.com", 
        "focus": "Healthcare & Nutrition",
        "phone": "+91-9123456789",
        "address": "456, Anna Salai, T. Nagar, Chennai, Tamil Nadu - 600017",
        "map_link": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15546.68764032135!2d80.2458448!3d13.0336697!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a526715f33663a7%3A0xf67b60580d469777!2sT.%20Nagar%2C%20Chennai%2C%20Tamil%20Nadu!5e0!3m2!1sen!2sin!4v1633512345678!5m2!1sen!2sin"
    },
    {
        "name": "Udavum Ullangal", 
        "email": "trust3@example.com", 
        "focus": "Skill Development",
        "phone": "+91-9988776655",
        "address": "789, East Coast Road, Neelankarai, Chennai, Tamil Nadu - 600041",
        "map_link": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15549.982701460368!2d80.2464738!3d12.9868725!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a525f20f0196231%3A0xc33e2187f58b090!2sNeelankarai%2C%20Chennai%2C%20Tamil%20Nadu!5e0!3m2!1sen!2sin!4v1633512345678!5m2!1sen!2sin"
    },
    {
        "name": "Helping Hearts Home", 
        "email": "trust4@example.com", 
        "focus": "Education & Shelter",
        "phone": "+91-9000011111",
        "address": "101, Velachery Main Road, Guindy, Chennai, Tamil Nadu - 600032",
        "map_link": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d15548.748301548174!2d80.222304!3d13.004921!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a526732f7f9035f%3A0x6a2c9c22e4d023b!2sGuindy%2C%20Chennai%2C%20Tamil%20Nadu!5e0!3m2!1sen!2sin!4v1633512345678!5m2!1sen!2sin"
    },
]

# ---------------- Gmail Function ----------------
def send_email(to_email, subject, body_text, attachments=[]):
    """Handles Gmail authentication and sending emails with attachments."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json','w') as token:
                token.write(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)
        msg = MIMEMultipart()
        msg['to'] = to_email
        msg['subject'] = subject
        msg.attach(MIMEText(body_text))

        for filepath in attachments:
            part = MIMEBase('application', 'octet-stream')
            with open(filepath, 'rb') as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
            msg.attach(part)

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# ---------------- KNN Functions ----------------
def get_donor_dataframe():
    data = []
    donor_ids = []
    for donor_id, info in donors.items():
        d = info['data']
        gender = 0 if d['gender']=="Male" else 1 if d['gender']=="Female" else 2
        occupation = sum([ord(c) for c in d['occupation']]) % 100
        income = int(d['income']) if d['income'].isdigit() else 0
        data.append([gender, occupation, income])
        donor_ids.append(donor_id)
    df = pd.DataFrame(data, index=donor_ids, columns=['gender','occupation','income'])
    return df

def recommend_trusts_for_donor(target_donor_id, n_neighbors=2):
    df = get_donor_dataframe()
    if target_donor_id not in df.index:
        return [t['name'] for t in trusts_chennai]

    knn = NearestNeighbors(n_neighbors=n_neighbors+1, metric='euclidean')
    knn.fit(df.values)
    distances, indices = knn.kneighbors([df.loc[target_donor_id].values])
    similar_donor_ids = [df.index[i] for i in indices[0] if df.index[i] != target_donor_id]

    recommended_trusts = []
    for donor_id in similar_donor_ids:
        # Simplification: Always recommend the first trust in the list for similar donors
        recommended_trusts.append(trusts_chennai[0]['name']) 
    recommended_trusts = list(set(recommended_trusts))
    if not recommended_trusts:
        recommended_trusts = [t['name'] for t in trusts_chennai]
    
    return recommended_trusts

# ---------------- Trust Login/Logout Routes ----------------

@app.route('/trust_login', methods=['GET', 'POST'])
def trust_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in TRUST_CREDENTIALS and TRUST_CREDENTIALS[username]['password'] == password:
            session['trust_logged_in'] = True
            session['trust_username'] = username
            session['trust_name'] = TRUST_CREDENTIALS[username]['name']
            flash(f"Logged in as {session['trust_name']}", 'success')
            return redirect(url_for('about')) # Redirect to the Trust Dashboard
        else:
            error = "Invalid username or password for Trust."
    return render_template('trust_login.html', error=error)

@app.route('/trust_logout')
def trust_logout():
    session.pop('trust_logged_in', None)
    session.pop('trust_username', None)
    session.pop('trust_name', None)
    flash("Successfully logged out of Trust Dashboard.", 'success')
    return redirect(url_for('home'))

# ---------------- Core Routes ----------------

@app.route('/')
def home():
    return render_template("index.html")

# NEW ROUTE: For public Mission/Vision content
@app.route('/mandate')
def mandate():
    return render_template("about_mission.html") 

# ORIGINAL ROUTE: Remains strictly for Trust Dashboard (Expense Submission)
@app.route('/about', methods=['GET', 'POST'])
def about():
    # 1. PROTECTION: Check if a Trust is logged in to access the Dashboard
    if not session.get('trust_logged_in'):
        flash("Access denied. Please log in as a Trust Representative to submit expense reports.", 'error')
        return redirect(url_for('trust_login'))

    # 2. FILE SUBMISSION LOGIC (POST request)
    if request.method == 'POST':
        donor_name = request.form['donor_name']
        donor_email = request.form['donor_email']
        trust_name = request.form['trust_name']
        files = request.files.getlist('photos')
        
        attachments = []
        try:
            if files and any(f.filename for f in files):
                for file in files:
                    if file.filename and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ['jpg', 'jpeg', 'png', 'pdf']:
                        filename = f"{trust_name}_{random.randint(1000, 9999)}_{file.filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)
                        attachments.append(filepath)
                    else:
                        flash('Error: Only JPG, PNG, and PDF files are allowed.', 'error')
                        return redirect(url_for('about'))
            else:
                flash('Please upload at least one expense bill or photo.', 'error')
                return redirect(url_for('about'))

            # Prepare and send email
            subject = f"Expense Report from {trust_name} - Your Donation Impact Proof"
            body = f"""
Dear {donor_name},

Thank you for your generous support. As part of our transparency promise, {trust_name} has provided the attached expense bills/photos detailing how your donation was utilized.

Trust Name: {trust_name}

Sincerely,
The TRUST BRIDGE HEARTS Team
"""
            success = send_email(donor_email, subject, body, attachments=attachments)

            if success:
                flash(f'Expense report successfully sent to {donor_email}! The donor has been notified.', 'success')
            else:
                flash('Error: Failed to send the expense report email. Please check your Gmail API setup.', 'error')
                    
        except Exception as e:
            flash(f'An unexpected error occurred during file processing: {e}', 'error')
        finally:
            # Cleanup temporary files
            for filepath in attachments:
                if os.path.exists(filepath):
                    os.remove(filepath)
                
        return redirect(url_for('about'))

    # 3. RENDER THE DASHBOARD (GET request)
    return render_template("about.html", trusts=trusts_chennai)

@app.route('/contact')
def contact():
    # Define TBH contact info here
    TBH_CONTACT_INFO = {
        "email_support": "support@trustbridgehearts.org",
        "email_admin": "admin@trustbridgehearts.org",
        "phone": "+91-8000000000",
        "address": "Office No. 7, 3rd Floor, Chennai One IT Park, Thoraipakkam, Chennai, Tamil Nadu - 600097",
        "map_link": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3887.8998811804923!2d80.2483838743128!3d12.977461887342937!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3a525d886916a041%3A0xf639a0391d4e0a75!2sChennai%20One%20IT%20SEZ!5e0!3m2!1sen!2sin!4v1633512345678!5m2!1sen!2sin"
    }
    # Pass both trusts data and TBH contact data to the contact page
    return render_template("contact.html", trusts=trusts_chennai, tbh_contact=TBH_CONTACT_INFO)

@app.route('/trusts')
def trusts():
    return render_template("trusts.html", trusts=trusts_chennai)

# ---------------- Trust Profile Route ----------------
@app.route('/trust/<trust_name>')
def trust_profile(trust_name):
    """Displays the detailed profile page for a single trust."""
    trust = next((t for t in trusts_chennai if t['name'] == trust_name), None)
    
    if trust is None:
        flash(f"Trust profile for '{trust_name}' not found.", 'error')
        return redirect(url_for('trusts'))
        
    return render_template('trust_profile.html', trust=trust)

# ---------------- Donor Registration ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name = request.form['name']
        gender = request.form['gender']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        occupation = request.form['occupation']
        income = request.form['income']

        donor_id = f"D{random.randint(1000,9999)}"
        while donor_id in donors:
            donor_id = f"D{random.randint(1000,9999)}"

        # Generate credentials
        username = ''.join(random.choices(string.ascii_letters, k=6))
        password = ''.join(random.choices(string.ascii_letters+string.digits, k=6))

        # Save webcam photo
        photo_data = request.form.get('photo_data')
        photo_path = None
        if photo_data:
            header, encoded = photo_data.split(",", 1)
            decoded = base64.b64decode(encoded)
            os.makedirs('static/photos', exist_ok=True)
            photo_filename = f"{donor_id}.png"
            photo_path = os.path.join('static/photos', photo_filename)
            with open(photo_path, "wb") as f:
                f.write(decoded)
        
        donors[donor_id] = {
            "username": username,
            "password": password,
            "photo": photo_path, 
            "data": {
                "name": name, "gender": gender, "address": address,
                "phone": phone, "email": email, "occupation": occupation,
                "income": income, "id": donor_id 
            },
            "first_login_done": False,
            "donations": []
        }

        with open('donors.json','w') as f:
            json.dump(donors,f)

        # Send email with credentials
        subject = "Your Donor Login Credentials"
        body = f"""
Hello {name},

Thank you for registering at TRUST BRIDGE HEARTS.

Your login credentials are:
Username: {username}
Password: {password}

Please use these credentials to log in for the first time.
"""
        send_email(email, subject, body)
        return redirect(url_for('login'))
    return render_template("register.html")

# ---------------- Donor Login ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']

        for donor_id, info in donors.items():
            if info['username']==username and info['password']==password:
                if not info.get("first_login_done"):
                    donors[donor_id]["first_login_done"] = True
                    with open('donors.json','w') as f:
                        json.dump(donors,f)
                session['donor_id'] = donor_id
                return redirect(url_for('donor_dashboard'))

        error = "Invalid username or password. Check your email for credentials."
    return render_template('login.html', error=error)

# ---------------- Donor Logout ----------------
@app.route('/logout')
def logout():
    session.pop('donor_id', None)
    return redirect(url_for('home'))

# ---------------- Donor Dashboard ----------------
@app.route('/donor_dashboard')
def donor_dashboard():
    donor_id = session.get('donor_id')
    if not donor_id or donor_id not in donors:
        return redirect(url_for('login'))
        
    donor_data = donors[donor_id]['data']
    donations = donors[donor_id].get('donations', [])
    
    # Pass the donor_id explicitly for the photo path fix
    return render_template('donor_dashboard.html', 
                           donor=donor_data, 
                           donations=donations, 
                           donor_id=donor_id) 

# ---------------- Donation ----------------
@app.route('/donate', methods=['GET','POST'])
def donate():
    donor_id = session.get('donor_id')
    if not donor_id or donor_id not in donors:
        return redirect(url_for('login'))

    donor_data = donors[donor_id]['data']
    recommended_trusts = recommend_trusts_for_donor(donor_id)

    if request.method=='POST':
        try:
            trust_name = request.form['trust']
            amount = request.form['amount']

            # Generate UPI QR
            qr_text = f"upi://pay?pa={UPI_ID}&pn={trust_name}&am={amount}&cu=INR"
            qr_img = qrcode.make(qr_text)
            qr_path = os.path.join('static/img', 'upi_qr.png')
            os.makedirs('static/img', exist_ok=True)
            qr_img.save(qr_path)

            # Save donation as PENDING confirmation
            donors[donor_id]['donations'].append({"trust": trust_name, "amount": amount, "status": "pending"})
            with open('donors.json','w') as f:
                json.dump(donors, f)

            # Notify trust by email (optional, can be moved to confirm_upi)
            trust_email = next((t['email'] for t in trusts_chennai if t['name']==trust_name), None)
            if trust_email:
                subject = f"PENDING Donation from {donor_data['name']}"
                body = f"Donor {donor_data['name']} is generating QR code for ₹{amount} to {trust_name}. Awaiting UPI ID confirmation."
                send_email(trust_email, subject, body)

            # SUCCESS PATH
            return render_template("payment_qr.html", qr_path=qr_path, trust=trust_name, amount=amount)

        except Exception as e:
            # FAILURE PATH: Catch any error and return a response (redirect)
            flash(f"An error occurred while processing your donation: {e}", 'error')
            print(f"Donation processing error: {e}") 
            return redirect(url_for('donate')) 

    # GET request handling
    return render_template("donate.html", trusts=trusts_chennai, donor=donor_data, recommended_trusts=recommended_trusts)

# ---------------- UPI Confirmation Route ----------------
@app.route('/confirm_upi', methods=['GET', 'POST'])
def confirm_upi():
    donor_id = session.get('donor_id')
    if not donor_id or donor_id not in donors:
        flash("Please log in to confirm your payment.", 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        upi_id = request.form['upi_id']
        
        # Find the last donation record which is assumed to be the one just paid
        if donors[donor_id]['donations'] and donors[donor_id]['donations'][-1].get('status') == 'pending':
            # Update the last donation record with the UPI ID and mark as confirmed
            donors[donor_id]['donations'][-1]['donor_upi_id'] = upi_id
            donors[donor_id]['donations'][-1]['status'] = 'confirmed'
        else:
             # Fallback: if no pending donation is found, still store the UPI ID
             donors[donor_id]['data']['last_used_upi_id'] = upi_id
        
        # Save the updated donor data
        with open('donors.json','w') as f:
            json.dump(donors, f)

        flash("Payment confirmed! Your UPI ID has been recorded securely for traceability.", 'success')
        return redirect(url_for('donor_dashboard'))

    return render_template('confirm_upi.html')


# ---------------- Emergency storage (added) ----------------
EMERGENCY_JSON = 'emergency.json'
if os.path.exists(EMERGENCY_JSON):
    with open(EMERGENCY_JSON, 'r') as f:
        try:
            emergencies = json.load(f)
        except Exception:
            emergencies = []
else:
    emergencies = []

def save_emergencies():
    with open(EMERGENCY_JSON, 'w') as f:
        json.dump(emergencies, f, indent=2, default=str)

# ---------------- Trust Emergency route (trusts submit emergency) ----------------
@app.route('/trust_emergency', methods=['GET', 'POST'])
def trust_emergency():
    # Trust must be logged in
    if not session.get('trust_logged_in'):
        flash("Login required as Trust.", 'error')
        return redirect(url_for('trust_login'))

    trust_username = session.get('trust_username')
    trust_name = session.get('trust_name')

    if request.method == 'POST':
        # NOTE: per your choice B - trust will enter the 40% required amount directly
        required_40pct_str = request.form.get('required_amount', '').strip()
        purpose = request.form.get('purpose', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()

        if not required_40pct_str:
            flash("Please enter the 40% emergency amount required.", 'error')
            return redirect(url_for('trust_emergency'))

        filtered = ''.join(c for c in required_40pct_str if (c.isdigit() or c == '.'))
        if not filtered:
            flash("Invalid amount provided.", 'error')
            return redirect(url_for('trust_emergency'))

        requested_40pct = float(filtered)
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Create emergency object (include donations list & collected amount)
        emergency = {
            "trust_username": trust_username,
            "trust_name": trust_name,
            "purpose": purpose,
            "contact_phone": contact_phone,
            "requested_40pct": requested_40pct,
            "status": "pending",   # pending / approved / rejected
            "submitted_at": timestamp,
            "notes": "",
            "donations": [],       # list of donation records for this emergency
            "collected": 0.0,
            "total_required": None  # optional (trust didn't supply total, only 40% amount)
        }

        emergencies.append(emergency)
        save_emergencies()

        # notify admin and trust (existing send_email used)
        admin_email = "admin@trustbridgehearts.org"
        trust_email = next((t['email'] for t in trusts_chennai if t['name'] == trust_name), None)

        subject_admin = f"EMERGENCY: {trust_name} requesting immediate support"
        body_admin = f"""
Trust: {trust_name}
Submitted by account: {trust_username}
Purpose: {purpose}
Contact Phone: {contact_phone}
Requested Emergency (40%): ₹{requested_40pct}
Submitted At (UTC): {timestamp}

Please review and take action via the Admin Emergency page.
"""
        send_email(admin_email, subject_admin, body_admin)
        if trust_email:
            send_email(trust_email, f"Copy - {subject_admin}", f"Your emergency request has been received and is pending review by admin.\n\nRequested: ₹{requested_40pct}\n\nThanks,\nTRUST BRIDGE HEARTS")

        # Broadcast short alert to donors (pre-approval notice)
        broadcast_subject = f"Urgent: {trust_name} submitted an emergency request"
        broadcast_body_template = f"""
Dear {{name}},

{trust_name} has submitted an emergency funding request (pending admin approval):

Purpose: {purpose}
Immediate Emergency Request (40% target): ₹{requested_40pct}

You'll be notified when admin approves and the emergency donation page opens.
Thanks,
TRUST BRIDGE HEARTS
"""
        for d_id, d_info in donors.items():
            d_email = d_info.get('data', {}).get('email')
            d_name = d_info.get('data', {}).get('name', 'Friend')
            if d_email:
                try:
                    send_email(d_email, broadcast_subject, broadcast_body_template.format(name=d_name))
                except Exception as e:
                    print(f"Failed broadcast pre-approval to {d_email}: {e}")

        flash(f"Emergency submitted (40% target ₹{requested_40pct}). Admin will review.", "success")
        return redirect(url_for('about'))

    # GET
    return render_template('trust_emergency.html', trust_name=session.get('trust_name'))

# ---------------- Admin: Emergencies list & actions ----------------
@app.route('/admin/emergencies')
def admin_emergencies():
    # protect via admin session; if not logged in redirect to admin dashboard (preserves your current flow)
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    # show all emergencies (latest first)
    reversed_list = list(reversed(emergencies))
    return render_template('admin_emergency.html', emergencies=reversed_list, total_donors=len(donors), base_count=len(emergencies))

@app.route('/admin/emergency_action/<int:orig_index>/<action>', methods=['POST','GET'])
def admin_emergency_action(orig_index, action):
    # protect admin
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if orig_index < 0 or orig_index >= len(emergencies):
        flash("Invalid emergency index.", "error")
        return redirect(url_for('admin_emergencies'))

    if action not in ('approve','reject'):
        flash("Invalid action.", "error")
        return redirect(url_for('admin_emergencies'))

    # update status
    emergencies[orig_index]['status'] = 'approved' if action == 'approve' else 'rejected'
    emergencies[orig_index]['reviewed_at'] = datetime.utcnow().isoformat() + 'Z'
    save_emergencies()

    trust_name = emergencies[orig_index]['trust_name']
    requested_40pct = emergencies[orig_index]['requested_40pct']
    purpose = emergencies[orig_index].get('purpose','')
    contact_phone = emergencies[orig_index].get('contact_phone','')
    trust_email = next((t['email'] for t in trusts_chennai if t['name']==trust_name), None)
    admin_email = "admin@trustbridgehearts.org"

    if action == 'approve':
        # create link to donate_emergency route
        try:
            external_link = url_for('donate_emergency', trust_name=trust_name, index=orig_index, _external=True)
        except Exception:
            external_link = f"/donate_emergency/{trust_name}/{orig_index}"

        subject_to_donors = f"Emergency Approved: {trust_name} needs ₹{requested_40pct} (Donate now)"
        body_to_donors_template = f"""
Dear {{name}},

Good news — admin has approved an emergency request from {trust_name}.

Purpose: {purpose}
Immediate Emergency Target (40%): ₹{requested_40pct}

Donate now via this dedicated emergency page:
{external_link}

Thank you for your support,
TRUST BRIDGE HEARTS
"""
        # send to all donors
        for d_id, d_info in donors.items():
            d_email = d_info.get('data',{}).get('email')
            d_name = d_info.get('data',{}).get('name','Friend')
            if d_email:
                try:
                    send_email(d_email, subject_to_donors, body_to_donors_template.format(name=d_name))
                except Exception as e:
                    print(f"Failed sending approved emergency broadcast to {d_email}: {e}")

        # notify trust
        if trust_email:
            send_email(trust_email, f"Your emergency was approved", f"Your emergency request for ₹{requested_40pct} was approved by admin. Donors have been notified and can donate at {external_link}")

    else:
        # Rejected: notify trust
        if trust_email:
            send_email(trust_email, f"Your emergency request was rejected", f"Your emergency request for {trust_name} has been reviewed and rejected. Please contact admin for details.")

    flash(f"Emergency #{orig_index} {action}ed.", "success")
    return redirect(url_for('admin_emergencies'))

# ---------------- Donation flow for a specific emergency (separate page) ----------------
@app.route('/donate_emergency/<trust_name>/<int:index>', methods=['GET', 'POST'])
def donate_emergency(trust_name, index):
    # Validate index and trust match
    if index < 0 or index >= len(emergencies):
        flash("Invalid emergency reference.", "error")
        return redirect(url_for('home'))

    em = emergencies[index]
    if em['trust_name'] != trust_name:
        flash("Emergency not found.", "error")
        return redirect(url_for('home'))

    if em.get('status') != 'approved':
        flash("This emergency is not open for donations yet.", "error")
        return redirect(url_for('home'))

    # compute remaining cap = requested_40pct - collected
    target = float(em.get('requested_40pct', 0.0))
    collected = float(em.get('collected', 0.0))
    remaining = round(max(0.0, target - collected), 2)

    if request.method == 'POST':
        donor_id = session.get('donor_id')
        if not donor_id:
            flash("Please login as donor to donate to an emergency.", "error")
            return redirect(url_for('login'))

        amount_str = request.form.get('amount','').strip()
        filtered = ''.join(c for c in amount_str if (c.isdigit() or c == '.'))
        if not filtered:
            flash("Invalid donation amount.", "error")
            return redirect(url_for('donate_emergency', trust_name=trust_name, index=index))

        amount = float(filtered)
        if amount <= 0:
            flash("Donation amount must be positive.", "error")
            return redirect(url_for('donate_emergency', trust_name=trust_name, index=index))

        if amount > remaining:
            flash(f"Donation exceeds remaining emergency capacity. Remaining allowed: ₹{remaining}", "error")
            return redirect(url_for('donate_emergency', trust_name=trust_name, index=index))

        # Generate UPI QR for this emergency
        qr_text = f"upi://pay?pa={UPI_ID}&pn={trust_name}&am={amount}&cu=INR"
        qr_img = qrcode.make(qr_text)
        os.makedirs('static/img', exist_ok=True)
        qr_filename = f"emergency_{index}_qr_{random.randint(1000,9999)}.png"
        qr_path = os.path.join('static/img', qr_filename)
        qr_img.save(qr_path)

        # Save donation as pending in emergency record
        donation_record = {
            "donor_id": donor_id,
            "donor_email": donors.get(donor_id, {}).get('data', {}).get('email'),
            "amount": amount,
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat() + 'Z'
        }
        em['donations'].append(donation_record)
        em['collected'] = round(float(em.get('collected', 0.0)) + amount, 2)
        save_emergencies()

        # Notify admin/trust optionally
        trust_email = next((t['email'] for t in trusts_chennai if t['name'] == trust_name), None)
        admin_email = "admin@trustbridgehearts.org"
        subject = f"Emergency donation PENDING: {trust_name} ₹{amount}"
        body = f"Donor {donors.get(donor_id, {}).get('data', {}).get('name','Unknown')} has initiated a donation of ₹{amount} for emergency: {em.get('purpose','')}. Please await confirmation."
        send_email(admin_email, subject, body)
        if trust_email:
            send_email(trust_email, subject, f"A donor initiated ₹{amount} for your emergency. Check admin dashboard for details.")

        # Show QR so donor can pay externally via UPI
        return render_template('payment_qr.html', qr_path=qr_path, trust=trust_name, amount=amount)

    # GET: render donation page with remaining info
    return render_template('donate_emergency.html',
                           trust_name=trust_name,
                           index=index,
                           emergency=em,
                           remaining=remaining,
                           target=target,
                           collected=collected)

# ---------------- Admin Dashboard ----------------
@app.route('/admin_dashboard')
def admin_dashboard():
    donor_list = []
    for donor_id, info in donors.items():
        d = info['data']
        donor_list.append({
            "id": donor_id,
            "name": d['name'],
            "gender": d['gender'],
            "phone": d['phone'],
            "email": d['email'],
            "occupation": d['occupation'],
            "income": d['income']
        })
    return render_template("dashboard.html", donors=donor_list)

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

if __name__=='__main__':
    app.run(debug=True)
