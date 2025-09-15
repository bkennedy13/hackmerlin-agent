import logging
import re
from typing import Dict, List, Set
from spellchecker import SpellChecker

logger = logging.getLogger(__name__)

class LetterCluesManager:
    """Manages letter clues for level 6+ passwords."""
    
    def __init__(self):
        self.level_clues = {}  # level -> {'responses': [], 'candidates': set()}
        self.spell = SpellChecker()
    
    def add_clue(self, level: int, question: str, response: str):
        """Store a clue response for analysis."""
        if level not in self.level_clues:
            self.level_clues[level] = {'responses': [], 'candidates': set()}
        
        self.level_clues[level]['responses'].append({
            'question': question,
            'response': response
        })
        logger.info(f"Stored clue for level {level}: {response[:50]}")
    
    def analyze_clues(self, level: int, llm_analyzer) -> List[str]:
        """Analyze all clues for a level and generate password candidates."""
        if level not in self.level_clues:
            return []
        
        clues = self.level_clues[level]['responses']
        if len(clues) < 2:  # Need at least 2 clues to work with
            return []
        
        # Extract letter fragments from all responses
        fragments = []
        for clue in clues:
            response = clue['response']
            question = clue['question']
            
            # Extract any capital letter sequences or mixed case words (like "Gob")
            # Include both all-caps and title-case words
            letter_sequences = re.findall(r'\b[A-Z]{2,10}\b|\b[A-Z][a-z]{1,9}\b', response)
            for seq in letter_sequences:
                fragments.append({
                    'letters': seq.upper(),
                    'question_type': self._classify_question(question),
                    'full_response': response
                })
        
        if not fragments:
            return []
        
        # Deduplicate overlapping fragments
        unique_fragments = []
        for frag in fragments:
            is_substring = False
            for other in fragments:
                if frag['letters'] != other['letters'] and frag['letters'] in other['letters']:
                    is_substring = True
                    break
            if not is_substring:
                unique_fragments.append(frag)
        fragments = unique_fragments if unique_fragments else fragments
        
        # First, try simple direct combinations
        candidates = self._try_direct_combinations(fragments)
        
        # If we found good candidates, return them
        if candidates:
            return candidates[:3]
        
        # Otherwise, use LLM
        prompt = self._build_llm_prompt(fragments)
        
        try:
            # Use the LLM to suggest complete words
            result = llm_analyzer._call_ollama(prompt)
            candidates = self._parse_llm_suggestions(result)
            
            # Validate candidates are real words
            valid_candidates = []
            for word in candidates:
                if self.spell.known([word.lower()]) or len(word) >= 10:
                    valid_candidates.append(word.upper())
                    logger.info(f"Valid candidate from clues: {word.upper()}")
            
            return valid_candidates[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Letter clues analysis failed: {e}")
            
            # Fallback: try simple combinations
            return self._fallback_combine(fragments)
    
    def _try_direct_combinations(self, fragments: List[Dict]) -> List[str]:
        """Try directly combining first and last fragments."""
        first_frags = [f['letters'] for f in fragments if f['question_type'] == 'first']
        last_frags = [f['letters'] for f in fragments if f['question_type'] == 'last']
        
        candidates = []
        
        # Try all combinations of first + last
        for first in first_frags:
            for last in last_frags:
                # Direct concatenation
                word = first + last
                if self.spell.known([word.lower()]):
                    candidates.append(word)
                    logger.info(f"Direct combination found: {word}")
                
                # Try with one letter overlap (common pattern)
                if first[-1] == last[0]:
                    word = first + last[1:]
                    if self.spell.known([word.lower()]):
                        candidates.append(word)
                        logger.info(f"Overlap combination found: {word}")
        
        return candidates
    
    def _classify_question(self, question: str) -> str:
        """Classify what type of letter question this is."""
        question_lower = question.lower()
        if 'first' in question_lower:
            return 'first'
        elif 'last' in question_lower:
            return 'last'
        elif 'acronym' in question_lower or 'poem' in question_lower:
            return 'acronym'
        else:
            return 'unknown'
    
    def _build_llm_prompt(self, fragments: List[Dict]) -> str:
        """Build a prompt for the LLM with all fragments."""
        # Collect all letter sequences
        all_letters = []
        first_clues = []
        last_clues = []
        
        for frag in fragments:
            letters = frag['letters']
            q_type = frag['question_type']
            all_letters.append(letters)
            
            if q_type == 'first':
                first_clues.append(letters)
            elif q_type == 'last':
                last_clues.append(letters)
        
        # Simple prompt that encourages direct combination
        prompt = f"Letters found: {', '.join(all_letters)}\n"
        
        if first_clues and last_clues:
            prompt += f"Try combining them directly: {first_clues[0]} + {last_clues[0]}\n"
        
        prompt += "What common English word uses these letters? Just the word:"
        
        return prompt
    
    def _parse_llm_suggestions(self, llm_response: str) -> List[str]:
        """Parse LLM response for word suggestions."""
        words = []
        # Look for any word-like strings
        potential_words = re.findall(r'\b[A-Za-z]{4,15}\b', llm_response)
        
        for word in potential_words:
            word_upper = word.upper()
            # Skip common filler words
            if word_upper not in ['THE', 'AND', 'THAT', 'COULD', 'MATCH', 'WORDS', 'WITH']:
                words.append(word_upper)
        
        return words[:5]  # Return up to 5 suggestions
    
    def _fallback_combine(self, fragments: List[Dict]) -> List[str]:
        """Simple fallback: try combining fragments."""
        candidates = set()
        
        # If we have 2-3 fragments, try combining them
        if len(fragments) >= 2:
            for frag in fragments:
                word = frag['letters']
                if 4 <= len(word) <= 10:
                    candidates.add(word)
        
        return list(candidates)[:3]