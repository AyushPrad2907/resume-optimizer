import re
import string
from flask import Flask, request, jsonify, send_from_directory
import pdfplumber

app = Flask(__name__)

# A simple list of common English stop words to filter out
STOP_WORDS = set([
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in",
    "is", "it", "no", "not", "of", "on", "or", "so", "that", "the", "this",
    "to", "was", "with", "from", "were", "has", "have", "had", "will", "would",
    "should", "can", "could"
])

def extract_keywords(text):
    """
    Extracts a list of cleaned, unique keywords from a given text.
    It converts the text to lowercase, removes punctuation, and filters out stop words.
    """
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Split the text into words
    words = text.split()
    # Filter out stop words and return a set of unique words
    return set(word for word in words if word not in STOP_WORDS)

def generate_suggestions(score, missing_keywords):
    """
    Generates tailored suggestions based on the ATS score and missing keywords.
    """
    suggestions = []
    if score < 40:
        suggestions.append("Your resume is missing many key terms from the job description.")
        suggestions.append("Suggestions: Try to tailor your resume more closely to the specific requirements. Use the exact keywords from the JD where applicable.")
    elif 40 <= score <= 70:
        suggestions.append("You have a good match, but there is room for improvement.")
        suggestions.append("Suggestions: Review the missing keywords and add them to your resume. Make sure to use strong action verbs and quantify your achievements.")
    else:
        suggestions.append("Excellent match! Your resume is highly aligned with the job description.")
        suggestions.append("Suggestions: Your resume looks great. Consider adding more details to showcase your projects and experiences, and proofread carefully.")

    if missing_keywords:
        missing_str = ", ".join(list(missing_keywords)[:10]) # Show up to 10 missing keywords
        suggestions.append(f"Specifically, consider adding these missing keywords: {missing_str}")

    return suggestions

@app.route('/')
def index():
    """Serves the index.html file."""
    return send_from_directory('.', 'index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Main endpoint to analyze the resume against the job description.
    """
    try:
        # Get data from the request
        jd_text = request.form['jd']
        resume_file = request.files['resume']

        # Read text from the PDF file
        resume_text = ""
        with pdfplumber.open(resume_file) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""
        
        if not resume_text:
            return jsonify({"error": "Could not extract text from the resume PDF. Please ensure the file is not an image scan."}), 400

        # Extract keywords from both texts
        jd_keywords = extract_keywords(jd_text)
        resume_keywords = extract_keywords(resume_text)

        # Find matched and missing keywords
        matched_keywords = jd_keywords.intersection(resume_keywords)
        missing_keywords = jd_keywords.difference(resume_keywords)
        
        total_jd_keywords = len(jd_keywords)
        matched_count = len(matched_keywords)

        # Calculate ATS Score
        if total_jd_keywords == 0:
            ats_score = 0
        else:
            ats_score = round((matched_count / total_jd_keywords) * 100)

        # Determine Probability
        probability = "Low"
        if ats_score > 70:
            probability = "High"
        elif ats_score > 40:
            probability = "Medium"

        # Generate suggestions
        suggestions = generate_suggestions(ats_score, missing_keywords)

        # Return the results as JSON
        return jsonify({
            "ats_score": ats_score,
            "probability": probability,
            "missing_keywords": sorted(list(missing_keywords)),
            "suggestions": suggestions
        })

    except Exception as e:
        # Log the error for debugging purposes
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred while processing your request."}), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
