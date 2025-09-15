import requests
import json
import re
import logging
from typing import List
import re

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
        stripped = response.strip()
        # Check if it's a single word (no spaces) and all caps
        if ' ' not in stripped and stripped.isupper() and stripped.isalpha():
            logger.info(f"Direct extracted (all caps single word): {stripped}")
            return [stripped]
        
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
        """Extract spelled out letters using regex first, LLM as fallback."""
        
        # Method 1: Direct regex patterns for common spelling formats
        patterns_to_try = [
            # "C - A - R - P - E - T" or "C-A-R-P-E-T"
            r'\b([A-Z]\s*-\s*[A-Z](?:\s*-\s*[A-Z])*)\b',
            # "C A R P E T" (space separated)
            r'\b([A-Z](?:\s+[A-Z]){2,})\b',
            # "C, A, R, P, E, T" (comma separated)
            r'\b([A-Z](?:,\s*[A-Z]){2,})\b',
            # "The letters are: C, A, R, P, E, T" (with prefix)
            r'letters?\s*(?:are|is)?:?\s*([A-Z](?:[\s,-]+[A-Z])+)',
            # "made up of the letters C, A, R, P, E, T"
            r'letters?\s+([A-Z](?:[\s,-]+[A-Z])+)',
        ]
        
        for pattern in patterns_to_try:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                # Extract just the letters
                letters = re.findall(r'[A-Za-z]', match)
                if len(letters) >= 3:  # Must be at least 3 letters
                    word = ''.join(letters).upper()
                    logger.info(f"Spelling extracted (regex): {word}")
                    return [word]
        
        # Method 2: If no clear pattern, try a more targeted LLM prompt
        # But first check if response contains individual letters at all
        single_letters = re.findall(r'\b[A-Z]\b', response.upper())
        if len(single_letters) >= 3:
            # Found individual letters, combine them
            word = ''.join(single_letters)
            logger.info(f"Spelling extracted (single letters): {word}")
            return [word]
        
        # Method 3: LLM fallback with better prompt
        if any(keyword in response.lower() for keyword in ['letter', 'spell', 'each']):
            prompt = f'''Response: "{response}"

    This response contains letters that spell a word. Extract ONLY the letters mentioned and combine them into one word.

    For example:
    - "C - A - R - P - E - T" becomes "CARPET"
    - "The letters are A, B, C" becomes "ABC"

    Word:'''
            
            try:
                result = self._call_ollama(prompt)
                # Clean the result more strictly
                word = self._clean_spelling_result(result, response)
                if word:
                    logger.info(f"Spelling extracted (LLM): {word}")
                    return [word]
            except Exception as e:
                logger.error(f"Spelling extraction LLM failed: {e}")
        
        logger.warning("No spelling pattern found")
        return []

    def _clean_spelling_result(self, llm_result: str, original_response: str) -> str:
        """Clean LLM result for spelling extraction, ensuring it uses the original letters."""
        print(f"LLM result: {llm_result}")
        
        # Extract the word from LLM result
        words = re.findall(r'\b[A-Z]{3,15}\b', llm_result.upper())
        if not words:
            words = re.findall(r'\b[A-Za-z]{3,15}\b', llm_result)
            words = [w.upper() for w in words]
        
        if not words:
            return ""
        
        candidate = words[0]
        
        # Verify the candidate uses letters from the original response
        original_letters = re.findall(r'\b[A-Z]\b', original_response.upper())
        if len(original_letters) >= 3:
            # Check if candidate could be formed from original letters
            from collections import Counter
            original_count = Counter(original_letters)
            candidate_count = Counter(candidate)
            
            # If candidate uses letters not in original, or too many of a letter, reject it
            for letter, count in candidate_count.items():
                if original_count[letter] < count:
                    # Candidate uses letters not available, fall back to direct join
                    fallback = ''.join(original_letters)
                    logger.info(f"LLM result '{candidate}' invalid, using direct join: '{fallback}'")
                    return fallback
        
        return candidate
    
    def _extract_reverse(self, response: str) -> List[str]:
        """Extract and reverse backwards word."""
        # For "YRREHC" should return "CHERRY"
        
        # If the response is a single word (no spaces), reverse it manually
        stripped = response.strip()
        if ' ' not in stripped and stripped:
            reversed_word = stripped[::-1].upper()
            logger.info(f"Reverse extracted manually: {reversed_word}")
            return [reversed_word]
        
        # Otherwise, use LLM
        prompt = f'Text: "{response}"\nFind the backwards word and spell it forwards. Just the word:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word:
                logger.info(f"Reverse extracted: {word}")
                return [word]
        except Exception as e:
            logger.error(f"Reverse extraction failed: {e}")
        return []
    
    def _clean_result(self, text: str) -> str:
        """Extract a clean candidate from an LLM reply without latching onto THE/KEY/etc."""
        print(text)

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
        prompt = f'Text: "{response}"\nFirst letter of each line spells:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word:
                logger.info(f"Acronym extracted: {word}")
                return [word]
        except Exception as e:
            logger.error(f"Acronym extraction failed: {e}")
        return []
    
    def _extract_generic(self, response: str) -> List[str]:
        """Generic extraction."""
        prompt = f'Text: "{response}"\nMain word:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word:
                logger.info(f"Generic extracted: {word}")
                return [word]
        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
        return []
    
    def _clean_result(self, text: str) -> str:
        """Extract clean word from response."""
        print(text)
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
        """Call Ollama with minimal settings."""
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