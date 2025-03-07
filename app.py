from flask import Flask, request, render_template, redirect, flash
import PyPDF2
import docx
import re
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname="resume_parser",
        user="postgres",  # Replace with your PostgreSQL username
        password="shivanirao1710",  # Replace with your PostgreSQL password
        host="localhost"
    )
    return conn

# Extract text from PDF
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Extract text from Word document
def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Parse resume text
def parse_resume(text):
    data = {
        "name": "",
        "email": "",
        "phone": "",
        "skills": "",
        "experience": "",
        "education": "",
        "projects": ""
    }

    # Extract email
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", text, re.IGNORECASE)
    if emails:
        data["email"] = emails[0]

    # Extract phone number
    phones = re.findall(r"\+?\d[\d -]{8,12}\d", text)
    if phones:
        data["phone"] = phones[0]

    # Extract name (first line as a placeholder)
    data["name"] = text.split("\n")[0].strip()

    # Extract skills (improved keyword matching)
    skills_list = [
        "python", "java", "sql", "flask", "django", "postgresql", "machine learning", "data analysis",
        "javascript", "html", "css", "react", "node.js", "aws", "docker", "git", "rest api", "mongodb"
    ]
    found_skills = []
    for skill in skills_list:
        if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE):
            found_skills.append(skill)
    data["skills"] = ", ".join(found_skills)

    # Extract experience (look for section headers and extract the following text)
    experience_keywords = ["experience", "work history", "employment", "professional experience"]
    experience_text = ""
    for keyword in experience_keywords:
        if keyword.lower() in text.lower():
            start_index = text.lower().find(keyword.lower())
            # Extract text until the next section or end of document
            end_index = find_next_section(text, start_index)
            experience_text = text[start_index:end_index].strip()
            break
    data["experience"] = experience_text

    # Extract education (look for section headers and extract the following text)
    education_keywords = ["education", "academic background", "degrees", "qualifications"]
    education_text = ""
    for keyword in education_keywords:
        if keyword.lower() in text.lower():
            start_index = text.lower().find(keyword.lower())
            # Extract text until the next section or end of document
            end_index = find_next_section(text, start_index)
            education_text = text[start_index:end_index].strip()
            break
    data["education"] = education_text

    # Extract projects (look for section headers and extract the following text)
    projects_keywords = ["projects", "personal projects", "project experience"]
    projects_text = ""
    for keyword in projects_keywords:
        if keyword.lower() in text.lower():
            start_index = text.lower().find(keyword.lower())
            # Extract text until the next section or end of document
            end_index = find_next_section(text, start_index)
            projects_text = text[start_index:end_index].strip()
            break
    data["projects"] = projects_text

    # Debugging: Print out the parsed sections
    print("Experience Text: ", data["experience"])
    print("Education Text: ", data["education"])
    print("Projects Text: ", data["projects"])

    return data

# Helper function to find the next section
def find_next_section(text, start_index):
    # Look for common section headers
    section_headers = ["experience", "education", "projects", "skills", "certifications", "achievements"]
    next_index = len(text)
    for header in section_headers:
        header_index = text.lower().find(header, start_index + 1)
        if header_index != -1 and header_index < next_index:
            next_index = header_index
    return next_index

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "resume" not in request.files:
        flash("No file uploaded!")
        return redirect("/")

    file = request.files["resume"]
    if file.filename == "":
        flash("No file selected!")
        return redirect("/")

    # Extract text based on file type
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(file)
    elif file.filename.endswith(".docx") or file.filename.endswith(".doc"):
        text = extract_text_from_docx(file)
    else:
        flash("Unsupported file format! Please upload a PDF or DOCX file.")
        return redirect("/")

    # Parse resume text
    parsed_data = parse_resume(text)

    # Save to database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO resumes (name, email, phone, skills, experience, education, projects, file_name) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (parsed_data["name"], parsed_data["email"], parsed_data["phone"],
             parsed_data["skills"], parsed_data["experience"], parsed_data["education"],
             parsed_data["projects"], file.filename)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Resume uploaded and parsed successfully!")
        return redirect("/display")

    except Exception as e:
        print("Error inserting into database:", e)
        flash("Error uploading resume. Please try again.")
        return redirect("/")

# Display parsed data
@app.route("/display", methods=["GET"])
def display():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM resumes ORDER BY id DESC LIMIT 1")  # Fetch the latest resume
    resume_data = cur.fetchone()
    cur.close()
    conn.close()

    if resume_data:
        return render_template("display.html", resume=resume_data)
    else:
        flash("No resume data found!")
        return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
