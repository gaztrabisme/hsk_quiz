import streamlit as st
import json
from question_bank import QuestionBank
from session import QuizSession
from ui_components import show_question, show_stats, show_round_summary

st.set_page_config(
    page_title="Chinese Quiz",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load progress file handler
def load_progress(uploaded_file):
    try:
        data = json.loads(uploaded_file.getvalue())
        # handle both bank state and session stats
        with open('hsk_quiz.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)

        # create new bank with imported state
        bank = QuestionBank.import_state(questions_data, data['bank_state'])
        st.session_state.quiz_session = QuizSession(bank)
        st.session_state.quiz_session.start_round()

        # show success message with some stats
        st.success(f"Progress loaded! Loaded {len(bank.questions)} questions with performance data.")

    except Exception as e:
        st.error(f"Error loading progress file: {e}")
        return False
    return True

# Initialize session state
if 'quiz_session' not in st.session_state:
    with open('hsk_quiz.json', 'r', encoding='utf-8') as f:
        questions_data = json.load(f)
    bank = QuestionBank(questions_data)
    st.session_state.quiz_session = QuizSession(bank)
    st.session_state.quiz_session.start_round()

# Sidebar for stats and controls
show_stats(st.session_state.quiz_session)

# Handle file upload for progress
st.sidebar.divider()
uploaded_file = st.sidebar.file_uploader("📤 Upload Progress", type="json")
if uploaded_file and 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = uploaded_file.name
    if load_progress(uploaded_file):
        st.rerun()
elif uploaded_file and st.session_state.get('last_uploaded_file') != uploaded_file.name:
    st.session_state.last_uploaded_file = uploaded_file.name
    if load_progress(uploaded_file):
        st.rerun()

# Main quiz interface
st.title("🇨🇳 Chinese Quiz")

# in app.py, modify the main flow:
session = st.session_state.quiz_session

if session.current_round:
    qid = session.current_round[0]
    question = session.bank.questions[qid]
    show_question(question, session)
elif session.skipped:
    st.warning("### 📝 Review skipped questions", icon="⏭️")
    qid = session.skipped[0]
    question = session.bank.questions[qid]
    show_question(question, session)
else:
    show_round_summary(session)
    if st.button("Start New Round →", key="new_round", use_container_width=True):
        session.start_round()
        st.rerun()
