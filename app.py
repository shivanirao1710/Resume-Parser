from flask import Flask, request, render_template, redirect, flash, jsonify
import PyPDF2
import docx
import re
import psycopg2
from transformers import pipeline

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load the LLM model for generating insights and ranking jobs
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

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

# Generate insights using LLM
def generate_insights(text):
    summary = summarizer(text, max_length=100, min_length=30, do_sample=False)
    return summary[0]["summary_text"]

# Extract specific sections
def extract_section(text, keywords):
    for keyword in keywords:
        if keyword.lower() in text.lower():
            start_index = text.lower().find(keyword.lower())
            end_index = find_next_section(text, start_index)
            return text[start_index:end_index].strip()
    return ""

# Find the next section header
def find_next_section(text, start_index):
    section_headers = ["experience", "education", "projects", "skills", "certifications", "achievements"]
    next_index = len(text)
    for header in section_headers:
        header_index = text.lower().find(header, start_index + 1)
        if header_index != -1 and header_index < next_index:
            next_index = header_index
    return next_index
# Dictionary to map skill variations to their canonical form
skill_variations = {
    "nodejs": "node.js",
    "node.js": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "javascript": "js",
    "typescript": "ts",
    "c++": "cpp",
    "c#": "csharp",
    "html5": "html",
    "css3": "css",
    "postgresql": "postgres",
    "mongodb": "mongo",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "kubernetes": "k8s",
    "python3": "python",
    "python2": "python",
    # Add more variations as needed
}
def normalize_skill(skill):
    """Normalize a skill to its canonical form."""
    return skill_variations.get(skill.lower(), skill.lower())

def normalize_text(text):
    """Normalize skill variations in the resume text."""
    for variation, canonical in skill_variations.items():
        text = re.sub(rf"\b{re.escape(variation)}\b", canonical, text, flags=re.IGNORECASE)
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
        "projects": "",
        "insights": ""
    }

    # Normalize the resume text
    text = normalize_text(text)

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

    # Extract skills
    skills_list = [
        # Technical skills (Programming, Web frameworks, Databases, Cloud, etc.)
        "python", "java", "c++", "c#", "ruby", "sql", "html", "css", "javascript", "java swings", "typescript", "php",
        "flask", "django", "nodejs", "expressjs", "react", "reactjs", "nextjs", "angular", "vue.js", "jquery", "bootstrap", "spring", "asp.net",
        "swift", "kotlin", "objective-c", "go", "scala", "perl", "shell scripting", "bash", "powershell", "rust",
        "haskell", "sql server", "postgresql", "mongodb", "mysql", "oracle", "redis", "firebase", "sqlite",
        "hadoop", "spark", "kafka", "elasticsearch", "cassandra", "bigquery", "aws", "azure", "google cloud", "gcp",
        "terraform", "docker", "kubernetes", "ansible", "puppet", "chef", "jenkins", "git", "gitlab", "github", "bitbucket",
        "vagrant", "virtualbox", "jenkins", "ci/cd", "maven", "gradle", "npm", "yarn", "bower", "nginx", "apache",
        "webpack", "graphql", "rest api", "soap", "json", "xml", "protobuf", "swagger", "microservices", "devops",
        "cloudformation", "azure devops", "cloud storage", "cloud architecture", "containerization", "serverless",
        "elastic beanstalk", "lambda", "cloudwatch", "docker swarm", "nginx", "apache kafka", "fluentd", "prometheus",
        "grafana", "openstack", "vagrant", "selenium", "pytest", "junit", "mocha", "chai", "karma", "jasmine",
        "testng", "jupyter", "pandas", "matplotlib", "seaborn", "numpy", "scikit-learn", "tensorflow", "pytorch",
        "keras", "nltk", "spaCy", "openCV", "d3.js", "tableau", "power bi", "matlab", "sas", "r", "spss", "stata",
        "excel", "rds", "spark sql", "sas", "apache flink", "databricks", "etl", "business intelligence", "data mining",
        "data engineering", "data scientist", "etl pipelines", "data lakes", "deep learning", "machine learning",
        "computer vision", "natural language processing", "predictive analytics", "data visualization", "statistics",
        "blockchain", "cryptocurrency", "bitcoin", "ethereum", "iot", "iot protocols", "home automation", "arduino",
        "raspberry pi", "mqtt", "zigbee", "smart contracts", "solidity", "ethereum", "docker", "pytorch", "keras",
        "tensorflow", "scipy", "data wrangling", "jupyter notebooks", "tableau", "google analytics", "splunk",
        "elasticsearch", "salesforce", "service now", "aws lambda", "apache spark", "cloud computing", "cloud migration",
        "blockchain", "nfc", "qr codes", "tcp/ip", "vpn", "pentesting", "ethical hacking", "penetration testing",
        "security", "open security", "ssl", "tls", "http", "oauth", "network security", "firewall", "siem", "firewall",
        "authentication", "authorization", "ssh", "sftp", "ssl", "keycloak", "data encryption", "cybersecurity", "risk management",
        "communication", "teamwork", "leadership", "problem-solving", "creativity", "critical thinking", "time management",
        "adaptability", "collaboration", "conflict resolution", "empathy", "active listening", "negotiation", "presentation",
        "public speaking", "decision making", "attention to detail", "interpersonal skills", "self-motivation", "work ethic",
        "confidentiality", "organizational skills", "stress management", "self-learning", "positive attitude", "customer service",
        "accountability", "delegation", "mentorship", "project management", "resource management", "goal setting",
        "strategic thinking", "analytical thinking", "emotional intelligence", "networking", "team building", "influencing",
        "persuasion", "flexibility", "confidentiality", "coaching", "facilitation", "mindfulness", "decision-making",
        "adaptability", "learning agility", "self-awareness", "conflict management", "collaboration skills", "relationship-building"
    ]

    # Normalize skills in the skills list
    normalized_skills_list = [normalize_skill(skill) for skill in skills_list]

    # Find skills in the resume text
    found_skills = [skill for skill in normalized_skills_list if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE)]
    data["skills"] = ", ".join(found_skills)

    # Extract experience
    experience_keywords = ["experience", "work history", "employment", "professional experience"]
    data["experience"] = extract_section(text, experience_keywords)

    # Extract education
    education_keywords = ["education", "academic background", "degrees", "qualifications"]
    data["education"] = extract_section(text, education_keywords)

    # Extract projects
    projects_keywords = ["projects", "personal projects", "project experience"]
    data["projects"] = extract_section(text, projects_keywords)

    # Generate insights using LLM
    data["insights"] = generate_insights(text)

    return data

# Home page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# Upload and parse resume
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
            INSERT INTO resumes (name, email, phone, skills, experience, education, projects, file_name, insights) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (parsed_data["name"], parsed_data["email"], parsed_data["phone"],
             parsed_data["skills"], parsed_data["experience"], parsed_data["education"],
             parsed_data["projects"], file.filename, parsed_data["insights"])
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

# Display resume data
@app.route("/display", methods=["GET"])
def display():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM resumes ORDER BY id DESC LIMIT 1")
    resume_data = cur.fetchone()
    cur.close()
    conn.close()

    if resume_data:
        return render_template("display.html", resume=resume_data)
    else:
        flash("No resume data found!")
        return redirect("/")

# Get job recommendations
@app.route("/get_jobs", methods=["GET"])
def get_jobs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT skills, experience, projects FROM resumes ORDER BY id DESC LIMIT 1")
        resume_data = cur.fetchone()

        combined_skills = set()
        for skills_field in resume_data:
            combined_skills.update([skill.strip().lower() for skill in skills_field.split(",")])

        cur.execute("SELECT job_role, company_name, company_type, skills FROM jobroles")
        jobs = cur.fetchall()

        recommended_jobs = []
        for job in jobs:
            job_role, company_name, company_type, job_skills = job
            job_skills_set = set(job_skills.lower().split(", "))
            matched_skills = combined_skills.intersection(job_skills_set)
            missing_skills = job_skills_set.difference(combined_skills)

            if matched_skills:
                # Calculate relevance score (percentage of matched skills)
                relevance_score = (len(matched_skills) / len(job_skills_set)) * 100
                relevance_score = round(relevance_score, 2)  # Round to 2 decimal places

                recommended_jobs.append({
                    "job_role": job_role,
                    "company_name": company_name,
                    "company_type": company_type,
                    "skills": job_skills,
                    "matched_skills": ", ".join(matched_skills),
                    "missing_skills": ", ".join(missing_skills),
                    "relevance_score": relevance_score
                })

        # Rank jobs by relevance score (highest first)
        ranked_jobs = sorted(recommended_jobs, key=lambda x: x["relevance_score"], reverse=True)[:5]

        return jsonify({"jobs": ranked_jobs})

    except Exception as e:
        print("Error fetching job recommendations:", e)
        return jsonify({"jobs": []})

if __name__ == "__main__":
    app.run(debug=True)
