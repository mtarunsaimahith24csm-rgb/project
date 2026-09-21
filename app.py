from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file
)

import sqlite3
import joblib
import json
import pandas as pd
from io import BytesIO
model = joblib.load("model/student_model.pkl")

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)

app.secret_key = "student-performance-secret-key"


# ==================================================
# DATABASE CONFIGURATION
# ==================================================

DATABASE = "students.db"


# ==================================================
# MACHINE LEARNING MODEL
# ==================================================

MODEL_PATH = "model/student_model.pkl"

model = joblib.load(MODEL_PATH)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ==================================================
# INITIALIZE DATABASE
# ==================================================

def initialize_database():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            attendance REAL NOT NULL,
            study_hours REAL NOT NULL,
            previous_score REAL NOT NULL,
            assignment_score REAL NOT NULL,
            internal_score REAL NOT NULL,
            sleep_hours REAL NOT NULL,
            participation REAL NOT NULL,
            predicted_score REAL,
            performance TEXT,
            risk_level TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    existing_admin = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if existing_admin is None:

        hashed_password = generate_password_hash(
    "admin123",
    method="pbkdf2:sha256"
)
        

        connection.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "admin",
                hashed_password,
                "admin"
            )
        )

    connection.commit()
    connection.close()

# ==================================================
# PERFORMANCE CLASSIFICATION
# ==================================================

def get_performance(score):

    if score >= 85:
        return "Excellent"

    elif score >= 70:
        return "Good"

    elif score >= 50:
        return "Average"

    else:
        return "At Risk"


# ==================================================
# RISK CLASSIFICATION
# ==================================================

def get_risk_level(score):

    if score >= 75:
        return "Low"

    elif score >= 50:
        return "Medium"

    else:
        return "High"


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def index():

    return render_template("index.html")


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        # Demo login credentials
        if username == "admin" and password == "admin123":

            session["username"] = username

            return redirect(
                url_for("dashboard")
            )

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.pop("username", None)

    return redirect(
        url_for("index")
    )


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get all students
    students = connection.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    # Total students
    total_students = connection.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    # Performance statistics
    excellent = connection.execute(
        "SELECT COUNT(*) FROM students WHERE performance = 'Excellent'"
    ).fetchone()[0]

    good = connection.execute(
        "SELECT COUNT(*) FROM students WHERE performance = 'Good'"
    ).fetchone()[0]

    average = connection.execute(
        "SELECT COUNT(*) FROM students WHERE performance = 'Average'"
    ).fetchone()[0]

    at_risk = connection.execute(
        "SELECT COUNT(*) FROM students WHERE performance = 'At Risk'"
    ).fetchone()[0]

    # Risk statistics
    low_risk = connection.execute(
        "SELECT COUNT(*) FROM students WHERE risk_level = 'Low'"
    ).fetchone()[0]

    medium_risk = connection.execute(
        "SELECT COUNT(*) FROM students WHERE risk_level = 'Medium'"
    ).fetchone()[0]

    high_risk = connection.execute(
        "SELECT COUNT(*) FROM students WHERE risk_level = 'High'"
    ).fetchone()[0]

    # Average predicted score
    average_score = connection.execute(
        """
        SELECT AVG(predicted_score)
        FROM students
        WHERE predicted_score IS NOT NULL
        """
    ).fetchone()[0]

    if average_score is None:
        average_score = 0

    # Top 5 performers
    top_students = connection.execute(
        """
        SELECT *
        FROM students
        WHERE predicted_score IS NOT NULL
        ORDER BY predicted_score DESC
        LIMIT 5
        """
    ).fetchall()

    # 5 students with lowest predicted scores
    at_risk_students = connection.execute(
        """
        SELECT *
        FROM students
        WHERE predicted_score IS NOT NULL
        ORDER BY predicted_score ASC
        LIMIT 5
        """
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        students=students,
        total_students=total_students,
        excellent=excellent,
        good=good,
        average=average,
        at_risk=at_risk,
        low_risk=low_risk,
        medium_risk=medium_risk,
        high_risk=high_risk,
        average_score=round(average_score, 2),
        top_students=top_students,
        at_risk_students=at_risk_students
    )
# ==================================================
# STUDENT LIST
# ==================================================

@app.route("/students")
def students():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    students = connection.execute(
        """
        SELECT *
        FROM students
        ORDER BY id DESC
        """
    ).fetchall()


    connection.close()


    return render_template(
        "students.html",
        students=students
    )


# ==================================================
# ADD STUDENT
# ==================================================

@app.route(
    "/students/add",
    methods=["GET", "POST"]
)
def add_student():

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        student_id = request.form[
            "student_id"
        ]

        name = request.form[
            "name"
        ]


        attendance = float(
            request.form["attendance"]
        )

        study_hours = float(
            request.form["study_hours"]
        )

        previous_score = float(
            request.form["previous_score"]
        )

        assignment_score = float(
            request.form["assignment_score"]
        )

        internal_score = float(
            request.form["internal_score"]
        )

        sleep_hours = float(
            request.form["sleep_hours"]
        )

        participation = float(
            request.form["participation"]
        )


        # ------------------------------------------
        # MACHINE LEARNING PREDICTION
        # ------------------------------------------

        input_data = [[

            attendance,

            study_hours,

            previous_score,

            assignment_score,

            internal_score,

            sleep_hours,

            participation

        ]]


        predicted_score = float(
            model.predict(input_data)[0]
        )


        # Keep score between 0 and 100

        predicted_score = max(
            0,
            min(100, predicted_score)
        )


        performance = get_performance(
            predicted_score
        )


        risk_level = get_risk_level(
            predicted_score
        )


        # ------------------------------------------
        # SAVE STUDENT
        # ------------------------------------------

        connection = get_db_connection()


        try:

            connection.execute(
                """
                INSERT INTO students (

                    student_id,

                    name,

                    attendance,

                    study_hours,

                    previous_score,

                    assignment_score,

                    internal_score,

                    sleep_hours,

                    participation,

                    predicted_score,

                    performance,

                    risk_level

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (

                    student_id,

                    name,

                    attendance,

                    study_hours,

                    previous_score,

                    assignment_score,

                    internal_score,

                    sleep_hours,

                    participation,

                    predicted_score,

                    performance,

                    risk_level

                )
            )


            connection.commit()


        except sqlite3.IntegrityError:

            connection.close()


            return render_template(

                "add_student.html",

                error="Student ID already exists."

            )


        connection.close()


        return redirect(
            url_for("students")
        )


    return render_template(
        "add_student.html"
    )


# ==================================================
# STUDENT DETAILS
# ==================================================

@app.route(
    "/students/<int:student_id>"
)
def student_detail(student_id):

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    student = connection.execute(

        """
        SELECT *
        FROM students
        WHERE id = ?
        """,

        (student_id,)

    ).fetchone()


    connection.close()


    if student is None:

        return "Student not found", 404


    return render_template(

        "student_detail.html",

        student=student

    )

@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    student = connection.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if student is None:
        connection.close()
        return "Student not found", 404

    if request.method == "POST":

        student_code = request.form["student_id"]
        name = request.form["name"]

        attendance = float(request.form["attendance"])
        study_hours = float(request.form["study_hours"])
        previous_score = float(request.form["previous_score"])
        assignment_score = float(request.form["assignment_score"])
        internal_score = float(request.form["internal_score"])
        sleep_hours = float(request.form["sleep_hours"])
        participation = float(request.form["participation"])

        # Prepare data for ML model
        input_data = [[
            attendance,
            study_hours,
            previous_score,
            assignment_score,
            internal_score,
            sleep_hours,
            participation
        ]]

        # Generate new prediction
        predicted_score = float(
            model.predict(input_data)[0]
        )

        # Keep score between 0 and 100
        predicted_score = max(
            0,
            min(100, predicted_score)
        )

        # Calculate performance
        performance = get_performance(
            predicted_score
        )

        # Calculate risk
        risk_level = get_risk_level(
            predicted_score
        )

        try:

            connection.execute(
                """
                UPDATE students
                SET
                    student_id = ?,
                    name = ?,
                    attendance = ?,
                    study_hours = ?,
                    previous_score = ?,
                    assignment_score = ?,
                    internal_score = ?,
                    sleep_hours = ?,
                    participation = ?,
                    predicted_score = ?,
                    performance = ?,
                    risk_level = ?
                WHERE id = ?
                """,
                (
                    student_code,
                    name,
                    attendance,
                    study_hours,
                    previous_score,
                    assignment_score,
                    internal_score,
                    sleep_hours,
                    participation,
                    predicted_score,
                    performance,
                    risk_level,
                    student_id
                )
            )

            connection.commit()

        except sqlite3.IntegrityError:

            connection.close()

            return render_template(
                "edit_student.html",
                student=student,
                error="Student ID already exists."
            )

        connection.close()

        return redirect(
            url_for(
                "student_detail",
                student_id=student_id
            )
        )

    connection.close()

    return render_template(
        "edit_student.html",
        student=student
    )

# ==================================================
# DELETE STUDENT
# ==================================================

@app.route(
    "/students/delete/<int:student_id>",
    methods=["POST"]
)
def delete_student(student_id):

    if "username" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    connection.execute(

        """
        DELETE FROM students
        WHERE id = ?
        """,

        (student_id,)

    )


    connection.commit()

    connection.close()


    return redirect(
        url_for("students")
    )


# ==================================================
# PREDICTION PAGE
# ==================================================



# ==================================================
# ANALYTICS
# ==================================================

@app.route("/analytics")
def analytics():

    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    rows = connection.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    connection.close()

    students = []

    for student in rows:

        students.append({
            "id": student["id"],
            "student_id": student["student_id"],
            "name": student["name"],
            "attendance": student["attendance"],
            "study_hours": student["study_hours"],
            "previous_score": student["previous_score"],
            "assignment_score": student["assignment_score"],
            "internal_score": student["internal_score"],
            "sleep_hours": student["sleep_hours"],
            "participation": student["participation"],
            "predicted_score": student["predicted_score"] or 0,
            "performance": student["performance"],
            "risk_level": student["risk_level"]
        })

    return render_template(
        "analytics.html",
        students=students
    )


# ==================================================
# API
# ==================================================

@app.route("/api/students")
def api_students():

    if "username" not in session:

        return jsonify({

            "error":
                "Unauthorized"

        }), 401


    connection = get_db_connection()


    students = connection.execute(

        """
        SELECT *
        FROM students
        """

    ).fetchall()


    connection.close()


    result = []


    for student in students:

        result.append({

            "student_id":
                student["student_id"],

            "name":
                student["name"],

            "predicted_score":
                student["predicted_score"],

            "performance":
                student["performance"],

            "risk_level":
                student["risk_level"]

        })


    return jsonify(result)


# ==================================================
# START APPLICATION
# ==================================================
@app.route("/model-evaluation")
def model_evaluation():

    if "username" not in session:
        return redirect(url_for("login"))

    try:

        with open(
            "model/model_metrics.json",
            "r"
        ) as file:

            metrics = json.load(file)

    except FileNotFoundError:

        return "Model evaluation file not found. Please train the model first.", 404

    return render_template(
        "model_evaluation.html",
        metrics=metrics
    )
@app.route("/import-export")
def import_export():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "import_export.html"
    )
@app.route("/students/import", methods=["POST"])
def import_students():

    if "username" not in session:
        return redirect(url_for("login"))

    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return render_template(
            "import_export.html",
            error="Please select a CSV or Excel file."
        )

    filename = uploaded_file.filename.lower()

    try:

        if filename.endswith(".csv"):
            data = pd.read_csv(uploaded_file)

        elif filename.endswith(".xlsx"):
            data = pd.read_excel(uploaded_file)

        else:
            return render_template(
                "import_export.html",
                error="Only CSV and Excel (.xlsx) files are supported."
            )

    except Exception as error:

        return render_template(
            "import_export.html",
            error=f"Unable to read file: {error}"
        )

    required_columns = [
        "student_id",
        "name",
        "attendance",
        "study_hours",
        "previous_score",
        "assignment_score",
        "internal_score",
        "sleep_hours",
        "participation"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:

        return render_template(
            "import_export.html",
            error=(
                "Missing columns: "
                + ", ".join(missing_columns)
            )
        )

    connection = get_db_connection()

    imported_count = 0
    failed_count = 0
    errors = []

    for index, row in data.iterrows():

        excel_row = index + 2

        try:

            student_id = str(row["student_id"]).strip()
            name = str(row["name"]).strip()

            if not student_id:
                raise ValueError("Student ID is empty.")

            if not name:
                raise ValueError("Student name is empty.")

            attendance = float(row["attendance"])
            study_hours = float(row["study_hours"])
            previous_score = float(row["previous_score"])
            assignment_score = float(row["assignment_score"])
            internal_score = float(row["internal_score"])
            sleep_hours = float(row["sleep_hours"])
            participation = float(row["participation"])

            if not 0 <= attendance <= 100:
                raise ValueError(
                    "Attendance must be between 0 and 100."
                )

            if not 0 <= previous_score <= 100:
                raise ValueError(
                    "Previous score must be between 0 and 100."
                )

            if not 0 <= assignment_score <= 100:
                raise ValueError(
                    "Assignment score must be between 0 and 100."
                )

            if not 0 <= internal_score <= 100:
                raise ValueError(
                    "Internal score must be between 0 and 100."
                )

            if study_hours < 0:
                raise ValueError(
                    "Study hours cannot be negative."
                )

            if sleep_hours < 0:
                raise ValueError(
                    "Sleep hours cannot be negative."
                )

            if not 0 <= participation <= 10:
                raise ValueError(
                    "Participation must be between 0 and 10."
                )

            input_data = [[
                attendance,
                study_hours,
                previous_score,
                assignment_score,
                internal_score,
                sleep_hours,
                participation
            ]]

            predicted_score = float(
                model.predict(input_data)[0]
            )

            predicted_score = max(
                0,
                min(100, predicted_score)
            )

            performance = get_performance(
                predicted_score
            )

            risk_level = get_risk_level(
                predicted_score
            )

            connection.execute(
                """
                INSERT OR REPLACE INTO students
                (
                    student_id,
                    name,
                    attendance,
                    study_hours,
                    previous_score,
                    assignment_score,
                    internal_score,
                    sleep_hours,
                    participation,
                    predicted_score,
                    performance,
                    risk_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    name,
                    attendance,
                    study_hours,
                    previous_score,
                    assignment_score,
                    internal_score,
                    sleep_hours,
                    participation,
                    predicted_score,
                    performance,
                    risk_level
                )
            )

            imported_count += 1

        except Exception as error:

            failed_count += 1

            errors.append(
                f"Row {excel_row}: {error}"
            )

    connection.commit()
    connection.close()

    return render_template(
        "import_export.html",
        success=(
            f"Import completed. "
            f"{imported_count} student(s) imported successfully."
        ),
        imported_count=imported_count,
        failed_count=failed_count,
        errors=errors
    )
@app.route("/students/export")
def export_students():

    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT
            student_id,
            name,
            attendance,
            study_hours,
            previous_score,
            assignment_score,
            internal_score,
            sleep_hours,
            participation,
            predicted_score,
            performance,
            risk_level
        FROM students
        ORDER BY id
        """
    ).fetchall()

    connection.close()


    data = []

    for row in rows:

        data.append({
            "student_id": row["student_id"],
            "name": row["name"],
            "attendance": row["attendance"],
            "study_hours": row["study_hours"],
            "previous_score": row["previous_score"],
            "assignment_score": row["assignment_score"],
            "internal_score": row["internal_score"],
            "sleep_hours": row["sleep_hours"],
            "participation": row["participation"],
            "predicted_score": row["predicted_score"],
            "performance": row["performance"],
            "risk_level": row["risk_level"]
        })


    dataframe = pd.DataFrame(data)


    output = BytesIO()


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        dataframe.to_excel(
            writer,
            index=False,
            sheet_name="Students"
        )


    output.seek(0)


    return send_file(
        output,
        as_attachment=True,
        download_name="student_predictions.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
@app.route("/students/<int:student_id>/report")
def student_report(student_id):

    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    student = connection.execute(
        """
        SELECT *
        FROM students
        WHERE id = ?
        """,
        (student_id,)
    ).fetchone()

    connection.close()

    if student is None:
        return "Student not found", 404

    output = BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=10
    )

    normal_style = styles["BodyText"]

    elements = []

    elements.append(
        Paragraph(
            "STUDENT PERFORMANCE REPORT",
            title_style
        )
    )

    elements.append(
        Paragraph(
            "Student Performance Prediction System",
            ParagraphStyle(
                "Subtitle",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=10,
                spaceAfter=20
            )
        )
    )

    student_info = [
        ["Student ID", student["student_id"]],
        ["Student Name", student["name"]],
    ]

    student_table = Table(
        student_info,
        colWidths=[150, 300]
    )

    student_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(student_table)

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            "Academic Information",
            heading_style
        )
    )

    academic_data = [
        ["Parameter", "Value"],
        ["Attendance", f"{student['attendance']}%"],
        ["Study Hours", str(student["study_hours"])],
        ["Previous Score", str(student["previous_score"])],
        ["Assignment Score", str(student["assignment_score"])],
        ["Internal Score", str(student["internal_score"])],
        ["Sleep Hours", str(student["sleep_hours"])],
        ["Participation", str(student["participation"])],
    ]

    academic_table = Table(
        academic_data,
        colWidths=[250, 200]
    )

    academic_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(academic_table)

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            "Prediction Result",
            heading_style
        )
    )

    predicted_score = student["predicted_score"] or 0

    result_data = [
        ["Metric", "Result"],
        [
            "Predicted Final Score",
            f"{predicted_score:.2f}/100"
        ],
        [
            "Performance",
            student["performance"]
        ],
        [
            "Risk Level",
            student["risk_level"]
        ],
    ]

    result_table = Table(
        result_data,
        colWidths=[250, 200]
    )

    result_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(result_table)

    elements.append(Spacer(1, 25))

    elements.append(
        Paragraph(
            "Prediction generated using the Random Forest "
            "Regression machine learning model.",
            ParagraphStyle(
                "Footer",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=9
            )
        )
    )

    document.build(elements)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=(
            f"{student['student_id']}_performance_report.pdf"
        ),
        mimetype="application/pdf"
    )
def get_performance(score):

    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Average"
    else:
        return "At Risk"


def get_risk_level(score):

    if score >= 70:
        return "Low"
    elif score >= 50:
        return "Medium"
    else:
        return "High"
@app.route("/predict", methods=["GET", "POST"])
def predict():

    if "username" not in session:
        return redirect(url_for("login"))

    prediction = None
    performance = None
    risk_level = None
    error = None

    if request.method == "POST":

        try:
            attendance = float(request.form["attendance"])
            study_hours = float(request.form["study_hours"])
            previous_score = float(request.form["previous_score"])
            assignment_score = float(request.form["assignment_score"])
            internal_score = float(request.form["internal_score"])
            sleep_hours = float(request.form["sleep_hours"])
            participation = float(request.form["participation"])

            if not 0 <= attendance <= 100:
                raise ValueError(
                    "Attendance must be between 0 and 100."
                )

            if study_hours < 0:
                raise ValueError(
                    "Study hours cannot be negative."
                )

            if not 0 <= previous_score <= 100:
                raise ValueError(
                    "Previous score must be between 0 and 100."
                )

            if not 0 <= assignment_score <= 100:
                raise ValueError(
                    "Assignment score must be between 0 and 100."
                )

            if not 0 <= internal_score <= 100:
                raise ValueError(
                    "Internal score must be between 0 and 100."
                )

            if sleep_hours < 0:
                raise ValueError(
                    "Sleep hours cannot be negative."
                )

            if not 0 <= participation <= 10:
                raise ValueError(
                    "Participation must be between 0 and 10."
                )

            input_data = [[
                attendance,
                study_hours,
                previous_score,
                assignment_score,
                internal_score,
                sleep_hours,
                participation
            ]]

            prediction = float(
                model.predict(input_data)[0]
            )

            prediction = max(
                0,
                min(100, prediction)
            )

            performance = get_performance(prediction)
            risk_level = get_risk_level(prediction)

        except Exception as e:
            error = str(e)

    return render_template(
        "predict.html",
        prediction=prediction,
        performance=performance,
        risk_level=risk_level,
        error=error
    )    
if __name__ == "__main__":

    initialize_database()

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5001

    )