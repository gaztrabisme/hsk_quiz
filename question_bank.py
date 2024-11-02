from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math
import random

@dataclass
class QuestionState:
    difficulty: float = 1.0
    times_shown: int = 0
    times_correct: int = 0
    consecutive_wrong: int = 0
    last_5_attempts: List[bool] = field(default_factory=list)
    time_to_answer: List[float] = field(default_factory=list)
    last_seen: Optional[datetime] = None
    mastery_level: float = 0.0  # 0 to 1
    category: str = ""

class QuestionBank:
    def __init__(self, questions_data: dict):
        self.questions = {q['id']: q for q in questions_data['questions']}
        self.states = {qid: QuestionState(category=q['category'])
                      for qid, q in self.questions.items()}
        self.category_stats = self._initialize_category_stats()

    def _initialize_category_stats(self) -> Dict[str, Dict]:
        categories = set(q['category'] for q in self.questions.values())
        return {cat: {'total_attempts': 0, 'correct_attempts': 0}
                for cat in categories}

    def calculate_pattern_score(self, qid: int) -> float:
        state = self.states[qid]

        # base difficulty
        score = state.difficulty

        # pattern analysis
        if len(state.last_5_attempts) >= 5:
            recent_performance = state.last_5_attempts[-5:]
            early_correct = sum(recent_performance[:3])
            late_correct = sum(recent_performance[3:])

            if early_correct > late_correct:  # getting worse
                score *= 1.5
            elif early_correct < late_correct:  # improving
                score *= 0.8

        # speed analysis
        if state.time_to_answer:
            recent_times = state.time_to_answer[-5:]
            avg_time = sum(recent_times) / len(recent_times)
            speed_factor = min(2.0, avg_time / 5.0)
            score *= speed_factor

        # apply time decay
        decay = self.calculate_decay(qid)
        score *= decay

        return score

    def calculate_decay(self, qid: int) -> float:
        state = self.states[qid]
        if not state.last_seen:
            return 1.0

        days_passed = (datetime.now() - state.last_seen).days
        decay = 1.0 - (state.mastery_level * (1 - math.exp(-days_passed/30)))
        return decay

    def calculate_category_difficulty(self, category: str) -> float:
        cat_questions = [qid for qid, q in self.questions.items()
                        if q['category'] == category]
        if not cat_questions:
            return 1.0
        return sum(self.states[qid].difficulty for qid in cat_questions) / len(cat_questions)

    def select_questions(self, n: int = 50) -> List[int]:
        # adjust n based on difficulty
        avg_difficulty = sum(s.difficulty for s in self.states.values()) / len(self.states)
        fatigue_factor = len([s for s in self.states.values() if s.difficulty > 3]) / len(self.states)
        adjusted_n = int(n * (1 - (fatigue_factor * 0.3)))

        # calculate scores for all questions
        question_scores = []
        for qid in self.questions:
            pattern_score = self.calculate_pattern_score(qid)
            cat_difficulty = self.calculate_category_difficulty(self.questions[qid]['category'])

            # combine individual and category difficulty
            final_score = pattern_score * 0.7 + cat_difficulty * 0.3
            question_scores.append((qid, final_score))

        question_scores.sort(key=lambda x: x[1], reverse=True)

        # select questions by priority
        high_priority = [q[0] for q in question_scores[:int(adjusted_n * 0.6)]]
        untested = [qid for qid in self.questions if self.states[qid].times_shown == 0]
        random_pool = list(set(self.questions.keys()) - set(high_priority) - set(untested))

        selected = (
            random.sample(high_priority, min(len(high_priority), int(adjusted_n * 0.6))) +
            random.sample(untested, min(len(untested), int(adjusted_n * 0.3))) +
            random.sample(random_pool, min(len(random_pool), int(adjusted_n * 0.1)))
        )

        # fill remaining slots if needed
        while len(selected) < adjusted_n:
            remaining = list(set(self.questions.keys()) - set(selected))
            if not remaining:
                break
            selected.append(random.choice(remaining))

        random.shuffle(selected)
        return selected[:adjusted_n]

    def update_question_state(self, qid: int, correct: bool, time_taken: float):
        state = self.states[qid]
        category = self.questions[qid]['category']

        # update basic stats
        state.times_shown += 1
        state.last_seen = datetime.now()
        state.time_to_answer.append(time_taken)
        state.last_5_attempts.append(correct)
        if len(state.last_5_attempts) > 5:
            state.last_5_attempts.pop(0)

        # update category stats
        self.category_stats[category]['total_attempts'] += 1
        if correct:
            self.category_stats[category]['correct_attempts'] += 1

        # update mastery and difficulty
        if correct:
            state.times_correct += 1
            state.consecutive_wrong = 0
            state.mastery_level = min(1.0, state.mastery_level + 0.1)
            state.difficulty = max(1.0, state.difficulty * 0.8)
        else:
            state.consecutive_wrong += 1
            state.mastery_level = max(0.0, state.mastery_level - 0.2)
            difficulty_increase = 2.0 * (1 + state.consecutive_wrong * 0.5)
            state.difficulty += difficulty_increase

    def get_category_stats(self) -> Dict[str, Dict]:
        stats = {}
        for cat, base_stats in self.category_stats.items():
            stats[cat] = {
                'total_attempts': base_stats['total_attempts'],
                'correct_attempts': base_stats['correct_attempts'],
                'accuracy': (base_stats['correct_attempts'] / base_stats['total_attempts']
                           if base_stats['total_attempts'] > 0 else 0),
                'avg_difficulty': self.calculate_category_difficulty(cat)
            }
        return stats

    def export_state(self) -> dict:
        return {
            'states': {
                qid: {
                    'difficulty': state.difficulty,
                    'times_shown': state.times_shown,
                    'times_correct': state.times_correct,
                    'consecutive_wrong': state.consecutive_wrong,
                    'last_5_attempts': state.last_5_attempts,
                    'mastery_level': state.mastery_level,
                    'last_seen': state.last_seen.isoformat() if state.last_seen else None
                }
                for qid, state in self.states.items()
            },
            'category_stats': self.category_stats,
            'timestamp': datetime.now().isoformat()
        }

    @classmethod
    def import_state(cls, questions_data: dict, state_data: dict) -> 'QuestionBank':
        bank = cls(questions_data)
        for qid, state_dict in state_data['states'].items():
            qid = int(qid)
            bank.states[qid].difficulty = state_dict['difficulty']
            bank.states[qid].times_shown = state_dict['times_shown']
            bank.states[qid].times_correct = state_dict['times_correct']
            bank.states[qid].consecutive_wrong = state_dict['consecutive_wrong']
            bank.states[qid].last_5_attempts = state_dict['last_5_attempts']
            bank.states[qid].mastery_level = state_dict['mastery_level']
            if state_dict['last_seen']:
                bank.states[qid].last_seen = datetime.fromisoformat(state_dict['last_seen'])

        bank.category_stats = state_data.get('category_stats', bank._initialize_category_stats())
        return bank
