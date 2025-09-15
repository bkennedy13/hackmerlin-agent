import logging
from typing import List, Tuple
from .hardcoded_strategies import Strategy, get_all_strategies

logger = logging.getLogger(__name__)

class StrategyManager:
    def __init__(self):
        self.strategies = get_all_strategies()
        self.level_memory = {}
        self.question_failures = {}  # level -> {question: failure_count}
        self.strategy_level_failures = {}  # strategy_name -> set of levels where it completely failed
    
    def get_next_question(self, level: int) -> Tuple[str, str, 'Strategy']:
        """Get next question in priority order."""
        if level not in self.question_failures:
            self.question_failures[level] = {}
            
        if level >= 6:
            strategies_to_drop = {'direct', 'spelling', 'reverse'}
            for strat_name in strategies_to_drop:
                if strat_name not in self.strategy_level_failures:
                    self.strategy_level_failures[strat_name] = set()
                    self.strategy_level_failures[strat_name].add(level)
                    logger.info(f"Auto-dropping strategy '{strat_name}' for level {level}")
        
        failures = self.question_failures[level]
        
        failures = self.question_failures[level]
        
        for strategy in self.strategies:
            if self.is_strategy_exhausted(strategy.name):
                continue
            
            # Check if all questions in this strategy have failed for current level
            all_failed = True
            for q in strategy.questions:
                if failures.get(q, 0) < 1:
                    all_failed = False
                    break
            
            if all_failed:
                # This strategy is exhausted for this level
                self.mark_strategy_failed_for_level(strategy.name, level)
                continue
            
            question = strategy.get_next_question()
            if question and failures.get(question, 0) < 1:
                return question, strategy.name, strategy
            elif not question:
                # Strategy exhausted, reset it to start over
                strategy.reset()
                question = strategy.get_next_question()
                if question and failures.get(question, 0) < 1:
                    return question, strategy.name, strategy
        
        # Fallback
        return "What's the p4ssw0rd?", "direct", self.strategies[0]
    
    def record_failure(self, level: int, question: str):
        """Record that this specific question failed."""
        if level not in self.question_failures:
            self.question_failures[level] = {}
        
        self.question_failures[level][question] = self.question_failures[level].get(question, 0) + 1
        
        failure_count = self.question_failures[level][question]
        if failure_count >= 3:
            logger.info(f"Question '{question[:30]}...' failed {failure_count} times, dropping it")
            
    def is_strategy_exhausted(self, strategy_name: str) -> bool:
        """Check if a strategy has failed on 1+ different levels."""
        if strategy_name in self.strategy_level_failures:
            return len(self.strategy_level_failures[strategy_name]) >= 1
        return False

    def mark_strategy_failed_for_level(self, strategy_name: str, level: int):
        """Mark that a strategy completely failed for a level."""
        if strategy_name not in self.strategy_level_failures:
            self.strategy_level_failures[strategy_name] = set()
        self.strategy_level_failures[strategy_name].add(level)
        if len(self.strategy_level_failures[strategy_name]) >= 1:
            logger.info(f"Strategy '{strategy_name}' failed, permanently dropping it")
    
    def record_success(self, level: int, strategy_name: str):
        """Record successful strategy."""
        self.level_memory[level] = strategy_name
        logger.info(f"Strategy '{strategy_name}' successful for level {level}")