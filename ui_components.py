import streamlit as st
import json
import time
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def show_feedback(question: dict, selected_option: str, is_correct: bool):
    if is_correct:
        st.success("✨ Correct! ✨", icon="🎯")
    else:
        st.error(f"Not quite! The correct answer was: {question['correct_answer'].upper()}. {question['options'][question['correct_answer']]}", icon="💡")

    # continue button
    if st.button("Continue →", use_container_width=True):
        st.rerun()

def show_question(question, session):
    st.write(f"### Question {session.stats.correct + session.stats.wrong + session.stats.skipped + 1}/50")

    # Show question and difficulty indicator
    qid = session.current_round[0]
    difficulty = session.bank.states[qid].difficulty
    difficulty_emoji = "🔥" if difficulty > 5 else "⚡" if difficulty > 3 else "❄️"

    st.write(f"### {difficulty_emoji} {question['question']}")
    st.write(f"Category: {question['category']}")

    # track if an answer was selected
    answer_selected = False

    # Answer options in columns
    cols = st.columns(4)
    for i, (opt_key, opt_value) in enumerate(question['options'].items()):
        if cols[i].button(f"{opt_key.upper()}. {opt_value}",
                         key=f"opt_{opt_key}_{qid}",  # unique key
                         use_container_width=True):
            is_correct = opt_key == question['correct_answer']
            session.handle_answer(is_correct)
            answer_selected = True

            if is_correct:
                st.success("✨ Correct! ✨", icon="🎯")
            else:
                st.error(f"Not quite! The correct answer was: {question['correct_answer'].upper()}. {question['options'][question['correct_answer']]}", icon="💡")

    # only show continue button after answer
    if answer_selected and st.button("Continue →",
                                   key=f"continue_{qid}",
                                   use_container_width=True):
        st.rerun()

    # skip button with unique key
    if st.button("Skip for now",
                 key=f"skip_{qid}",
                 use_container_width=True):
        session.handle_skip()
        st.rerun()

def show_advanced_stats(session):
    stats = session.get_advanced_stats()

    st.write("## 📊 Advanced Statistics")

    # Create tabs for different stat categories
    tab1, tab2, tab3 = st.tabs(["Category Performance", "Session Stats", "Difficulty Analysis"])

    with tab1:
        # Convert category stats to DataFrame for easier plotting
        cat_data = []
        for cat, data in stats['category_performance'].items():
            cat_data.append({
                'Category': cat,
                'Accuracy': data['accuracy'] * 100,
                'Difficulty': data['avg_difficulty'],
                'Total Attempts': data['total_attempts']
            })
        df_cat = pd.DataFrame(cat_data)

        # Create bubble chart
        fig = px.scatter(df_cat,
                        x='Accuracy',
                        y='Difficulty',
                        size='Total Attempts',
                        color='Category',
                        title='Category Performance Overview')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Show detailed stats in expandable sections
        for cat, data in stats['category_performance'].items():
            with st.expander(f"📝 {cat} Details"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Accuracy", f"{data['accuracy']*100:.1f}%")
                col2.metric("Avg Difficulty", f"{data['avg_difficulty']:.1f}")
                col3.metric("Total Attempts", data['total_attempts'])

                if 'avg_time' in data:
                    st.metric("Average Answer Time", f"{data['avg_time']:.1f}s")

    with tab2:
        # Session performance metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Questions per Minute",
                   f"{stats['session_stats']['questions_per_minute']:.1f}")
        col2.metric("Session Accuracy",
                   f"{stats['session_stats']['accuracy']*100:.1f}%")
        col3.metric("Best Streak", stats['session_stats']['best_streak'])

        # Session duration in MM:SS format
        duration = int(stats['session_stats']['duration'])
        st.metric("Session Duration",
                 f"{duration//60}:{duration%60:02d}")

    with tab3:
        # Difficulty distribution pie chart
        diff_data = stats['difficulty_distribution']
        fig = go.Figure(data=[go.Pie(
            labels=['Easy', 'Medium', 'Hard'],
            values=[diff_data['easy'], diff_data['medium'], diff_data['hard']],
            hole=.3
        )])
        fig.update_layout(title_text="Question Difficulty Distribution")
        st.plotly_chart(fig, use_container_width=True)

def show_stats(session):
    st.sidebar.title("Quiz Stats")

    # initialize state for advanced stats toggle if not exists
    if 'show_advanced_stats' not in st.session_state:
        st.session_state.show_advanced_stats = False

    # Basic stats with emojis
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        st.metric("✅", session.stats.correct)
    with col2:
        st.metric("❌", session.stats.wrong)
    with col3:
        st.metric("⏭️", session.stats.skipped)

    # Streak display with dynamic emoji
    streak_emoji = "🔥" if session.stats.streak >= 3 else "📈"
    st.sidebar.write(f"{streak_emoji} Current Streak: {session.stats.streak}")
    st.sidebar.write(f"🏆 Best Streak: {session.stats.best_streak}")

    # Get current question's difficulty indicator
    if session.current_round:
        current_q = session.current_round[0]
        difficulty = session.bank.states[current_q].difficulty
        difficulty_emoji = "🔥" if difficulty > 5 else "⚡" if difficulty > 3 else "❄️"
        st.sidebar.write(f"{difficulty_emoji} Current Question Difficulty: {difficulty:.1f}")

    st.sidebar.divider()

    # Controls
    if st.sidebar.button("↻ New Round", use_container_width=True):
        session.start_round()
        st.rerun()

    # Toggle advanced stats
    if st.sidebar.button(
        "📊 Advanced Stats " + ("(Hide)" if st.session_state.show_advanced_stats else "(Show)"),
        use_container_width=True
    ):
        st.session_state.show_advanced_stats = not st.session_state.show_advanced_stats
        st.rerun()

    # Only show advanced stats if toggled
    if st.session_state.show_advanced_stats:
        show_advanced_stats(session)

    # Save functionality with combined data
    if st.sidebar.button("💾 Save Progress", use_container_width=True):
        export_data = {
            'bank_state': session.bank.export_state(),
            'session_stats': session.get_advanced_stats()
        }
        st.sidebar.download_button(
            "📥 Download Progress",
            data=json.dumps(export_data, indent=2),
            file_name="quiz_progress.json",
            mime="application/json"
        )

def show_round_summary(session):
    st.success("🎉 Round Complete!")

    # show stats in a more visual way
    cols = st.columns(3)
    with cols[0]:
        st.metric("Correct Answers", session.stats.correct)
    with cols[1]:
        st.metric("Wrong Answers", session.stats.wrong)
    with cols[2]:
        st.metric("Questions Skipped", session.stats.skipped)

    # calculate accuracy
    total_answered = session.stats.correct + session.stats.wrong
    accuracy = (session.stats.correct / total_answered * 100) if total_answered > 0 else 0

    st.write(f"### 📊 Round Performance")
    st.write(f"Accuracy: {accuracy:.1f}%")
    st.write(f"Best Streak: {session.stats.best_streak} 🔥")
