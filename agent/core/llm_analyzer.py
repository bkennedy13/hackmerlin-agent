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
        """Extract spelled out letters using LLM to arrange them properly."""
        
        # Method 1: Look for clear letter patterns first
        pattern_match = re.search(r'([A-Z](?:[\s,\-]+[A-Z]){2,})', response)
        if pattern_match:
            letters = re.findall(r'[A-Z]', pattern_match.group(1))
            if len(letters) >= 3:
                # Use LLM to arrange these letters into the most likely word
                letters_str = ', '.join(letters)
                prompt = f'Letters: {letters_str}\nWhat English word uses exactly these letters? Just the word:'
                
                try:
                    result = self._call_ollama(prompt)
                    word = self._clean_result(result)
                    if word and len(word) >= 3:
                        return [word]
                except:
                    pass
        
        # Method 2: Fallback - just join the letters directly
        caps_letters = re.findall(r'\b[A-Z]\b', response)
        if len(caps_letters) >= 3:
            word = ''.join(caps_letters)
            return [word]
        
        return []
    
    def _extract_reverse(self, response: str) -> List[str]:
        """Extract and reverse backwards word."""
        
        # Method 1: Look for exactly one all-caps word (3-15 letters)
        caps_words = re.findall(r'\b[A-Z]{3,15}\b', response)
        if len(caps_words) == 1:
            reversed_word = caps_words[0][::-1]
            return [reversed_word]
        
        # Method 2: If response is just one word (no spaces), reverse it
        stripped = re.sub(r'[^A-Za-z]', '', response.strip())
        if stripped and len(stripped) >= 3 and len(stripped) <= 15:
            reversed_word = stripped[::-1].upper()
            return [reversed_word]
        
        # Method 3: LLM fallback only if no clear single word found
        prompt = f'Text: "{response}"\nFind the backwards word and spell it forwards. Just the word:'
        
        try:
            result = self._call_ollama(prompt)
            word = self._clean_result(result)
            if word and len(word) >= 3 and len(word) <= 15:
                return [word]
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