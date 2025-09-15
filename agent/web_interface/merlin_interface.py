from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

class MerlinInterface:
    """Clean web interface for HackMerlin with working logic from the original."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = self._setup_driver()
        self.current_level = 1
    
    def _setup_driver(self):
        """Setup Chrome WebDriver."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5)
        return driver
    
    def navigate_to_game(self):
        """Navigate to hackmerlin.io and wait for React to load properly."""
        logger.info("Navigating to https://hackmerlin.io")
        self.driver.get("https://hackmerlin.io")
        
        # Clear any existing state
        self.driver.delete_all_cookies()
        self.driver.execute_script("if(window.localStorage) localStorage.clear();")
        self.driver.execute_script("if(window.sessionStorage) sessionStorage.clear();")
        
        # Refresh to start clean
        self.driver.refresh()
        
        try:
            # Wait for the textarea with the exact placeholder
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea[placeholder*='talk to merlin']"))
            )
            
            # Wait for buttons to be clickable (but we won't click them)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button//span[text()='Ask']"))
            )
            
            # Additional wait for React state updates
            time.sleep(3)

            self._update_level()
            
        except Exception as e:
            logger.error(f"Failed to wait for React app: {e}")
            time.sleep(5)
            self._update_level()
    
    def send_message(self, message: str) -> str:
        """Send message using Enter key with proper response detection."""
        try:            
            # Find the textarea with the specific placeholder
            textarea = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea[placeholder*='talk to merlin']"))
            )
            
            # Clear any existing text
            textarea.clear()
            time.sleep(0.5)
            
            # Type the message
            textarea.send_keys(message)
            time.sleep(0.5)
            
            # Store current response to detect changes
            try:
                old_response = self.driver.find_element(By.CSS_SELECTOR, "blockquote p").text
            except:
                old_response = ""
            
            # Submit using Enter key
            textarea.send_keys(Keys.ENTER)
            
            # Wait for response to change using the working logic
            response = self._wait_for_response_change(old_response)
            logger.info(f"Received response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return ""
    
    def submit_password(self, password: str) -> bool:
        """Submit password using Enter key with proper level detection."""
        try:
            logger.info(f"Submitting password: {password}")
            
            # Find password input field
            password_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='SECRET PASSWORD']"))
            )
            
            # Clear and enter password
            password_input.clear()
            time.sleep(0.5)
            password_input.send_keys(password.upper())
            time.sleep(0.5)
            
            # Store current level
            old_level = self.current_level
            
            # Submit using Enter key
            password_input.send_keys(Keys.ENTER)
            
            # Wait for potential level change or popup
            time.sleep(3)
            
            # Handle any popup/modal with Enter (from working version)
            self._handle_popup()
            
            # Update level and check for success
            self._update_level()
            
            success = self.current_level > old_level
            if success:
                logger.info(f"Password correct! Advanced to level {self.current_level}")
                
                # Wait for new level interface to be ready
                time.sleep(2)
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea[placeholder*='talk to merlin']"))
                    )
                    logger.info("New level interface is ready")
                except:
                    logger.warning("New level interface may not be ready yet")
                    
            else:
                logger.info("Password incorrect")
                
            return success
            
        except Exception as e:
            logger.error(f"Error submitting password: {e}")
            return False
    
    def extract_passwords_basic(self, response: str) -> List[str]:
        """Extract passwords using the proven logic from original."""
        if not response or response.strip() == "Hello traveler! Ask me anything...":
            return []
            
        passwords = []
        
        # Pattern 1: Text in double quotes (most reliable)
        quoted_matches = re.findall(r'"([^"]+)"', response)
        passwords.extend(quoted_matches)
        
        # Pattern 2: All caps words (3-15 characters)
        caps_matches = re.findall(r'\b[A-Z]{3,15}\b', response)
        passwords.extend(caps_matches)
        
        # Clean up and deduplicate
        result = []
        seen = set()
        
        for password in passwords:
            # Remove any non-alphanumeric characters
            clean_password = re.sub(r'[^a-zA-Z0-9]', '', password)
            
            if (clean_password and 
                len(clean_password) >= 3 and
                clean_password.lower() not in seen):
                seen.add(clean_password.lower())
                result.append(clean_password)
        
        return result[:3]
    
    def _wait_for_response_change(self, old_response: str, timeout: int = 20) -> str:
        """Wait for response to change - using the working logic from original."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                blockquote_p = self.driver.find_element(By.CSS_SELECTOR, "blockquote p")
                current_response = blockquote_p.text
                
                # Check if response has changed and is not empty
                if (current_response != old_response and 
                    current_response.strip() and 
                    current_response != "Hello traveler! Ask me anything..."):
                    return current_response
                    
            except Exception as e:
                logger.debug(f"Waiting for response: {e}")
            
            time.sleep(0.5)
        
        # Fallback: return whatever we have
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "blockquote p").text
        except:
            return ""
    
    def _update_level(self):
        """Extract current level from page using working logic."""
        try:
            # Wait a bit for any state updates
            time.sleep(1)
            
            # Look for level in h1 elements
            level_elements = self.driver.find_elements(By.XPATH, "//h1[contains(text(), 'Level')]")
            if level_elements:
                text = level_elements[0].text
                match = re.search(r'Level (\d+)', text)
                if match:
                    self.current_level = int(match.group(1))
                    return
            
            logger.warning("Could not detect current level, defaulting to 1")
            self.current_level = 1
            
        except Exception as e:
            logger.warning(f"Error detecting level: {e}")
            self.current_level = 1
    
    def _handle_popup(self):
        """Handle popups/modals by pressing Enter key - from working version."""
        try:            
            # Wait a moment for any popup to appear
            time.sleep(1)
            
            # Press Enter key to dismiss any modal/popup
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ENTER)
            
            # Wait for popup to close
            time.sleep(1)
            
            # Press Enter again if needed (sometimes takes two)
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ENTER)
            
            time.sleep(1)  # Wait for interface to be ready
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling level transition: {e}")
            return True  # Continue anyway
    
    def get_current_level(self) -> int:
        """Get current level number."""
        self._update_level()
        return self.current_level
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
    
    def __del__(self):
        self.close()