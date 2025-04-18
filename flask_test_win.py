import os
from flask import Flask, json, request, jsonify
from flask_mysqldb import MySQL, MySQLdb
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
import re
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('punkt_tab')
nltk.download('stopwords')
import pymysql
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'sql12.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql12774029'
app.config['MYSQL_PASSWORD'] = 'WPIf4sUYbz'
app.config['MYSQL_DB'] = 'sql12774029'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

<<<<<<< Updated upstream
db_username = os.getenv('DB_USERNAME', 'sql12774029')
db_password = os.getenv('DB_PASSWORD', 'WPIf4sUYbz')
db_host = os.getenv('DB_HOST', 'sql12.freesqldatabase.com')
db_name = os.getenv('DB_NAME', 'sql12774029')

engine = create_engine(f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}')
=======
engine = create_engine('mysql+pymysql://sql12774029:WPIf4sUYbz@sql12.freesqldatabase.com/sql12774029')
>>>>>>> Stashed changes

@app.route('/', methods=['GET'])
def process_role_description():
    applicant_id = request.args.get('applicant_id', 10, type=int)
    fetch_job_skills = """
        SELECT company.CompanyName, joblistings.JobListingID, joblistings.JobTitle, joblistings.JobDescription, jobcategories.CategoryName, jobcategories.CategoryDescription, jobroles.RoleName, jobroles.RoleDescription
        FROM joblistings
        INNER JOIN jobcategories ON joblistings.JobCategoryID = jobcategories.JobCategoryID
        INNER JOIN jobroles ON joblistings.JobRoleID = jobroles.JobRoleID
        INNER JOIN company ON joblistings.CompanyID = company.CompanyID
        WHERE joblistings.JobListingID
    """
    applicant_skills_query = """
        SELECT applicantskills.ApplicantID, skills.SkillName, skills.SkillDescription
        FROM applicantskills
        INNER JOIN skills ON applicantskills.SkillID = skills.SkillID 
        WHERE applicantskills.ApplicantID = %s
    """

    sql_cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    sql_cursor.execute(applicant_skills_query, (applicant_id,))
    applicant_skills = pd.DataFrame(sql_cursor.fetchall())

    sql_cursor.execute(fetch_job_skills)
    job_skills = pd.DataFrame(sql_cursor.fetchall())

    category_description = job_skills[['CategoryName', 'CategoryDescription', 'JobListingID', 'CompanyName', 'JobTitle', 'JobDescription']].drop_duplicates(subset=['CategoryDescription'])
    role_description = job_skills[['RoleName', 'RoleDescription', 'JobListingID']].drop_duplicates(subset=['RoleDescription'])

    category_description = category_description.drop_duplicates(subset=['CategoryDescription'])
    category_description['CategoryDescription'] = category_description['CategoryDescription'].str.lower()
    category_description['CategoryDescription'] = category_description['CategoryDescription'].apply(lambda x: re.sub(r'[^a-zA-Z]', ' ', x))
    category_description['CategoryDescription'] = category_description['CategoryDescription'].apply(lambda x: re.sub(r'\s+', ' ', x))

    role_description = role_description.drop_duplicates(subset=['RoleDescription'])
    role_description['RoleDescription'] = role_description['RoleDescription'].str.lower()
    role_description['RoleDescription'] = role_description['RoleDescription'].apply(lambda x: re.sub(r'[^a-zA-Z]', ' ', x))
    role_description['RoleDescription'] = role_description['RoleDescription'].apply(lambda x: re.sub(r'\s+', ' ', x))

    stop_words = nltk.corpus.stopwords.words('english')
    category_description['CategoryDescription'] = category_description['CategoryDescription'].apply(
        lambda x: ' '.join([word for word in nltk.word_tokenize(x) if word not in stop_words ])
    )

    applicant_skills_filtered = applicant_skills[applicant_skills['ApplicantID'] == applicant_id]

    combined_skills = ' '.join(applicant_skills_filtered['SkillDescription'].str.lower().tolist())
    combined_skills = re.sub(r'[^a-zA-Z]', ' ', combined_skills)
    combined_skills = re.sub(r'\s+', ' ', combined_skills).strip()

    tfidf = TfidfVectorizer()
    features = tfidf.fit_transform(category_description['CategoryDescription'])
    applicant_skill_features = tfidf.transform([combined_skills])

    category_similarity_scores = cosine_similarity(applicant_skill_features, features).flatten()

    top_similar_skills = sorted(
        [(idx, score) for idx, score in enumerate(category_similarity_scores) if score > 0.0],
        key=lambda x: x[1], 
        reverse=True
    )[:10]

    if not top_similar_skills:
        return jsonify({"message": "No recommendations found."}), 404

    recommendations = {
        "JobIndex": applicant_id,
        "ApplicantSkillsDescription": combined_skills,
        "Recommendations": [
            {
                "JobListingID": int(category_description['JobListingID'].iloc[idx]),
                "CompanyName": category_description['CompanyName'].iloc[idx],
                "JobTitle": category_description['JobTitle'].iloc[idx],
                "JobDescription": category_description['JobDescription'].iloc[idx],
                "CategoryDescription": category_description['CategoryDescription'].iloc[idx],
                "CategoryName": category_description['CategoryName'].iloc[idx],
            }
            for idx, score, in top_similar_skills
        ]
    }

    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True)
