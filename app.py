import streamlit as st
import json
from datetime import datetime
import re
import requests

# =============================================================================
# BRANDING - ResumeMatch
# =============================================================================
APP_NAME = "ResumeMatch"
APP_TAGLINE = "AI-Powered Resume Analysis & Job Matching"
APP_ICON = "📄"
# =============================================================================

# Import document processing libraries
try:
    from pypdf import PdfReader
    import pdfplumber
except ImportError:
    st.error("Run: pip install pypdf pdfplumber")

try:
    from docx import Document as DocxDocument
except ImportError:
    st.error("Run: pip install python-docx")

# Page configuration
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS - Blue Theme
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    
    .score-container {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .section-header {
        color: #0f172a;
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #2563eb;
        padding-bottom: 0.5rem;
    }
    
    .strength {
        color: #10b981;
        font-weight: 500;
    }
    
    .weakness {
        color: #ef4444;
        font-weight: 500;
    }
    
    .neutral {
        color: #2563eb;
        font-weight: 500;
    }
    
    .stButton>button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        border: none;
    }
    
    .stButton>button:hover {
        background-color: #1e40af;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .metric-card {
        background-color: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        color: #1e293b;
    }
    
    .app-header {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .app-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .app-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)


def extract_text_from_pdf(file):
    """Extract text from PDF"""
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except:
        try:
            file.seek(0)
            reader = PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            st.error(f"PDF extraction failed: {str(e)}")
            return None
    return text.strip()


def extract_text_from_docx(file):
    """Extract text from DOCX"""
    try:
        doc = DocxDocument(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        st.error(f"DOCX extraction failed: {str(e)}")
        return None


def extract_keywords(text):
    """Extract keywords from text"""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
    
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9\.\-]*\b', text.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    from collections import Counter
    return Counter(keywords)


def calculate_keyword_match(resume_text, job_text):
    """Calculate keyword matching"""
    resume_keywords = extract_keywords(resume_text)
    job_keywords = extract_keywords(job_text)
    
    common_keywords = set(resume_keywords.keys()) & set(job_keywords.keys())
    
    if len(job_keywords) > 0:
        match_percentage = (len(common_keywords) / len(job_keywords)) * 100
    else:
        match_percentage = 0
    
    top_job_keywords = [k for k, v in job_keywords.most_common(20)]
    matched = [k for k in top_job_keywords if k in resume_keywords]
    missing = [k for k in top_job_keywords if k not in resume_keywords]
    
    return {
        'match_percentage': match_percentage,
        'matched_keywords': matched[:10],
        'missing_keywords': missing[:10]
    }


def analyze_with_free_ai(resume_text, job_description):
    """FREE AI analysis using Hugging Face (NO API KEY NEEDED!)"""
    
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    
    resume_snippet = resume_text[:2500]
    job_snippet = job_description[:1500]
    
    prompt = f"""Analyze resume vs job. Be professional.

RESUME:
{resume_snippet}

JOB:
{job_snippet}

Return ONLY this JSON (no other text):
{{
  "match_score": 75,
  "overall_assessment": "Professional 2-3 sentence summary",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "experience_score": 75,
  "skills_score": 80,
  "education_score": 70,
  "recommendations": ["tip 1", "tip 2", "tip 3"]
}}"""

    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 800,
                    "temperature": 0.5,
                    "return_full_text": False
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
            elif isinstance(result, dict):
                generated_text = result.get('generated_text', '')
            else:
                return None
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', generated_text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
                required = ['match_score', 'overall_assessment', 'strengths', 'weaknesses', 'recommendations']
                if all(field in analysis_data for field in required):
                    return analysis_data
        
        return None
    except:
        return None


def rule_based_analysis(resume_text, job_description, keyword_analysis):
    """Advanced rule-based analysis"""
    
    resume_lower = resume_text.lower()
    job_lower = job_description.lower()
    
    keyword_score = min(keyword_analysis['match_percentage'], 100)
    
    has_experience = any(word in resume_lower for word in ['experience', 'work', 'employment', 'worked'])
    has_education = any(word in resume_lower for word in ['education', 'degree', 'university', 'bachelor', 'master'])
    has_skills = any(word in resume_lower for word in ['skills', 'technologies', 'proficient'])
    has_achievements = any(word in resume_lower for word in ['achieved', 'improved', 'increased', 'reduced', 'led'])
    has_metrics = bool(re.search(r'\d+%|\$\d+|\d+\+', resume_text))
    
    experience_score = 85 if (has_experience and has_achievements) else (70 if has_experience else 45)
    education_score = 80 if has_education else 50
    skills_score = min(int(keyword_score * 0.9 + 15), 100)
    
    if has_metrics:
        experience_score = min(experience_score + 10, 100)
    
    overall_score = int(
        (keyword_score * 0.40) + 
        (experience_score * 0.30) + 
        (skills_score * 0.20) + 
        (education_score * 0.10)
    )
    
    strengths = []
    if len(keyword_analysis['matched_keywords']) >= 8:
        strengths.append(f"Excellent keyword alignment with {len(keyword_analysis['matched_keywords'])} key terms")
    elif len(keyword_analysis['matched_keywords']) >= 5:
        strengths.append(f"Good keyword coverage with {len(keyword_analysis['matched_keywords'])} relevant terms")
    
    if has_experience and has_achievements:
        strengths.append("Strong track record with documented achievements")
    elif has_experience:
        strengths.append("Relevant work experience clearly presented")
    
    if has_metrics:
        strengths.append("Quantified accomplishments with specific metrics")
    
    if has_skills:
        strengths.append("Technical skills clearly highlighted")
    
    if len(strengths) < 3:
        strengths.append("Resume is well-formatted and professional")
    
    weaknesses = []
    if len(keyword_analysis['missing_keywords']) >= 7:
        weaknesses.append(f"Missing {len(keyword_analysis['missing_keywords'])} important keywords")
    elif len(keyword_analysis['missing_keywords']) >= 4:
        weaknesses.append(f"Could add {len(keyword_analysis['missing_keywords'])} more relevant terms")
    
    if not has_metrics:
        weaknesses.append("Add quantifiable achievements with numbers and percentages")
    
    if not has_achievements:
        weaknesses.append("Include more action verbs and accomplishments")
    
    if keyword_score < 50:
        weaknesses.append("Needs better alignment with job requirements")
    
    if len(weaknesses) < 3:
        weaknesses.append("Consider adding more specific examples")
    
    recommendations = []
    if len(keyword_analysis['missing_keywords']) > 0:
        top = ', '.join(keyword_analysis['missing_keywords'][:3])
        recommendations.append(f"Add these keywords if applicable: {top}")
    
    if not has_metrics:
        recommendations.append("Add specific numbers and percentages to quantify impact")
    else:
        recommendations.append("Expand quantifiable results across all sections")
    
    if keyword_score < 70:
        recommendations.append("Mirror the job description language in your resume")
    else:
        recommendations.append("Feature most relevant experience at the top")
    
    if overall_score >= 80:
        assessment = "Excellent match. Strong alignment with job requirements and relevant qualifications."
    elif overall_score >= 65:
        assessment = "Good match. Solid qualifications with room for targeted keyword optimization."
    elif overall_score >= 50:
        assessment = "Moderate match. Relevant elements present but needs better highlighting of skills."
    else:
        assessment = "Fair match. Significantly tailor resume to emphasize transferable skills."
    
    return {
        'match_score': overall_score,
        'overall_assessment': assessment,
        'strengths': strengths[:3],
        'weaknesses': weaknesses[:3],
        'experience_score': experience_score,
        'skills_score': skills_score,
        'education_score': education_score,
        'recommendations': recommendations[:3]
    }


def analyze_resume(resume_text, job_description):
    """Main analysis - tries FREE AI first, uses rule-based as backup"""
    
    with st.spinner("Analyzing keywords..."):
        keyword_analysis = calculate_keyword_match(resume_text, job_description)
    
    st.info("Attempting AI analysis... (30-60 seconds)")
    ai_analysis = analyze_with_free_ai(resume_text, job_description)
    
    if ai_analysis:
        st.success("AI analysis complete!")
        analysis = ai_analysis
        analysis['keyword_matches'] = keyword_analysis['matched_keywords']
        analysis['missing_skills'] = keyword_analysis['missing_keywords']
        
        ats_score = min(int(keyword_analysis['match_percentage'] * 0.75 + 25), 100)
        
        if ats_score < 70:
            ats_issues = ["Low keyword density", "May not pass automated screening"]
            ats_improvements = ["Add more relevant keywords", "Use standard section headings"]
        else:
            ats_issues = ["Good keyword coverage"]
            ats_improvements = ["Continue using industry terminology", "Maintain clear structure"]
        
        analysis['ats_compatibility'] = {
            'score': ats_score,
            'issues': ats_issues,
            'improvements': ats_improvements
        }
        
        analysis['experience_alignment'] = {
            'score': analysis.get('experience_score', 70),
            'summary': 'Based on work history'
        }
        analysis['skills_alignment'] = {
            'score': analysis.get('skills_score', 70),
            'summary': f'Matched {len(keyword_analysis["matched_keywords"])} skills'
        }
        analysis['education_alignment'] = {
            'score': analysis.get('education_score', 70),
            'summary': 'Based on education'
        }
        
        return analysis
    else:
        st.info("Using advanced keyword analysis")
        analysis = rule_based_analysis(resume_text, job_description, keyword_analysis)
        
        analysis['keyword_matches'] = keyword_analysis['matched_keywords']
        analysis['missing_skills'] = keyword_analysis['missing_keywords']
        
        ats_score = min(int(keyword_analysis['match_percentage'] * 0.75 + 25), 100)
        
        if ats_score < 60:
            ats_issues = ["Limited keyword optimization", "May struggle with ATS"]
            ats_improvements = ["Increase keyword density", "Mirror job description terms", "Use standard headers"]
        elif ats_score < 75:
            ats_issues = ["Moderate ATS compatibility"]
            ats_improvements = ["Add more industry keywords", "Use bullet points"]
        else:
            ats_issues = ["Strong ATS compatibility"]
            ats_improvements = ["Maintain keyword strategy", "Keep clear formatting"]
        
        analysis['ats_compatibility'] = {
            'score': ats_score,
            'issues': ats_issues,
            'improvements': ats_improvements
        }
        
        analysis['experience_alignment'] = {
            'score': analysis['experience_score'],
            'summary': 'Based on work history'
        }
        analysis['skills_alignment'] = {
            'score': analysis['skills_score'],
            'summary': f'{len(keyword_analysis["matched_keywords"])} matching keywords'
        }
        analysis['education_alignment'] = {
            'score': analysis['education_score'],
            'summary': 'Based on education'
        }
        
        return analysis


def display_score(score, label):
    """Display score with color"""
    if score >= 80:
        color = "#10b981"
    elif score >= 60:
        color = "#f59e0b"
    else:
        color = "#ef4444"
    
    st.markdown(f"""
    <div style="background-color: {color}; color: white; padding: 1.5rem; 
                border-radius: 8px; text-align: center; margin: 1rem 0;">
        <div style="font-size: 3rem; font-weight: bold;">{score}%</div>
        <div style="font-size: 1.1rem; opacity: 0.9;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def main():
    # Header
    st.markdown(f"""
    <div class="app-header">
        <div class="app-title">{APP_NAME}</div>
        <div class="app-subtitle">{APP_TAGLINE}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### About {APP_NAME}")
        st.markdown("""
        Professional resume analysis using advanced AI:
        
        - Calculate job match scores
        - Identify strengths and weaknesses
        - Get actionable recommendations
        - Check ATS compatibility
        - Analyze skills alignment
        
        Upload your resume and job description to begin.
        """)
        
        st.markdown("---")
        st.markdown("### How It Works")
        st.markdown("""
        1. Upload resume (PDF or DOCX)
        2. Paste job description
        3. Click 'Analyze Resume'
        4. Review insights
        """)
        
        st.markdown("---")
        st.markdown("### 100% Free")
        st.markdown("""
        Completely free to use.
        No registration.
        No API keys.
        No costs.
        """)
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="section-header">Resume Upload</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload your resume",
            type=['pdf', 'docx'],
            help="Supported: PDF, DOCX"
        )
        
        if uploaded_file:
            st.text(f"File: {uploaded_file.name}")
            st.text(f"Size: {uploaded_file.size / 1024:.2f} KB")
    
    with col2:
        st.markdown('<div class="section-header">Job Description</div>', unsafe_allow_html=True)
        job_description = st.text_area(
            "Paste job description",
            height=200,
            placeholder="Paste the complete job description..."
        )
    
    st.markdown("---")
    
    if st.button("Analyze Resume", type="primary"):
        if not uploaded_file:
            st.error("Please upload a resume first.")
            return
        
        if not job_description or len(job_description.strip()) < 50:
            st.error("Please provide a complete job description (min 50 characters).")
            return
        
        # Extract text
        with st.spinner("Extracting text..."):
            if uploaded_file.type == "application/pdf":
                resume_text = extract_text_from_pdf(uploaded_file)
            else:
                resume_text = extract_text_from_docx(uploaded_file)
            
            if not resume_text or len(resume_text.strip()) < 100:
                st.error("Could not extract text. Ensure file contains readable text.")
                return
        
        # Analyze
        analysis = analyze_resume(resume_text, job_description)
        
        if not analysis:
            st.error("Analysis failed. Please try again.")
            return
        
        # Results
        st.markdown("---")
        st.markdown("## Analysis Results")
        
        # Overall Score
        st.markdown('<div class="section-header">Overall Match Score</div>', unsafe_allow_html=True)
        display_score(analysis['match_score'], "Match Score")
        
        # Assessment
        st.markdown('<div class="section-header">Overall Assessment</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; color: #1e293b; font-size: 1.05rem;'>{analysis['overall_assessment']}</div>", unsafe_allow_html=True)
        
        # Detailed Scores
        st.markdown('<div class="section-header">Detailed Analysis</div>', unsafe_allow_html=True)
        
        score_col1, score_col2, score_col3 = st.columns(3)
        
        with score_col1:
            display_score(analysis['experience_alignment']['score'], "Experience")
            st.markdown(f"<small>{analysis['experience_alignment']['summary']}</small>", unsafe_allow_html=True)
        
        with score_col2:
            display_score(analysis['skills_alignment']['score'], "Skills")
            st.markdown(f"<small>{analysis['skills_alignment']['summary']}</small>", unsafe_allow_html=True)
        
        with score_col3:
            display_score(analysis['education_alignment']['score'], "Education")
            st.markdown(f"<small>{analysis['education_alignment']['summary']}</small>", unsafe_allow_html=True)
        
        # Strengths & Weaknesses
        st.markdown('<div class="section-header">Key Insights</div>', unsafe_allow_html=True)
        
        strength_col, weakness_col = st.columns(2)
        
        with strength_col:
            st.markdown("#### Strengths")
            for strength in analysis['strengths']:
                st.markdown(f"<span class='strength'>✓</span> {strength}", unsafe_allow_html=True)
        
        with weakness_col:
            st.markdown("#### Areas for Improvement")
            for weakness in analysis['weaknesses']:
                st.markdown(f"<span class='weakness'>✗</span> {weakness}", unsafe_allow_html=True)
        
        # Missing Keywords
        if analysis['missing_skills']:
            st.markdown('<div class="section-header">Missing Keywords</div>', unsafe_allow_html=True)
            st.markdown("Important terms from job description not found in resume:")
            
            cols = st.columns(min(3, len(analysis['missing_skills'])))
            for idx, skill in enumerate(analysis['missing_skills']):
                with cols[idx % len(cols)]:
                    st.markdown(f"<div style='background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; color: #1e293b;'><span style='color: #ef4444; font-weight: 500;'>⚠</span> {skill}</div>", unsafe_allow_html=True)
        
        # Matched Keywords
        if analysis['keyword_matches']:
            st.markdown('<div class="section-header">Matched Keywords</div>', unsafe_allow_html=True)
            st.markdown("Keywords successfully included:")
            
            keyword_cols = st.columns(min(3, len(analysis['keyword_matches'])))
            for idx, keyword in enumerate(analysis['keyword_matches']):
                with keyword_cols[idx % len(keyword_cols)]:
                    st.markdown(f"<div style='background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; color: #1e293b;'><span style='color: #10b981; font-weight: 500;'>✓</span> {keyword}</div>", unsafe_allow_html=True)
        
        # ATS Compatibility
        st.markdown('<div class="section-header">ATS Compatibility</div>', unsafe_allow_html=True)
        
        display_score(analysis['ats_compatibility']['score'], "ATS Score")
        
        ats_col1, ats_col2 = st.columns(2)
        
        with ats_col1:
            st.markdown("#### Status")
            for issue in analysis['ats_compatibility']['issues']:
                st.markdown(f"- {issue}")
        
        with ats_col2:
            st.markdown("#### Recommendations")
            for improvement in analysis['ats_compatibility']['improvements']:
                st.markdown(f"- {improvement}")
        
        # Recommendations
        st.markdown('<div class="section-header">Action Items</div>', unsafe_allow_html=True)
        
        for idx, rec in enumerate(analysis['recommendations'], 1):
            st.markdown(f"<div style='background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; color: #1e293b;'><strong>{idx}.</strong> {rec}</div>", unsafe_allow_html=True)
        
        # Download
        st.markdown("---")
        
        report = {
            "date": datetime.now().isoformat(),
            "file": uploaded_file.name,
            "analysis": analysis
        }
        
        st.download_button(
            label="Download Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()
