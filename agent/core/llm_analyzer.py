import requests
import json
import re
import logging
from typing import List
import re
from spellchecker import SpellChecker

logger = logging.getLogger(__name__)

class LLMAnalyzer:
    """Ultra-simplified pattern recognition with very direct prompts."""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
    
    def extract_passwords(self, response: str, strategy_used: str, question_asked: str) -> List[str]:
        """Extract using strategy-specific ultra-simple prompts."""
        
        if strategy_used == "direct":
            return self._extract_direct(response)
        elif strategy_used == "spelling":
            return self._extract_spelling(response)
        elif strategy_used == "reverse":
            return self._extract_reverse(response)
        elif strategy_used == "letters":
            return self._extract_letters(response)
        elif strategy_used == "acronym":
            return self._extract_acronym(response)
        else:
            return self._extract_generic(response)
    
    def _extract_direct(self, response: str) -> List[str]:
        """Extract direct password mention."""
        # Find all words that are all caps and 3+ letters
        caps_words = re.findall(r'\b[A-Z]{3,15}\b', response)
        
        # If exactly one all-caps word, return it
        if len(caps_words) == 1:
            logger.info(f"Direct extracted (single caps word): {caps_words[0]}")
            return [caps_words[0]]
        
        # Otherwise, proceed with LLM
        prompt = f'Text: "{response}"\nFind the password word. Just the word:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word:
                logger.info(f"Direct extracted: {word}")
                return [word]
        except Exception as e:
            logger.error(f"Direct extraction failed: {e}")
        return []
    
    def _extract_spelling(self, response: str) -> List[str]:
        """Extract spelled out letters - fix spelling by looking for same or longer words."""        
        and_pattern = re.search(r'([A-Z](?:\s*,\s*[A-Z])*)\s*,?\s*and\s+([A-Z])', response, re.IGNORECASE)

        if and_pattern:
            # Get all letters before 'and' plus the letter after 'and'
            letters_before = re.findall(r'[A-Za-z]', and_pattern.group(1))
            letter_after = and_pattern.group(2)
            letters = letters_before + [letter_after]
            if len(letters) >= 3:
                word = ''.join(letters).upper()
                fixed_word = self._try_fix_spelling_common(word)
                logger.info(f"Spelling extracted (with 'and'): {fixed_word}")
                return [fixed_word]
    
        
        # Pattern 1: Letters with separators
        patterns = [
            r'(?:^|[^A-Za-z])([A-Z](?:\s*[-,\.]\s*[A-Z]){2,})(?:[^A-Za-z]|$)',
            r'(?:^|\s)([A-Z](?:\s+[A-Z]){2,})(?:\s|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                letters = re.findall(r'[A-Za-z]', match)
                if len(letters) >= 3:
                    word = ''.join(letters)
                    fixed_word = self._try_fix_spelling_common(word)
                    logger.info(f"Spelling extracted: {fixed_word}")
                    return [fixed_word]
        
        # Pattern 2: Dots
        dots_letters = re.findall(r'([A-Z])\.{2,}', response, re.IGNORECASE)
        if len(dots_letters) >= 3:
            word = ''.join(dots_letters)
            fixed_word = self._try_fix_spelling_common(word)
            logger.info(f"Spelling extracted (dots): {fixed_word}")
            return [fixed_word]
        
        # Pattern 3: Isolated single letters
        single_letters = re.findall(r'\b[A-Z]\b', response, re.IGNORECASE)
        if 3 <= len(single_letters) <= 10:
            word = ''.join(single_letters)
            fixed_word = self._try_fix_spelling_common(word)
            logger.info(f"Spelling extracted (isolated): {fixed_word}")
            return [fixed_word]
        
        return []
        
    def _extract_reverse(self, response: str) -> List[str]:
        """Extract and reverse backwards word."""
        
        # Method 1: Look for exactly one all-caps word (3-15 letters)
        caps_words = re.findall(r'\b[A-Z]{3,15}\b', response)
        if len(caps_words) == 1:
            reversed_word = caps_words[0][::-1]
            fixed_word = self._try_fix_spelling_common(reversed_word)
            logger.info(f"Reverse extracted (caps): {fixed_word}")
            return [fixed_word]
        
        # Method 2: If response is just one word (no spaces), reverse it
        stripped = re.sub(r'[^A-Za-z]', '', response.strip())
        if stripped and 3 <= len(stripped) <= 15:
            reversed_word = stripped[::-1].upper()
            fixed_word = self._try_fix_spelling_common(reversed_word)
            logger.info(f"Reverse extracted (stripped): {fixed_word}")
            return [fixed_word]
        
        # Method 3: LLM fallback only if no clear single word found
        prompt = f'Text: "{response}"\nFind the backwards word and spell it forwards. Just the word:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word and 3 <= len(word) <= 15:
                fixed_word = self._try_fix_spelling_common(word)
                logger.info(f"Reverse extracted (LLM): {fixed_word}")
                return [fixed_word]
        except Exception as e:
            logger.error(f"Reverse extraction failed: {e}")
        
        return []
    
    def _clean_result(self, text: str) -> str:
        """Extract a clean candidate from an LLM reply without latching onto THE/KEY/etc."""

        if not text:
            return ""

        STOPWORDS = {
            "THE","AND","CAN","CODE","WORD","WORDS","PASSWORD","SECRET","HIDDEN",
            "PLEASE","CANNOT","INCANTATION","WILL","MUST","ACCESS","KEY"
        }

        t = text.strip()

        # 1) If the model already summarized it, prefer that.
        m = re.search(r'(?:combined|full)\s+word\s+is[:\s]+([A-Za-z]{3,20})', t, flags=re.I)
        if m:
            return m.group(1).upper()

        # 2) Join spelled-out letters like "T - H - U - N - D - E - R" or "J, I, G, S, A, W"
        #    Prefer when the reply mentions "letters"/"spell(s)" but also catch generic patterns.
        # 2a) After "letters"/"spells"
        m = re.search(r'(letters?|spells?)\s*[^A-Za-z]*([A-Za-z,\s\-–—]+)', t, flags=re.I)
        if m:
            letters = re.findall(r'[A-Za-z]', m.group(2))
            if len(letters) >= 3:
                return ''.join(letters).upper()

        # 2b) Generic hyphen/comma/space-separated single letters anywhere
        m = re.search(r'\b(?:[A-Za-z]\s*(?:-|–|—|,|\s)){2,}[A-Za-z]\b', t)
        if m:
            letters = re.findall(r'[A-Za-z]', m.group(0))
            if len(letters) >= 3:
                return ''.join(letters).upper()

        # 3) Quoted word:  The word you seek is "REVERIE".
        q = re.findall(r'"([A-Za-z]{3,20})"', t)
        if q:
            return q[-1].upper()

        # 4) Phrase templates: "the password/word is X"
        m = re.search(r'\b(?:password|secret|code|word)\b.*?\bis\b[:\s"]*([A-Za-z]{3,20})', t, flags=re.I)
        if m:
            return m.group(1).upper()

        # 5) Last resort: first reasonable token, skipping obvious junk
        for w in re.findall(r'\b[A-Za-z]{3,20}\b', t):
            W = w.upper()
            if W not in STOPWORDS:
                return W

        return ""
    
    def _extract_acronym(self, response: str) -> List[str]:
        """Extract first letters from lines."""
        # For poem lines starting with C-H-E-R-R-Y should return "CHERRY"
        prompt = f'Text: "{response}"\nFirst letter of each phrase spells:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word:
                logger.info(f"Acronym extracted: {word}")
                return [word]
        except Exception as e:
            logger.error(f"Acronym extraction failed: {e}")
        return []
    
    def _clean_result(self, text: str) -> str:
        """Extract clean word from response."""

        if not text:
            return ""
        
        # Just get the first word that looks like a password
        words = re.findall(r'\b[A-Z]{3,15}\b', text.upper())
        if words:
            return words[0]
        
        # Fallback: any word
        words = re.findall(r'\b[A-Za-z]{3,15}\b', text)
        if words:
            return words[0].upper()
        
        return ""
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama with minimal settings.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 10,  # Very short - just the word
            }
        }
        
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['response']
        else:
            raise Exception(f"Ollama API failed: {response.status_code}")
         
    def _extract_letters(self, response: str) -> List[str]:
        """Extract from partial letter clues using LLM for completion."""
        from spellchecker import SpellChecker
        spell = SpellChecker()
        
        # Parse the response for letter clues
        first_letters = ""
        last_letters = ""
        
        # Pattern 1: "first X letters are ABC"
        first_match = re.search(r'first\s+\d+\s+letters?\s+(?:are|is)\s+([A-Z]{2,})', response, re.IGNORECASE)
        if first_match:
            first_letters = first_match.group(1).upper()
            logger.info(f"Found first letters: {first_letters}")
        
        # Pattern 2: "last X letters are XYZ"
        last_match = re.search(r'last\s+\d+\s+letters?\s+(?:are|is)\s+([A-Z]{2,})', response, re.IGNORECASE)
        if last_match:
            last_letters = last_match.group(1).upper()
            logger.info(f"Found last letters: {last_letters}")
        
        # Pattern 3: Just letters listed
        if not first_letters and not last_letters:
            # Look for pattern like "S, A, F" or "S A F"
            letter_pattern = re.findall(r'\b[A-Z]\b', response)
            if 2 <= len(letter_pattern) <= 4:
                partial = ''.join(letter_pattern)
                logger.info(f"Found partial letters: {partial}")
                first_letters = partial
        
        # Use LLM to complete the word if we have partial info
        if first_letters or last_letters:
            prompt_parts = []
            if first_letters:
                prompt_parts.append(f"starts with {first_letters}")
            if last_letters:
                prompt_parts.append(f"ends with {last_letters}")
            
            prompt = f"Common English word that {' and '.join(prompt_parts)}. One word:"
            
            try:
                result = self._call_ollama(prompt)
                word = self._clean_result(result)
                
                # Verify it matches our constraints
                if word:
                    word_upper = word.upper()
                    if first_letters and not word_upper.startswith(first_letters):
                        logger.info(f"LLM word {word_upper} doesn't match first letters {first_letters}")
                        return []
                    if last_letters and not word_upper.endswith(last_letters):
                        logger.info(f"LLM word {word_upper} doesn't match last letters {last_letters}")
                        return []
                    
                    # Spellcheck the result
                    if spell.known([word.lower()]) or len(word) >= 10:
                        logger.info(f"Letters extracted (LLM): {word_upper}")
                        return [word_upper]
                    else:
                        # Try to fix spelling
                        fixed = self._try_fix_spelling(word_upper)
                        if fixed != word_upper:
                            logger.info(f"Letters extracted (LLM, corrected): {fixed}")
                            return [fixed]
                        return [word_upper]
            except Exception as e:
                logger.error(f"Letters LLM extraction failed: {e}")
        
        return []

    def _try_fix_spelling_common(self, word: str) -> str:
        """Try to fix word by finding valid COMMON words of same length or longer."""
        from spellchecker import SpellChecker
        spell = SpellChecker()
        
        word_lower = word.lower()
        
        # If already valid AND common, return as-is
        if spell.known([word_lower]):
            # Check if it's a common word (high frequency)
            word_freq = spell.word_frequency[word_lower]
            if word_freq > 1e-6:  # Threshold for common words
                return word.upper()
        
        # Only try to fix words under 10 letters
        if len(word) >= 10:
            return word.upper()
        
        # Try adding each letter of the alphabet to see if it makes a valid word
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        candidates = []
        
        # Try inserting a letter at each position
        for pos in range(len(word_lower) + 1):
            for letter in alphabet:
                candidate = word_lower[:pos] + letter + word_lower[pos:]
                if spell.known([candidate]):
                    # Check frequency
                    if spell.word_frequency[candidate] > 1e-6:
                        candidates.append(candidate)
        
        # Try replacing each letter
        for pos in range(len(word_lower)):
            for letter in alphabet:
                if letter != word_lower[pos]:
                    candidate = word_lower[:pos] + letter + word_lower[pos+1:]
                    if spell.known([candidate]) and len(candidate) >= len(word_lower):
                        # Check frequency
                        if spell.word_frequency[candidate] > 1e-6:
                            candidates.append(candidate)
        
        # If we found valid COMMON candidates, prefer those that are longer
        if candidates:
            # Sort by frequency (more common first), then by length
            candidates.sort(key=lambda x: (spell.word_frequency[x], len(x)), reverse=True)
            result = candidates[0].upper()
            if result != word.upper():
                logger.info(f"Spelling corrected: {word.upper()} -> {result}")
            return result
        
        # No common word found, return original
        return word.upper()