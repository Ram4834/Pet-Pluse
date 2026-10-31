import os, re, secrets, time
from datetime import date, timedelta
from markupsafe import Markup
from functools import wraps
import mysql.connector
from flask import (Flask, request, session, redirect, url_for, render_template,
                   flash, abort)
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
KEY = ".secret_key"
if not os.path.exists(KEY):
    open(KEY, "w").write(secrets.token_hex(32))
app.secret_key = os.environ.get("SECRET_KEY") or open(KEY).read()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("PRODUCTION")),
                  PERMANENT_SESSION_LIFETIME=3600)

SPECIES = ["Cow", "Buffalo", "Goat", "Sheep", "Dog", "Cat", "Horse", "Other"]
DAIRY = ["Cow", "Buffalo", "Goat"]
ICONS = {"Cow": "🐄", "Buffalo": "🐃", "Goat": "🐐", "Sheep": "🐑", "Dog": "🐶", "Cat": "🐱", "Horse": "🐴", "Other": "🐾"}
app.jinja_env.globals["IC"] = ICONS
EN = {"low_alert": "{name}: latest milk {last} L is {pct}% below the 7-day average ({avg} L). The animal may be unwell - please arrange a health check."}
def _p(s):
    return dict(x.split("|") for x in s.strip().split("\n"))
TR = {
"hi": _p("""PetPulse - Livestock & Pet Health|पेटपल्स - पशुधन और पालतू स्वास्थ्य
Dashboard|डैशबोर्ड
My Animals|मेरे पशु
My animals|मेरे पशु
Milk Yield|दूध उत्पादन
Health|स्वास्थ्य
Vaccinations|टीकाकरण
Vets|पशु चिकित्सक
Logout|लॉगआउट
Login|लॉगिन
Email or Phone number|ईमेल या फ़ोन नंबर
Password|पासवर्ड
New user?|नए उपयोगकर्ता?
Create account|खाता बनाएँ
Register|पंजीकरण करें
Already registered?|पहले से पंजीकृत हैं?
Full name|पूरा नाम
Email|ईमेल
Phone (10 digits)|फ़ोन (10 अंक)
Password (min 8 characters)|पासवर्ड (कम से कम 8 अक्षर)
Confirm password|पासवर्ड की पुष्टि करें
Welcome|स्वागत है
Animals registered|पंजीकृत पशु
Milk in last 7 days|पिछले 7 दिनों का दूध
Vaccinations due in 30 days|30 दिनों में टीकाकरण देय
Health alerts|स्वास्थ्य चेतावनी
All animals are producing normally.|सभी पशु सामान्य दूध दे रहे हैं।
Milk trend (last 14 days)|दूध की प्रवृत्ति (पिछले 14 दिन)
Vaccination reminders|टीकाकरण अनुस्मारक
No vaccinations due.|कोई टीकाकरण देय नहीं।
Recent health records|हाल के स्वास्थ्य रिकॉर्ड
No records yet.|अभी कोई रिकॉर्ड नहीं।
overdue|विलंबित
days|दिन
Add animal|पशु जोड़ें
Name|नाम
Species|प्रजाति
Breed|नस्ल
Gender|लिंग
Date of birth|जन्म तिथि
Female|मादा
Male|नर
Age (yrs)|आयु (वर्ष)
Add|जोड़ें
Delete|हटाएँ
No animals yet.|अभी कोई पशु नहीं।
Please add an animal first.|कृपया पहले एक पशु जोड़ें।
Add milk log (Cow / Buffalo / Goat)|दूध रिकॉर्ड जोड़ें (गाय / भैंस / बकरी)
Animal|पशु
Date|तारीख
Morning yield (L)|सुबह का दूध (लीटर)
Evening yield (L)|शाम का दूध (लीटर)
Save|सहेजें
Milk records|दूध रिकॉर्ड
Morning|सुबह
Evening|शाम
Total|कुल
No records.|कोई रिकॉर्ड नहीं।
Add health record|स्वास्थ्य रिकॉर्ड जोड़ें
Veterinarian|पशु चिकित्सक
- not specified -|- निर्दिष्ट नहीं -
Visit date|भेंट की तारीख
Diagnosis|निदान
Prescription|नुस्खा
Health history|स्वास्थ्य इतिहास
Vet|चिकित्सक
Add vaccination|टीकाकरण जोड़ें
Vaccine name|टीके का नाम
Dose date|खुराक की तारीख
Next due date|अगली देय तारीख
Given|दिया गया
Next due|अगली तारीख
Overdue|विलंबित
Due soon|जल्द देय
Veterinarians|पशु चिकित्सक
Find a vet near you|अपने पास का पशु चिकित्सक खोजें
City or pincode|शहर या पिनकोड
Search|खोजें
Call|कॉल करें
Map|नक्शा
Add a veterinarian|पशु चिकित्सक जोड़ें
Specialization|विशेषज्ञता
Phone|फ़ोन
Street|सड़क
City|शहर
Pincode|पिनकोड
Address|पता
No vets found.|कोई चिकित्सक नहीं मिला।
Today|आज
14 days ago|14 दिन पहले
Pet added.|पशु जोड़ा गया।
Milk log saved.|दूध रिकॉर्ड सहेजा गया।
Health record saved.|स्वास्थ्य रिकॉर्ड सहेजा गया।
Vaccination saved.|टीकाकरण सहेजा गया।
Deleted.|हटा दिया गया।
Veterinarian added.|चिकित्सक जोड़ा गया।
Invalid email/phone or password.|ईमेल/फ़ोन या पासवर्ड गलत है।
Account created. Please log in.|खाता बन गया। कृपया लॉगिन करें।
low_alert|{name}: ताज़ा दूध {last} लीटर, 7 दिन के औसत ({avg} लीटर) से {pct}% कम है। पशु बीमार हो सकता है - कृपया जाँच कराएँ।"""),
"mr": _p("""PetPulse - Livestock & Pet Health|पेटपल्स - पशुधन आणि पाळीव प्राणी आरोग्य
Dashboard|डॅशबोर्ड
My Animals|माझे प्राणी
My animals|माझे प्राणी
Milk Yield|दूध उत्पादन
Health|आरोग्य
Vaccinations|लसीकरण
Vets|पशुवैद्य
Logout|लॉगआउट
Login|लॉगिन
Email or Phone number|ईमेल किंवा फोन नंबर
Password|पासवर्ड
New user?|नवीन वापरकर्ता?
Create account|खाते तयार करा
Register|नोंदणी करा
Already registered?|आधीच नोंदणी केली आहे?
Full name|पूर्ण नाव
Email|ईमेल
Phone (10 digits)|फोन (10 अंक)
Password (min 8 characters)|पासवर्ड (किमान 8 अक्षरे)
Confirm password|पासवर्डची पुष्टी करा
Welcome|स्वागत आहे
Animals registered|नोंदणीकृत प्राणी
Milk in last 7 days|गेल्या 7 दिवसांचे दूध
Vaccinations due in 30 days|30 दिवसांत लसीकरण देय
Health alerts|आरोग्य इशारे
All animals are producing normally.|सर्व प्राणी नेहमीप्रमाणे दूध देत आहेत.
Milk trend (last 14 days)|दूध प्रवृत्ती (गेले 14 दिवस)
Vaccination reminders|लसीकरण स्मरणपत्रे
No vaccinations due.|कोणतेही लसीकरण देय नाही.
Recent health records|अलीकडील आरोग्य नोंदी
No records yet.|अजून नोंदी नाहीत.
overdue|उशीर झाला
days|दिवस
Add animal|प्राणी जोडा
Name|नाव
Species|प्रजाती
Breed|जात
Gender|लिंग
Date of birth|जन्मतारीख
Female|मादी
Male|नर
Age (yrs)|वय (वर्षे)
Add|जोडा
Delete|हटवा
No animals yet.|अजून प्राणी नाहीत.
Please add an animal first.|कृपया आधी एक प्राणी जोडा.
Add milk log (Cow / Buffalo / Goat)|दूध नोंद जोडा (गाय / म्हैस / शेळी)
Animal|प्राणी
Date|तारीख
Morning yield (L)|सकाळचे दूध (लिटर)
Evening yield (L)|संध्याकाळचे दूध (लिटर)
Save|जतन करा
Milk records|दूध नोंदी
Morning|सकाळ
Evening|संध्याकाळ
Total|एकूण
No records.|नोंदी नाहीत.
Add health record|आरोग्य नोंद जोडा
Veterinarian|पशुवैद्य
- not specified -|- नमूद नाही -
Visit date|भेटीची तारीख
Diagnosis|निदान
Prescription|औषधोपचार
Health history|आरोग्य इतिहास
Vet|वैद्य
Add vaccination|लसीकरण जोडा
Vaccine name|लसीचे नाव
Dose date|डोसची तारीख
Next due date|पुढील देय तारीख
Given|दिले
Next due|पुढील तारीख
Overdue|उशीर
Due soon|लवकरच देय
Veterinarians|पशुवैद्य
Find a vet near you|जवळचा पशुवैद्य शोधा
City or pincode|शहर किंवा पिनकोड
Search|शोधा
Call|कॉल करा
Map|नकाशा
Add a veterinarian|पशुवैद्य जोडा
Specialization|विशेषज्ञता
Phone|फोन
Street|रस्ता
City|शहर
Pincode|पिनकोड
Address|पत्ता
No vets found.|पशुवैद्य सापडले नाहीत.
Today|आज
14 days ago|14 दिवसांपूर्वी
Pet added.|प्राणी जोडला.
Milk log saved.|दूध नोंद जतन केली.
Health record saved.|आरोग्य नोंद जतन केली.
Vaccination saved.|लसीकरण जतन केले.
Deleted.|हटवले.
Veterinarian added.|पशुवैद्य जोडला.
Invalid email/phone or password.|ईमेल/फोन किंवा पासवर्ड चुकीचा आहे.
Account created. Please log in.|खाते तयार झाले. कृपया लॉगिन करा.
low_alert|{name}: ताजे दूध {last} लिटर, 7 दिवसांच्या सरासरीपेक्षा ({avg} लिटर) {pct}% कमी आहे. प्राणी आजारी असू शकतो - कृपया तपासणी करून घ्या."""),
}

TR["hi"]["hint"] = "ट्रेंड लाइन देखने के लिए कम से कम 2 दिन का दूध रिकॉर्ड जोड़ें।"
TR["mr"]["hint"] = "ट्रेंड रेषा पाहण्यासाठी किमान 2 दिवसांची दूध नोंद जोडा."
EN["hint"] = "Add milk logs for at least 2 days to see the trend line."

def _(s):
    return TR.get(session.get("lang"), {}).get(s) or EN.get(s, s)
app.jinja_env.globals["_"] = _

def chart(pts, low=False):
    W, H, L, RT, T, B, N = 440, 170, 30, 8, 22, 26, 15
    slot = (W - L - RT) / N; bw = slot * 0.62; ch = H - T - B
    vals = dict(pts); mx = max(vals.values()) or 1; avg = sum(vals.values()) / len(vals); last = max(vals)
    o = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:520px"><defs>'
         '<linearGradient id="gG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#81c784"/><stop offset="1" stop-color="#2e7d32"/></linearGradient>'
         '<linearGradient id="gR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ef5350"/><stop offset="1" stop-color="#b71c1c"/></linearGradient></defs>']
    for g in (0, .5, 1):
        y = T + ch * (1 - g)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-RT}" y2="{y:.1f}" stroke="#e6e6e6"/><text x="{L-4}" y="{y+3:.1f}" font-size="8" text-anchor="end" fill="#888">{mx*g:.0f}</text>')
    for i in range(N):
        x = L + i * slot + (slot - bw) / 2
        d = date.today() - timedelta(days=14 - i)
        o.append(f'<text x="{x+bw/2:.1f}" y="{H-12}" font-size="8" text-anchor="middle" fill="#777">{d.day}</text>')
        v = vals.get(i)
        if v is None: continue
        h = max(v / mx * ch, 2); y = T + ch - h
        fill = "url(#gR)" if (low and i == last) else "url(#gG)"
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{fill}"><title>{d}: {v:.2f} L</title></rect>'
                 f'<text x="{x+bw/2:.1f}" y="{y-3:.1f}" font-size="8" font-weight="bold" text-anchor="middle" fill="{"#b71c1c" if (low and i == last) else "#1b5e20"}">{v:.1f}</text>')
    ya = T + ch * (1 - avg / mx)
    o.append(f'<line x1="{L}" y1="{ya:.1f}" x2="{W-RT}" y2="{ya:.1f}" stroke="#fb8c00" stroke-width="1.5" stroke-dasharray="5 3"/>'
             f'<text x="{L+2}" y="{ya-3:.1f}" font-size="8" fill="#e65100">avg {avg:.1f} L</text>'
             f'<text x="{L}" y="{H-1}" font-size="8" fill="#777">{_("14 days ago")}</text><text x="{W-RT}" y="{H-1}" font-size="8" text-anchor="end" fill="#777">{_("Today")}</text></svg>')
    return Markup("".join(o))

def milk_stats(uid):
    rows = q("""SELECT p.Pet_ID,p.Pet_Name,p.Species,m.Log_Date,SUM(m.Total_Yield) t FROM MilkYieldLog m JOIN Pet p
        ON p.Pet_ID=m.Pet_ID WHERE p.User_ID=%s AND m.Log_Date>=DATE_SUB(CURDATE(),INTERVAL 14 DAY)
        GROUP BY p.Pet_ID,p.Pet_Name,p.Species,m.Log_Date ORDER BY p.Pet_ID,m.Log_Date""", (uid,))
    by = {}
    for r in rows: by.setdefault(r["Pet_ID"], []).append(r)
    series, alerts, start = [], [], date.today() - timedelta(days=14)
    for rs in by.values():
        pts = [((r["Log_Date"] - start).days, float(r["t"])) for r in rs]
        ld, lv = rs[-1]["Log_Date"], float(rs[-1]["t"]); low = False
        prev = [float(r["t"]) for r in rs[:-1] if 0 < (ld - r["Log_Date"]).days <= 7]
        if len(prev) >= 2 and (date.today() - ld).days <= 3:
            avg = sum(prev) / len(prev)
            if avg > 0 and lv < 0.8 * avg:
                low = True
                alerts.append(_("low_alert").format(name=rs[0]["Pet_Name"], last=round(lv, 2), avg=round(avg, 2), pct=round((1 - lv / avg) * 100)))
        series.append({"name": rs[0]["Pet_Name"], "icon": ICONS.get(rs[0]["Species"], "🐾"), "n": len(rs), "svg": chart(pts, low)})
    return series, alerts


def db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "petplusedb"))

def q(sql, args=(), one=False, commit=False):
    con = db(); cur = con.cursor(dictionary=True)
    try:
        cur.execute(sql, args)
        if commit:
            con.commit(); return cur.lastrowid
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        cur.close(); con.close()

# ---------- security helpers ----------
@app.before_request
def csrf():
    if "t" not in session:
        session["t"] = secrets.token_hex(16)
    if request.method == "POST" and not secrets.compare_digest(
            request.form.get("t", ""), session["t"]):
        abort(400)
app.jinja_env.globals["T"] = lambda: session.get("t", "")

@app.after_request
def headers(r):
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Cache-Control"] = "no-store"
    return r

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

def norm(s):
    s = (s or "").strip()
    return s.lower() if "@" in s else re.sub(r"\D", "", s)[-10:]

FAILS = {}
def blocked(key):
    FAILS[key] = [t for t in FAILS.get(key, []) if time.time() - t < 600]
    return len(FAILS[key]) >= 5

def verify(u, pw):
    h = u["Password"] or ""
    if h.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(h, pw)
    if secrets.compare_digest(h, pw):  # old plain-text password: upgrade it
        q("UPDATE Users SET Password=%s WHERE UserID=%s",
          (generate_password_hash(pw), u["UserID"]), commit=True)
        return True
    return False

def own_pet(pid):
    p = q("SELECT * FROM Pet WHERE Pet_ID=%s AND User_ID=%s", (pid, session["uid"]), one=True)
    if not p: abort(404)
    return p

def pets_of(user, dairy=False):
    sql = "SELECT Pet_ID, Pet_Name, Species FROM Pet WHERE User_ID=%s"
    a = [user]
    if dairy:
        sql += " AND Species IN (%s,%s,%s)"; a += DAIRY
    return q(sql + " ORDER BY Pet_Name", a)

def dt(s):
    try: return date.fromisoformat(s)
    except Exception: return None

# ---------- auth ----------
@app.route("/")
def home():
    return redirect(url_for("dashboard" if "uid" in session else "login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name, email, phone = f["name"].strip(), norm(f["email"]), norm(f["phone"])
        pw = f["password"]
        if not name or "@" not in email or len(phone) != 10:
            flash(_("Enter a valid name, email and 10-digit phone number."))
        elif len(pw) < 8 or pw != f["confirm"]:
            flash(_("Password must be at least 8 characters and both entries must match."))
        elif q("SELECT 1 FROM Users WHERE LOWER(Email)=%s OR Phone=%s", (email, phone), one=True):
            flash(_("An account with this email or phone already exists."))
        else:
            q("INSERT INTO Users (Name, Email, Phone, Password) VALUES (%s,%s,%s,%s)",
              (name, email, phone, generate_password_hash(pw)), commit=True)
            flash(_("Account created. Please log in."))
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident, pw = norm(request.form["ident"]), request.form["password"]
        key = ident + request.remote_addr
        if blocked(key):
            flash(_("Too many failed attempts. Try again after 10 minutes."))
        else:
            for u in q("SELECT * FROM Users WHERE LOWER(Email)=%s OR Phone=%s", (ident, ident)):
                if verify(u, pw):
                    lg = session.get("lang"); session.clear(); session.permanent = True
                    session.update(uid=u["UserID"], name=u["Name"], t=secrets.token_hex(16), lang=lg)
                    return redirect(url_for("dashboard"))
            FAILS.setdefault(key, []).append(time.time())
            flash(_("Invalid email/phone or password."))
    return render_template("login.html")

@app.route("/lang/<code>")
def lang(code):
    session["lang"] = code if code in TR else "en"
    ref = request.referrer or ""
    return redirect(ref if ref.startswith(request.host_url) else url_for("home"))

@app.route("/logout", methods=["POST"])
def logout():
    session.clear(); return redirect(url_for("login"))

# ---------- pages ----------
@app.route("/dashboard")
@login_required
def dashboard():
    u = session["uid"]
    n = q("SELECT COUNT(*) n FROM Pet WHERE User_ID=%s", (u,), one=True)["n"]
    milk = q("""SELECT COALESCE(SUM(m.Total_Yield),0) s FROM MilkYieldLog m JOIN Pet p
        ON p.Pet_ID=m.Pet_ID WHERE p.User_ID=%s AND m.Log_Date>=DATE_SUB(CURDATE(),INTERVAL 7 DAY)""", (u,), one=True)["s"]
    due = q("""SELECT p.Pet_Name,p.Species,v.Vaccine_Name,v.Next_Due_Date,DATEDIFF(v.Next_Due_Date,CURDATE()) d
        FROM Vaccinations v JOIN Pet p ON p.Pet_ID=v.Pet_ID WHERE p.User_ID=%s
        AND v.Next_Due_Date<=DATE_ADD(CURDATE(),INTERVAL 30 DAY) ORDER BY v.Next_Due_Date""", (u,))
    rec = q("""SELECT p.Pet_Name,p.Species,h.Visit_Date,h.Diagnosis FROM HealthRecords h JOIN Pet p
        ON p.Pet_ID=h.Pet_ID WHERE p.User_ID=%s ORDER BY h.Visit_Date DESC LIMIT 5""", (u,))
    series, alerts = milk_stats(u)
    try:
        deliv = q("""SELECT p.Pet_Name,p.Species,b.Expected_Delivery,DATEDIFF(b.Expected_Delivery,CURDATE()) d FROM Breeding b
            JOIN Pet p ON p.Pet_ID=b.Pet_ID WHERE p.User_ID=%s AND b.Status='Pregnant'
            AND b.Expected_Delivery<=DATE_ADD(CURDATE(),INTERVAL 30 DAY) ORDER BY b.Expected_Delivery""", (u,))
    except Exception:
        deliv = []
    return render_template("dashboard.html", n=n, milk=milk, due=due, rec=rec, series=series, alerts=alerts, deliv=deliv)

@app.route("/pets", methods=["GET", "POST"])
@login_required
def pets():
    u = session["uid"]
    if request.method == "POST":
        f = request.form
        if not f["name"].strip() or f["species"] not in SPECIES or f["gender"] not in ("Male", "Female"):
            flash(_("Please fill the pet details correctly."))
        else:
            q("INSERT INTO Pet (User_ID,Pet_Name,Species,Breed,Gender,DOB) VALUES (%s,%s,%s,%s,%s,%s)",
              (u, f["name"].strip(), f["species"], f["breed"].strip() or None, f["gender"], dt(f["dob"])), commit=True)
            flash(_("Pet added."))
        return redirect(url_for("pets"))
    rows = q("""SELECT *, TIMESTAMPDIFF(YEAR,DOB,CURDATE()) Age FROM Pet WHERE User_ID=%s
        ORDER BY Pet_Name""", (u,))
    return render_template("pets.html", rows=rows, species=SPECIES)

@app.route("/milk", methods=["GET", "POST"])
@login_required
def milk():
    u = session["uid"]
    if request.method == "POST":
        f = request.form
        own_pet(f["pet"]); d = dt(f["date"])
        try:
            m, e = float(f["morning"]), float(f["evening"])
            ok = d and 0 <= m <= 100 and 0 <= e <= 100
        except ValueError:
            ok = False
        if ok:
            q("INSERT INTO MilkYieldLog (Pet_ID,Log_Date,Morning_Yield,Evening_Yield) VALUES (%s,%s,%s,%s)",
              (f["pet"], d, m, e), commit=True); flash(_("Milk log saved."))
        else:
            flash(_("Enter a valid date and yield (0-100 litres)."))
        return redirect(url_for("milk"))
    rows = q("""SELECT m.*,p.Pet_Name,p.Species FROM MilkYieldLog m JOIN Pet p ON p.Pet_ID=m.Pet_ID
        WHERE p.User_ID=%s ORDER BY m.Log_Date DESC, m.Log_ID DESC LIMIT 60""", (u,))
    series, alerts = milk_stats(u)
    return render_template("milk.html", rows=rows, pets=pets_of(u, True), today=date.today(), series=series, alerts=alerts)

@app.route("/health", methods=["GET", "POST"])
@login_required
def health():
    u = session["uid"]
    if request.method == "POST":
        f = request.form
        own_pet(f["pet"]); d = dt(f["date"])
        vet = f["vet"] or None
        if d and f["diagnosis"].strip():
            q("""INSERT INTO HealthRecords (Pet_ID,Vet_ID,Visit_Date,Diagnosis,Prescription)
                VALUES (%s,%s,%s,%s,%s)""", (f["pet"], vet, d, f["diagnosis"].strip(),
                f["prescription"].strip() or None), commit=True); flash(_("Health record saved."))
        else:
            flash(_("Date and diagnosis are required."))
        return redirect(url_for("health"))
    rows = q("""SELECT h.*,p.Pet_Name,p.Species,v.Vet_Name FROM HealthRecords h JOIN Pet p ON p.Pet_ID=h.Pet_ID
        LEFT JOIN Veterinarians v ON v.Vet_ID=h.Vet_ID WHERE p.User_ID=%s
        ORDER BY h.Visit_Date DESC""", (u,))
    return render_template("health.html", rows=rows, pets=pets_of(u), today=date.today(),
                           vets=q("SELECT Vet_ID,Vet_Name,Specialization FROM Veterinarians ORDER BY Vet_Name"))

@app.route("/vaccinations", methods=["GET", "POST"])
@login_required
def vaccinations():
    u = session["uid"]
    if request.method == "POST":
        f = request.form
        own_pet(f["pet"]); d, nd = dt(f["date"]), dt(f["next"])
        if d and f["vaccine"].strip():
            q("INSERT INTO Vaccinations (Pet_ID,Vaccine_Name,Dose_Date,Next_Due_Date) VALUES (%s,%s,%s,%s)",
              (f["pet"], f["vaccine"].strip(), d, nd), commit=True); flash(_("Vaccination saved."))
        else:
            flash(_("Vaccine name and dose date are required."))
        return redirect(url_for("vaccinations"))
    rows = q("""SELECT v.*,p.Pet_Name,p.Species,DATEDIFF(v.Next_Due_Date,CURDATE()) d FROM Vaccinations v
        JOIN Pet p ON p.Pet_ID=v.Pet_ID WHERE p.User_ID=%s ORDER BY v.Next_Due_Date""", (u,))
    return render_template("vaccinations.html", rows=rows, pets=pets_of(u), today=date.today())

@app.route("/vets", methods=["GET", "POST"])
@login_required
def vets():
    if request.method == "POST":
        f = request.form; ph = norm(f["phone"])
        if f["name"].strip() and ph and f["city"].strip():
            q("INSERT INTO Veterinarians (Vet_Name,Specialization,Phone,Street,City,Pincode) VALUES (%s,%s,%s,%s,%s,%s)",
              (f["name"].strip(), f["spec"].strip() or None, ph, f["street"].strip() or None, f["city"].strip(),
               re.sub(r"\D", "", f["pin"])[:6] or None), commit=True)
            flash(_("Veterinarian added."))
        else:
            flash("Name, phone and city are required.")
        return redirect(url_for("vets"))
    qs = request.args.get("q", "").strip(); like = f"%{qs}%"
    if qs:
        rows = q("""SELECT * FROM Veterinarians WHERE City LIKE %s OR Pincode LIKE %s OR Specialization LIKE %s OR Vet_Name LIKE %s
            ORDER BY (Pincode=%s OR City=%s) DESC, City, Vet_Name""", (like, like, like, like, qs, qs))
    else:
        rows = q("SELECT * FROM Veterinarians ORDER BY City, Vet_Name")
    return render_template("vets.html", rows=rows, qs=qs)

DEL = {"breeding": ("Breeding", "Breeding_ID", "breeding"), "milk": ("MilkYieldLog", "Log_ID", "milk"), "health": ("HealthRecords", "Record_ID", "health"),
       "vaccination": ("Vaccinations", "Vaccination_ID", "vaccinations")}

@app.route("/delete/<kind>/<int:rid>", methods=["POST"])
@login_required
def delete(kind, rid):
    if kind == "pet":
        own_pet(rid)
        con = db(); cur = con.cursor()
        for t in ("MilkYieldLog", "HealthRecords", "Vaccinations", "Breeding"):
            cur.execute(f"DELETE FROM {t} WHERE Pet_ID=%s", (rid,))
        cur.execute("DELETE FROM Pet WHERE Pet_ID=%s AND User_ID=%s", (rid, session["uid"]))
        con.commit(); cur.close(); con.close()
        flash(_("Pet and its records deleted.")); return redirect(url_for("pets"))
    if kind not in DEL: abort(404)
    t, k, back = DEL[kind]
    q(f"DELETE x FROM {t} x JOIN Pet p ON p.Pet_ID=x.Pet_ID WHERE x.{k}=%s AND p.User_ID=%s",
      (rid, session["uid"]), commit=True)
    flash(_("Deleted.")); return redirect(url_for(back))

# ---------- v4: edit, breeding, symptom checker ----------
def _t3(block):
    for line in block.strip().split("\n"):
        k, h, m = line.split("|")
        TR["hi"][k] = h; TR["mr"][k] = m
_t3("""Edit|संपादित करें|संपादित करा
Cancel|रद्द करें|रद्द करा
Please check the values.|कृपया मान जाँचें।|कृपया मूल्ये तपासा.
Updated.|अपडेट किया गया।|अद्यतनित केले.
Breeding|प्रजनन|प्रजनन
Symptoms|लक्षण|लक्षणे
Add breeding record|प्रजनन रिकॉर्ड जोड़ें|प्रजनन नोंद जोडा
Breeding date|प्रजनन की तारीख|प्रजनन तारीख
Method|तरीका|पद्धत
Natural|प्राकृतिक|नैसर्गिक
Artificial insemination|कृत्रिम गर्भाधान|कृत्रिम रेतन
Notes|टिप्पणी|टिपा
Expected delivery|अपेक्षित प्रसव|अपेक्षित प्रसूती
Days left|शेष दिन|उरलेले दिवस
Status|स्थिति|स्थिती
Pregnant|गर्भवती|गाभण
Delivered|प्रसव हुआ|प्रसूत झाली
Not pregnant|गर्भवती नहीं|गाभण नाही
Breeding records|प्रजनन रिकॉर्ड|प्रजनन नोंदी
Upcoming deliveries|आगामी प्रसव|येणारी प्रसूती
No upcoming deliveries.|कोई आगामी प्रसव नहीं।|कोणतीही प्रसूती नियोजित नाही.
No female animals found. Add one in My Animals first.|कोई मादा पशु नहीं मिली। पहले मेरे पशु में जोड़ें।|मादी प्राणी सापडला नाही. आधी माझे प्राणी मध्ये जोडा.
Breeding record saved.|प्रजनन रिकॉर्ड सहेजा गया।|प्रजनन नोंद जतन केली.
Symptom Checker|लक्षण जाँचकर्ता|लक्षण तपासणी
Select the animal and the symptoms you see.|पशु का प्रकार और दिख रहे लक्षण चुनें।|प्राण्याचा प्रकार आणि दिसणारी लक्षणे निवडा.
Check|जाँचें|तपासा
Possible conditions|संभावित बीमारियाँ|संभाव्य आजार
Match|मेल|जुळणी
What to do|क्या करें|काय करावे
Call a vet now|अभी पशु चिकित्सक को बुलाएँ|आत्ताच पशुवैद्याला बोलवा
Select at least one symptom.|कम से कम एक लक्षण चुनें।|किमान एक लक्षण निवडा.
No matching condition found. If the animal looks unwell, please consult a vet.|कोई मेल खाती बीमारी नहीं मिली। पशु बीमार लगे तो चिकित्सक से मिलें।|जुळणारा आजार सापडला नाही. प्राणी आजारी वाटल्यास पशुवैद्याला दाखवा.
This is only guidance, not a diagnosis. Always consult a veterinarian.|यह केवल मार्गदर्शन है, निदान नहीं। हमेशा पशु चिकित्सक से सलाह लें।|हे फक्त मार्गदर्शन आहे, निदान नाही. नेहमी पशुवैद्याचा सल्ला घ्या.
Find a vet|चिकित्सक खोजें|पशुवैद्य शोधा
Livestock (cow, buffalo, goat, sheep)|पशुधन (गाय, भैंस, बकरी, भेड़)|पशुधन (गाय, म्हैस, शेळी, मेंढी)
Pets (dog, cat)|पालतू (कुत्ता, बिल्ली)|पाळीव (कुत्रा, मांजर)
Fever|बुखार|ताप
Loss of appetite|भूख न लगना|भूक मंदावणे
Weakness / lethargy|कमज़ोरी / सुस्ती|अशक्तपणा / सुस्ती
Drop in milk yield|दूध में कमी|दूध उत्पादनात घट
Swollen or hot udder|थन में सूजन या गर्मी|कासेला सूज किंवा उष्णता
Clots or blood in milk|दूध में थक्के या खून|दुधात गाठी किंवा रक्त
Limping / swollen foot|लंगड़ाना / पैर में सूजन|लंगडणे / पायाला सूज
Mouth blisters or drooling|मुँह में छाले या लार|तोंडात फोड किंवा लाळ गळणे
Diarrhea|दस्त|जुलाब
Vomiting|उल्टी|उलटी
Bloated stomach|पेट फूलना|पोट फुगणे
Difficulty breathing|साँस लेने में कठिनाई|श्वास घेण्यास त्रास
Coughing|खाँसी|खोकला
Nasal or eye discharge|नाक या आँख से स्राव|नाक किंवा डोळ्यातून स्राव
Skin lumps|त्वचा पर गाँठें|त्वचेवर गाठी
Itching / hair loss|खुजली / बाल झड़ना|खाज / केस गळणे
Blood in urine or stool|पेशाब या मल में खून|लघवी किंवा विष्ठेत रक्त
Not chewing cud|जुगाली न करना|रवंथ न करणे
Unable to stand|खड़े न हो पाना|उभे राहता न येणे
Unusual aggression|असामान्य आक्रामकता|असामान्य आक्रमकता""")

def ensure_schema():
    q("""CREATE TABLE IF NOT EXISTS Breeding (Breeding_ID INT AUTO_INCREMENT PRIMARY KEY, Pet_ID INT, Breeding_Date DATE,
        Method VARCHAR(20), Expected_Delivery DATE, Status VARCHAR(20), Notes VARCHAR(200),
        FOREIGN KEY (Pet_ID) REFERENCES Pet(Pet_ID))""", commit=True)

EDIT = {
 "pet": ("Pet", "Pet_ID", "pets", [("name", "Pet_Name", "Name", "text", 1), ("species", "Species", "Species", "sel", SPECIES),
         ("breed", "Breed", "Breed", "text", 0), ("gender", "Gender", "Gender", "sel", ["Female", "Male"]), ("dob", "DOB", "Date of birth", "date", 0)]),
 "milk": ("MilkYieldLog", "Log_ID", "milk", [("date", "Log_Date", "Date", "date", 1), ("morning", "Morning_Yield", "Morning yield (L)", "num", 1),
          ("evening", "Evening_Yield", "Evening yield (L)", "num", 1)]),
 "health": ("HealthRecords", "Record_ID", "health", [("vet", "Vet_ID", "Veterinarian", "vet", 0), ("date", "Visit_Date", "Visit date", "date", 1),
           ("diagnosis", "Diagnosis", "Diagnosis", "text", 1), ("prescription", "Prescription", "Prescription", "text", 0)]),
 "vaccination": ("Vaccinations", "Vaccination_ID", "vaccinations", [("vaccine", "Vaccine_Name", "Vaccine name", "text", 1),
           ("date", "Dose_Date", "Dose date", "date", 1), ("next", "Next_Due_Date", "Next due date", "date", 0)]),
 "breeding": ("Breeding", "Breeding_ID", "breeding", [("status", "Status", "Status", "sel", ["Pregnant", "Delivered", "Not pregnant"]),
           ("date", "Expected_Delivery", "Expected delivery", "date", 1), ("notes", "Notes", "Notes", "text", 0)]),
}

@app.route("/edit/<kind>/<int:rid>", methods=["GET", "POST"])
@login_required
def edit(kind, rid):
    if kind not in EDIT: abort(404)
    t, pk, back, fs = EDIT[kind]; u = session["uid"]
    if kind == "pet":
        row = q("SELECT * FROM Pet WHERE Pet_ID=%s AND User_ID=%s", (rid, u), one=True)
    else:
        row = q(f"SELECT x.* FROM {t} x JOIN Pet p ON p.Pet_ID=x.Pet_ID WHERE x.{pk}=%s AND p.User_ID=%s", (rid, u), one=True)
    if not row: abort(404)
    if request.method == "POST":
        vals = []
        for n, c, lbl, ty, x in fs:
            v = request.form.get(n, "").strip(); bad = False
            if ty == "date":
                v = dt(v) if v else None; bad = bool(x) and v is None
            elif ty == "num":
                try: v = float(v); bad = not 0 <= v <= 100
                except ValueError: bad = True
            elif ty == "sel":
                bad = v not in x
            elif ty == "vet":
                v = v or None; bad = bool(v) and not q("SELECT 1 FROM Veterinarians WHERE Vet_ID=%s", (v,), one=True)
            else:
                bad = bool(x) and not v; v = v or None
            if bad:
                flash(_("Please check the values.")); return redirect(request.url)
            vals.append(v)
        q(f"UPDATE {t} SET " + ",".join(f"{f[1]}=%s" for f in fs) + f" WHERE {pk}=%s", vals + [rid], commit=True)
        flash(_("Updated.")); return redirect(url_for(back))
    out = []
    for n, c, lbl, ty, x in fs:
        v = "" if row[c] is None else row[c]; d = {"name": n, "label": lbl, "val": v, "opts": None}
        if ty == "sel":
            d["type"] = "select"; d["opts"] = [(o, (ICONS[o] + " " + o) if c == "Species" else _(o)) for o in x]
        elif ty == "vet":
            d["type"] = "select"; d["val"] = str(v)
            d["opts"] = [("", _("- not specified -"))] + [(str(r["Vet_ID"]), r["Vet_Name"]) for r in q("SELECT Vet_ID,Vet_Name FROM Veterinarians ORDER BY Vet_Name")]
        else:
            d["type"] = {"text": "text", "date": "date", "num": "number"}[ty]
        out.append(d)
    return render_template("edit.html", fields=out, back=url_for(back))

GEST = {"Cow": 283, "Buffalo": 310, "Goat": 150, "Sheep": 150, "Horse": 340, "Dog": 63, "Cat": 65}

@app.route("/breeding", methods=["GET", "POST"])
@login_required
def breeding():
    u = session["uid"]
    if request.method == "POST":
        f = request.form; p = own_pet(f["pet"]); d = dt(f["date"])
        if d and p["Species"] in GEST and p["Gender"] == "Female":
            q("INSERT INTO Breeding (Pet_ID,Breeding_Date,Method,Expected_Delivery,Status,Notes) VALUES (%s,%s,%s,%s,'Pregnant',%s)",
              (p["Pet_ID"], d, "AI" if f["method"] == "AI" else "Natural", d + timedelta(days=GEST[p["Species"]]),
               f["notes"].strip() or None), commit=True)
            flash(_("Breeding record saved."))
        else:
            flash(_("Please check the values."))
        return redirect(url_for("breeding"))
    ph = ",".join(["%s"] * len(GEST))
    pets = q(f"SELECT Pet_ID,Pet_Name,Species FROM Pet WHERE User_ID=%s AND Gender='Female' AND Species IN ({ph}) ORDER BY Pet_Name", [u] + list(GEST))
    rows = q("""SELECT b.*,p.Pet_Name,p.Species,DATEDIFF(b.Expected_Delivery,CURDATE()) d FROM Breeding b JOIN Pet p
        ON p.Pet_ID=b.Pet_ID WHERE p.User_ID=%s ORDER BY b.Expected_Delivery DESC""", (u,))
    return render_template("breeding.html", rows=rows, pets=pets, today=date.today())

SYM = {"fever": "Fever", "appetite": "Loss of appetite", "weak": "Weakness / lethargy", "milk": "Drop in milk yield",
       "udder": "Swollen or hot udder", "clots": "Clots or blood in milk", "limp": "Limping / swollen foot",
       "mouth": "Mouth blisters or drooling", "diarrhea": "Diarrhea", "vomit": "Vomiting", "bloat": "Bloated stomach",
       "breath": "Difficulty breathing", "cough": "Coughing", "discharge": "Nasal or eye discharge", "lumps": "Skin lumps",
       "itch": "Itching / hair loss", "blood": "Blood in urine or stool", "cud": "Not chewing cud", "stand": "Unable to stand",
       "aggr": "Unusual aggression"}
GROUPS = {"live": ["fever", "appetite", "weak", "milk", "udder", "clots", "limp", "mouth", "diarrhea", "bloat", "breath", "cough", "discharge", "lumps", "itch", "blood", "cud", "stand", "aggr"],
          "pet": ["fever", "appetite", "weak", "vomit", "diarrhea", "breath", "cough", "discharge", "lumps", "itch", "blood", "mouth", "aggr"]}
RABIES = ("Rabies (suspected)", {"aggr", "mouth", "weak"}, True, "Do not touch the animal with bare hands. Keep people and animals away and contact a vet and the local health authority immediately.")
CONDS = {
 "live": [("Mastitis (udder infection)", {"udder", "clots", "milk", "fever"}, False, "Milk out the quarter fully, apply a warm compress and keep the shed clean. See a vet for treatment and do not sell the milk until cleared."),
  ("Foot and Mouth Disease", {"fever", "mouth", "limp", "milk", "appetite"}, True, "Highly contagious: isolate the animal now, do not share water or tools, and inform a vet and the local animal husbandry office."),
  ("Bloat", {"bloat", "breath", "appetite", "cud"}, True, "Emergency: keep the animal standing and walking gently, stop green fodder and call a vet immediately."),
  ("Milk fever (low calcium)", {"weak", "stand", "milk", "appetite"}, True, "Common after calving. Needs calcium treatment from a vet quickly. Do not force-feed an animal that cannot stand."),
  ("Tick fever (blood parasite)", {"fever", "weak", "blood", "appetite", "milk"}, True, "Dark urine with high fever needs a vet blood test and treatment. Control ticks on the animal and in the shed."),
  ("Lumpy skin disease", {"fever", "lumps", "milk", "discharge", "appetite"}, True, "Contagious: isolate the animal, control flies and mosquitoes and call a vet. Ask about vaccinating the herd."),
  ("Indigestion / diarrhea", {"diarrhea", "appetite", "cud", "weak"}, False, "Give clean water with electrolytes, offer dry fodder and avoid sudden feed changes. See a vet if it lasts more than 2 days."),
  ("Respiratory infection", {"cough", "discharge", "breath", "fever", "weak"}, False, "Keep the animal warm, dry and in a ventilated shed. A vet may prescribe antibiotics; see one soon if breathing is hard."),
  ("Foot rot / hoof infection", {"limp", "fever", "appetite", "milk"}, False, "Clean the hoof, keep the floor dry and consult a vet. Avoid wet, muddy areas."),
  ("Skin infection / mange", {"itch", "lumps"}, False, "Keep the animal and shed clean, separate it from others and ask a vet for a medicated wash."), RABIES],
 "pet": [("Parvovirus (dogs)", {"vomit", "diarrhea", "blood", "weak", "appetite", "fever"}, True, "Serious and can be fatal within days, especially in puppies. Go to a vet immediately for fluids and treatment."),
  ("Canine distemper", {"fever", "cough", "discharge", "weak", "appetite"}, True, "Contagious viral disease. Isolate the pet and see a vet urgently. Vaccination is the best prevention."),
  ("Tick fever", {"fever", "weak", "blood", "appetite"}, True, "Needs a vet blood test and treatment. Use tick control on the pet and its bedding."),
  ("Gastroenteritis (stomach upset)", {"vomit", "diarrhea", "appetite", "weak"}, False, "Offer small sips of water and a bland diet. See a vet if vomiting continues or there is blood."),
  ("Respiratory infection", {"cough", "discharge", "breath", "fever"}, False, "Keep the pet warm and rested. See a vet if breathing is hard or it lasts more than 2 days."),
  ("Skin allergy / mange / fleas", {"itch", "lumps"}, False, "Check for fleas and ticks, wash bedding and ask a vet for a skin treatment. Do not use human creams."), RABIES]}

@app.route("/symptoms", methods=["GET", "POST"])
@login_required
def symptoms():
    g = request.values.get("g", "live"); g = g if g in GROUPS else "live"
    sel, res = set(), None
    if request.method == "POST":
        sel = set(request.form.getlist("s")) & set(GROUPS[g])
        if not sel:
            flash(_("Select at least one symptom."))
        else:
            res = []
            for name, ss, urgent, advice in CONDS[g]:
                m = len(sel & ss)
                if m >= 2 or (m == len(ss) and m >= 1):
                    res.append({"name": name, "score": round(m / len(ss) * 100), "urgent": urgent, "advice": advice})
            res = sorted(res, key=lambda r: (-r["score"], not r["urgent"]))[:3]
    return render_template("symptoms.html", g=g, syms=[(k, SYM[k]) for k in GROUPS[g]], sel=sel, res=res)

# ---------- templates ----------
CSS = """*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(135deg,#ffe0b2,#c8e6c9,#b3e5fc,#f8bbd0,#fff9c4);background-size:400% 400%;background-attachment:fixed;animation:bg 20s ease infinite;color:#1f2d1f;min-height:100vh}@keyframes bg{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;background:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><g opacity=".3" font-size="40"><text x="12" y="50">🐄</text><text x="170" y="70" transform="rotate(12 170 70)">🐶</text><text x="90" y="150">🐱</text><text x="220" y="185">🐐</text><text x="20" y="240">🐃</text><text x="150" y="275">🐑</text><text x="255" y="295">🐾</text></g></svg>')}body::after{content:'🐄  🐐  🐶  🐱  🐴  🐑  🐃';position:fixed;bottom:4px;left:0;right:0;text-align:center;font-size:2.6em;opacity:.4;pointer-events:none;z-index:0;white-space:pre}header,main{position:relative;z-index:1}header{position:sticky;top:0;z-index:5}button,a.btn,nav a,.langsel{transition:transform .18s cubic-bezier(.34,1.56,.64,1),box-shadow .18s}button:hover,a.btn:hover,nav a:hover{transform:translateY(-2px) scale(1.07);box-shadow:0 6px 14px #0003}button:active,a.btn:active,nav a:active{transform:scale(.88)}@keyframes pop{0%{transform:scale(1)}40%{transform:scale(1.22)}70%{transform:scale(.94)}100%{transform:scale(1)}}.pop{animation:pop .35s}.grid .card{transition:transform .2s cubic-bezier(.34,1.56,.64,1),box-shadow .2s}.grid .card:hover{transform:translateY(-5px) scale(1.04);box-shadow:0 10px 22px #0003}.langsel{width:auto;margin:0;padding:6px 12px;border-radius:18px;background:#ffffff33;color:#fff;border:1px solid #fff8;cursor:pointer}.langsel option{color:#000}
header{background:linear-gradient(90deg,#2e7d32,#00897b);color:#fff;padding:12px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;box-shadow:0 2px 8px #0003}
nav{display:flex;flex-wrap:wrap;gap:6px;align-items:center}nav a{color:#fff;text-decoration:none;padding:6px 12px;border-radius:20px;background:#ffffff22}nav a:hover{background:#ffffff55}
main{max-width:980px;margin:20px auto;padding:0 14px}.card{background:rgba(255,255,255,.74);backdrop-filter:blur(8px);border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 2px 8px #0002;border-top:4px solid #43a047}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}.grid .card{margin:0;text-align:center}.big{font-size:2em;font-weight:700;color:#2e7d32}
.ico{font-size:2.4em}.c1{background:#fff3e0;border-top-color:#fb8c00}.c1 .big{color:#e65100}.c2{background:#e1f5fe;border-top-color:#039be5}.c2 .big{color:#0277bd}.c3{background:#ffebee;border-top-color:#e53935}.c3 .big{color:#c62828}
h2{color:#1b5e20}h3{color:#2e7d32;margin-top:0}input,select,textarea,button{font:inherit;padding:8px;border:1px solid #bbb;border-radius:8px;width:100%;margin:4px 0 10px}
button{background:linear-gradient(90deg,#43a047,#00897b);color:#fff;border:0;cursor:pointer;width:auto;padding:8px 18px}button:hover{opacity:.9}button.d{background:#e53935;padding:4px 10px}
form.inl{display:inline}.inl button{margin:0}table{width:100%;border-collapse:collapse}th{background:#e8f5e9;color:#1b5e20}th,td{text-align:left;padding:8px;border-bottom:1px solid #e3e3e3}tr:hover td{background:#f9fff9}
.wrap{overflow-x:auto}.msg{background:#fff3cd;padding:10px;border-radius:8px;margin-bottom:12px}.auth{max-width:400px;margin:40px auto}.red{color:#c62828;font-weight:600}.chips label{display:inline-block;background:#f1f8e9;border:1px solid #c5e1a5;border-radius:18px;padding:6px 12px;margin:4px;cursor:pointer}.chips input{width:auto;margin:0 6px 0 0}.pi{font-size:1.5em;vertical-align:middle;margin-right:4px}.alert{background:#ffebee;border-left:5px solid #e53935;padding:10px;border-radius:8px;margin-bottom:8px}.ok{background:#e8f5e9;border-left:5px solid #43a047;padding:10px;border-radius:8px}.nav2{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.lang a{color:#fff;margin-left:4px;padding:3px 9px;border:1px solid #fff8;border-radius:12px;text-decoration:none;font-size:.85em}.row{display:flex;gap:8px;flex-wrap:wrap}.row>*{flex:1;min-width:140px}a.btn{display:inline-block;background:#039be5;color:#fff;padding:4px 10px;border-radius:14px;text-decoration:none;margin:2px;white-space:nowrap}"""
def page(body):
    return "{% extends 'base.html' %}{% block c %}" + body + "{% endblock %}"
def form(fields, btn="Save", action=""):
    return f'<form method="post" {action}><input type="hidden" name="t" value="{{{{T()}}}}">{fields}<button>{{{{_("{btn}")}}}}</button></form>'
def delbtn(kind, idexpr):
    return (f'<a class="btn" href="/edit/{kind}/{{{{{idexpr}}}}}">&#9999;&#65039; {{{{_("Edit")}}}}</a>' f'<form class="inl" method="post" action="/delete/{kind}/{{{{{idexpr}}}}}" onsubmit="return confirm(\'Delete?\')">'
            '<input type="hidden" name="t" value="{{T()}}"><button class="d">{{_("Delete")}}</button></form>')
T_ = lambda s: "{{_(%r)}}" % s
def lab(s, rest): return f'<label>{T_(s)}</label>{rest}'
PETSEL = lab("Animal", '<select name="pet" required>{% for p in pets %}<option value="{{p.Pet_ID}}">{{IC.get(p.Species,"🐾")}} {{p.Pet_Name}} ({{p.Species}})</option>{% endfor %}</select>')
NOPETS = '{% if not pets %}<p><a href="/pets">' + T_("Please add an animal first.") + '</a></p>{% endif %}'
def th(*a): return "<tr>" + "".join(f"<th>{T_(x) if x else ''}</th>" for x in a) + "</tr>"
def empty(n, key="No records."): return f'<tr><td colspan="{n}">{T_(key)}</td></tr>'
PI = '<span class="pi">{{IC.get(%s.Species,"🐾")}}</span>'
CHARTS = '{% if series %}<div class="card"><h3>&#128200; ' + T_("Milk trend (last 14 days)") + '</h3><div class="grid">{% for s in series %}<div><b>{{s.icon}} {{s.name}}</b>{{s.svg}}{% if s.n < 2 %}<br><small>' + T_("hint") + '</small>{% endif %}</div>{% endfor %}</div></div>{% endif %}'
ALERTS = '<div class="card"><h3>&#128680; ' + T_("Health alerts") + '</h3>{% for a in alerts %}<div class="alert">&#9888;&#65039; {{a}}</div>{% else %}<div class="ok">&#9989; ' + T_("All animals are producing normally.") + '</div>{% endfor %}</div>'
H3 = lambda ico, k: f'<h3>{ico} {T_(k)}</h3>'
TEMPLATES = {
"base.html": """<!doctype html><html lang="{{session.get('lang') or 'en'}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PetPulse</title><style>""" + CSS + """</style></head><body><header><b>&#128062; """ + T_("PetPulse - Livestock & Pet Health") + """</b><div class="nav2">
{% if session.uid %}<nav><a href="/dashboard">&#127968; """ + T_("Dashboard") + """</a><a href="/pets">&#128062; """ + T_("My Animals") + """</a><a href="/milk">&#129371; """ + T_("Milk Yield") + """</a><a href="/health">&#129658; """ + T_("Health") + """</a>
<a href="/vaccinations">&#128137; """ + T_("Vaccinations") + """</a><a href="/breeding">&#127868; """ + T_("Breeding") + """</a><a href="/symptoms">&#129298; """ + T_("Symptoms") + """</a><a href="/vets">&#128104;&#8205;&#9877;&#65039; """ + T_("Vets") + """</a><form class="inl" method="post" action="/logout"><input type="hidden" name="t" value="{{T()}}">
<button>""" + T_("Logout") + """ ({{session.name}})</button></form></nav>{% endif %}<select class="langsel" onchange="location='/lang/'+this.value">{% for c, n in [('en','&#127760; English'),('hi','हिन्दी'),('mr','मराठी')] %}<option value="{{c}}" {{'selected' if (session.get('lang') or 'en') == c}}>{{n|safe}}</option>{% endfor %}</select></div></header>
<main>{% for m in get_flashed_messages() %}<div class="msg">{{m}}</div>{% endfor %}{% block c %}{% endblock %}</main><script>document.addEventListener("click",function(e){var b=e.target.closest("button,a.btn,nav a,.grid .card");if(b){b.classList.remove("pop");void b.offsetWidth;b.classList.add("pop");}});</script></body></html>""",
"login.html": page('<div class="card auth"><h2>' + T_("Login") + '</h2>' + form(lab("Email or Phone number", '<input name="ident" required autofocus>') + lab("Password", '<input type="password" name="password" required>'), "Login") + '<p>' + T_("New user?") + ' <a href="/register">' + T_("Create account") + '</a></p></div>'),
"register.html": page('<div class="card auth"><h2>' + T_("Create account") + '</h2>' + form(lab("Full name", '<input name="name" required>') + lab("Email", '<input type="email" name="email" required>') + lab("Phone (10 digits)", '<input name="phone" required pattern="[0-9+ ]{10,14}">') + lab("Password (min 8 characters)", '<input type="password" name="password" minlength="8" required>') + lab("Confirm password", '<input type="password" name="confirm" required>'), "Register") + '<p>' + T_("Already registered?") + ' <a href="/login">' + T_("Login") + '</a></p></div>'),
"dashboard.html": page('<h2>&#128075; ' + T_("Welcome") + ', {{session.name}}</h2><div class="grid"><div class="card c1"><div class="ico">&#128062;</div><div class="big">{{n}}</div>' + T_("Animals registered") + '</div><div class="card c2"><div class="ico">&#129371;</div><div class="big">{{milk}} L</div>' + T_("Milk in last 7 days") + '</div><div class="card c3"><div class="ico">&#128137;</div><div class="big">{{due|length}}</div>' + T_("Vaccinations due in 30 days") + '</div></div><br>' + ALERTS + CHARTS
 + '<div class="card">' + H3("&#128276;", "Vaccination reminders") + '{% for v in due %}<p>{{IC.get(v.Species,"🐾")}} {{v.Pet_Name}} - &#128137; {{v.Vaccine_Name}} - {{v.Next_Due_Date}} {% if v.d<0 %}<span class="red">(' + T_("overdue") + ')</span>{% else %}({{v.d}} ' + T_("days") + '){% endif %}</p>{% else %}<p>' + T_("No vaccinations due.") + '</p>{% endfor %}</div>'
 '<div class="card">' + H3("&#127868;", "Upcoming deliveries") + '{% for b in deliv %}<p>{{IC.get(b.Species,"🐾")}} {{b.Pet_Name}} - {{b.Expected_Delivery}} ({{b.d}} ' + T_("days") + ')</p>{% else %}<p>' + T_("No upcoming deliveries.") + '</p>{% endfor %}</div>' '<div class="card">' + H3("&#129658;", "Recent health records") + '{% for r in rec %}<p>{{r.Visit_Date}} - {{IC.get(r.Species,"🐾")}} {{r.Pet_Name}}: {{r.Diagnosis}}</p>{% else %}<p>' + T_("No records yet.") + '</p>{% endfor %}</div>'),
"pets.html": page('<div class="card">' + H3("&#128062;", "Add animal") + form(lab("Name", '<input name="name" required>') + lab("Species", '<select name="species">{% for s in species %}<option value="{{s}}">{{IC[s]}} {{s}}</option>{% endfor %}</select>') + lab("Breed", '<input name="breed">') + lab("Gender", '<select name="gender"><option value="Female">' + T_("Female") + '</option><option value="Male">' + T_("Male") + '</option></select>') + lab("Date of birth", '<input type="date" name="dob">'), "Add") + '</div><div class="card wrap">' + H3("&#128062;", "My animals") + '<table>' + th("Name", "Species", "Breed", "Gender", "Age (yrs)", "") + '{% for p in rows %}<tr><td>' + PI % "p" + '<b>{{p.Pet_Name}}</b></td><td>{{p.Species}}</td><td>{{p.Breed or "-"}}</td><td>{{_(p.Gender)}}</td><td>{{p.Age if p.Age is not none else "-"}}</td><td>' + delbtn("pet", "p.Pet_ID") + '</td></tr>{% else %}' + empty(6, "No animals yet.") + '{% endfor %}</table></div>'),
"milk.html": page(ALERTS + CHARTS + '<div class="card">' + H3("&#129371;", "Add milk log (Cow / Buffalo / Goat)") + NOPETS + form(PETSEL + lab("Date", '<input type="date" name="date" value="{{today}}" required>') + lab("Morning yield (L)", '<input type="number" step="0.01" min="0" max="100" name="morning" required>') + lab("Evening yield (L)", '<input type="number" step="0.01" min="0" max="100" name="evening" required>'), "Save") + '</div><div class="card wrap">' + H3("&#129371;", "Milk records") + '<table>' + th("Date", "Animal", "Morning", "Evening", "Total", "") + '{% for r in rows %}<tr><td>{{r.Log_Date}}</td><td>' + PI % "r" + '{{r.Pet_Name}}</td><td>{{r.Morning_Yield}}</td><td>{{r.Evening_Yield}}</td><td><b>{{r.Total_Yield}}</b></td><td>' + delbtn("milk", "r.Log_ID") + '</td></tr>{% else %}' + empty(6) + '{% endfor %}</table></div>'),
"health.html": page('<div class="card">' + H3("&#129658;", "Add health record") + NOPETS + form(PETSEL + lab("Veterinarian", '<select name="vet"><option value="">' + T_("- not specified -") + '</option>{% for v in vets %}<option value="{{v.Vet_ID}}">{{v.Vet_Name}} ({{v.Specialization}})</option>{% endfor %}</select>') + lab("Visit date", '<input type="date" name="date" value="{{today}}" required>') + lab("Diagnosis", '<input name="diagnosis" required>') + lab("Prescription", '<textarea name="prescription" rows="2"></textarea>'), "Save") + '</div><div class="card wrap">' + H3("&#129658;", "Health history") + '<table>' + th("Date", "Animal", "Vet", "Diagnosis", "Prescription", "") + '{% for r in rows %}<tr><td>{{r.Visit_Date}}</td><td>' + PI % "r" + '{{r.Pet_Name}}</td><td>{{r.Vet_Name or "-"}}</td><td>{{r.Diagnosis}}</td><td>{{r.Prescription or "-"}}</td><td>' + delbtn("health", "r.Record_ID") + '</td></tr>{% else %}' + empty(6) + '{% endfor %}</table></div>'),
"vaccinations.html": page('<div class="card">' + H3("&#128137;", "Add vaccination") + NOPETS + form(PETSEL + lab("Vaccine name", '<input name="vaccine" required>') + lab("Dose date", '<input type="date" name="date" value="{{today}}" required>') + lab("Next due date", '<input type="date" name="next">'), "Save") + '</div><div class="card wrap">' + H3("&#128137;", "Vaccinations") + '<table>' + th("Animal", "Vaccine name", "Given", "Next due", "", "") + '{% for r in rows %}<tr><td>' + PI % "r" + '{{r.Pet_Name}}</td><td>&#128137; {{r.Vaccine_Name}}</td><td>{{r.Dose_Date}}</td><td>{{r.Next_Due_Date or "-"}}</td><td>{% if r.d is not none and r.d<0 %}<span class="red">' + T_("Overdue") + '</span>{% elif r.d is not none and r.d<=30 %}' + T_("Due soon") + '{% endif %}</td><td>' + delbtn("vaccination", "r.Vaccination_ID") + '</td></tr>{% else %}' + empty(6) + '{% endfor %}</table></div>'),
"vets.html": page('<div class="card">' + H3("&#128205;", "Find a vet near you") + '<form method="get" class="row"><input name="q" value="{{qs}}" placeholder="' + T_("City or pincode") + '"><button>&#128269; ' + T_("Search") + '</button></form></div><div class="card wrap">' + H3("&#128104;&#8205;&#9877;&#65039;", "Veterinarians") + '<table>' + th("Name", "Specialization", "Address", "") + '{% for v in rows %}<tr><td><b>{{v.Vet_Name}}</b></td><td>{{v.Specialization or "-"}}</td><td>{{v.Street or ""}} {{v.City}} {{v.Pincode or ""}}</td><td><a class="btn" href="tel:{{v.Phone}}">&#128222; ' + T_("Call") + '</a><a class="btn" target="_blank" href="https://www.google.com/maps/search/?api=1&query={{((v.Vet_Name or "") ~ " " ~ (v.Street or "") ~ " " ~ v.City ~ " " ~ (v.Pincode or ""))|urlencode}}">&#128506;&#65039; ' + T_("Map") + '</a></td></tr>{% else %}' + empty(4, "No vets found.") + '{% endfor %}</table></div><div class="card">' + H3("&#10133;", "Add a veterinarian") + form(lab("Name", '<input name="name" required>') + lab("Specialization", '<input name="spec">') + lab("Phone", '<input name="phone" required>') + lab("Street", '<input name="street">') + lab("City", '<input name="city" required>') + lab("Pincode", '<input name="pin" maxlength="6">'), "Add") + '</div>'),
}
TEMPLATES.update({
"edit.html": page('<div class="card">' + H3("&#9999;&#65039;", "Edit") + '<form method="post"><input type="hidden" name="t" value="{{T()}}">{% for f in fields %}<label>{{_(f.label)}}</label>{% if f.type == "select" %}<select name="{{f.name}}">{% for v, l in f.opts %}<option value="{{v}}" {{"selected" if v|string == f.val|string}}>{{l}}</option>{% endfor %}</select>{% else %}<input type="{{f.type}}" name="{{f.name}}" value="{{f.val}}" {{"step=0.01 min=0 max=100" if f.type == "number"}}>{% endif %}{% endfor %}<button>' + T_("Save") + '</button> <a class="btn" href="{{back}}">' + T_("Cancel") + '</a></form></div>'),
"breeding.html": page('<div class="card">' + H3("&#127868;", "Add breeding record") + '{% if not pets %}<p>' + T_("No female animals found. Add one in My Animals first.") + '</p>{% endif %}' + form(PETSEL + lab("Breeding date", '<input type="date" name="date" value="{{today}}" required>') + lab("Method", '<select name="method"><option value="Natural">' + T_("Natural") + '</option><option value="AI">' + T_("Artificial insemination") + '</option></select>') + lab("Notes", '<input name="notes" maxlength="200">'), "Save") + '</div><div class="card wrap">' + H3("&#127868;", "Breeding records") + '<table>' + th("Animal", "Breeding date", "Method", "Expected delivery", "Days left", "Status", "") + '{% for r in rows %}<tr><td>' + PI % "r" + '{{r.Pet_Name}}</td><td>{{r.Breeding_Date}}</td><td>{{_("Artificial insemination") if r.Method == "AI" else _("Natural")}}</td><td><b>{{r.Expected_Delivery}}</b></td><td>{% if r.Status == "Pregnant" %}{% if r.d < 0 %}<span class="red">' + T_("overdue") + '</span>{% elif r.d <= 14 %}<span class="red">{{r.d}}</span>{% else %}{{r.d}}{% endif %}{% else %}-{% endif %}</td><td>{{_(r.Status)}}</td><td>' + delbtn("breeding", "r.Breeding_ID") + '</td></tr>{% else %}' + empty(7) + '{% endfor %}</table></div>'),
"symptoms.html": page('<div class="card">' + H3("&#129298;", "Symptom Checker") + '<p>' + T_("Select the animal and the symptoms you see.") + '</p><p><a class="btn" href="/symptoms?g=live">&#128004; ' + T_("Livestock (cow, buffalo, goat, sheep)") + '</a><a class="btn" href="/symptoms?g=pet">&#128054; ' + T_("Pets (dog, cat)") + '</a></p>' + form('<input type="hidden" name="g" value="{{g}}"><div class="chips">{% for k, l in syms %}<label><input type="checkbox" name="s" value="{{k}}" {{"checked" if k in sel}}> {{_(l)}}</label>{% endfor %}</div>', "Check") + '</div>{% if res is not none %}<div class="card">' + H3("&#128203;", "Possible conditions") + '{% for r in res %}<div class="{{"alert" if r.urgent else "ok"}}"><b>{{r.name}}</b> - ' + T_("Match") + ' {{r.score}}%{% if r.urgent %} - <span class="red">&#128680; ' + T_("Call a vet now") + '</span>{% endif %}<br><b>' + T_("What to do") + ':</b> {{r.advice}}</div><br>{% else %}<p>' + T_("No matching condition found. If the animal looks unwell, please consult a vet.") + '</p>{% endfor %}<p><a class="btn" href="/vets">&#128205; ' + T_("Find a vet") + '</a></p><small>' + T_("This is only guidance, not a diagnosis. Always consult a veterinarian.") + '</small></div>{% endif %}'),
})
app.jinja_loader = DictLoader(TEMPLATES)

if __name__ == "__main__":
    try:
        ensure_schema()
    except Exception as e:
        print("Schema check failed:", e)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))