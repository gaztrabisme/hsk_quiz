from question_bank import QuestionBank
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class SessionStats:
    correct: int = 0
    wrong: int = 0
    skipped: int = 0
    streak: int = 0
    best_streak: int = 0
    start_time: float = field(default_factory=time.time)
    question_start_time: float = field(default_factory=time.time)
    times_per_category: Dict[str, List[float]] = field(default_factory=dict)

class QuizSession:
    def __init__(self, bank: QuestionBank):
        self.bank = bank
        self.current_round: List[int] = []
        self.skipped: List[int] = []
        self.stats = SessionStats()

    def start_round(self, n: int = 50):
        self.current_round = self.bank.select_questions(n)
        self.skipped = []
        self.stats = SessionStats()
        self.stats.question_start_time = time.time()

    def handle_answer(self, correct: bool):
        if not self.current_round:
            return

        qid = self.current_round.pop(0)
        time_taken = time.time() - self.stats.question_start_time

        # update question bank with timing info
        self.bank.update_question_state(qid, correct, time_taken)

        # update session stats
        category = self.bank.questions[qid]['category']
        if category not in self.stats.times_per_category:
            self.stats.times_per_category[category] = []
        self.stats.times_per_category[category].append(time_taken)

        if correct:
            self.stats.correct += 1
            self.stats.streak += 1
            self.stats.best_streak = max(self.stats.best_streak, self.stats.streak)
        else:
            self.stats.wrong += 1
            self.stats.streak = 0

        # reset timer for next question
        self.stats.question_start_time = time.time()

    def handle_skip(self):
        if not self.current_round:
            return

        self.skipped.append(self.current_round.pop(0))
        self.stats.skipped += 1
        self.stats.question_start_time = time.time()

    def get_advanced_stats(self) -> dict:
        # get category performance
        category_stats = self.bank.get_category_stats()

        # add timing data from current session
        for category, times in self.stats.times_per_category.items():
            if category in category_stats:
                category_stats[category]['avg_time'] = sum(times) / len(times) if times else 0

        # get overall session stats
        session_duration = time.time() - self.stats.start_time

        return {
            'category_performance': category_stats,
            'session_stats': {
                'duration': session_duration,
                'questions_per_minute': (self.stats.correct + self.stats.wrong) / (session_duration / 60) if session_duration > 0 else 0,
                'accuracy': self.stats.correct / (self.stats.correct + self.stats.wrong) if (self.stats.correct + self.stats.wrong) > 0 else 0,
                'streak': self.stats.streak,
                'best_streak': self.stats.best_streak
            },
            'difficulty_distribution': {
                'easy': len([s for s in self.bank.states.values() if s.difficulty <= 2]),
                'medium': len([s for s in self.bank.states.values() if 2 < s.difficulty <= 4]),
                'hard': len([s for s in self.bank.states.values() if s.difficulty > 4])
            }
        }

    def is_round_complete(self):
        return not self.current_round and not self.skipped
