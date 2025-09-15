import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import logging
from agent.core.learning_agent import LearningAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_multi_level():
    print("=== Testing Multi-Level Learning Agent ===")
    
    agent = LearningAgent(headless=True)
    
    try:
        # Play up to level 4 to see how difficulty scales
        results = agent.play_game(start_level=1, max_levels=4)
        
        # Print detailed summary
        agent.print_summary()
        
        print("\n=== LEARNING ANALYSIS ===")
        print(f"Total levels completed: {results['levels_completed']}")
        
        # Show what strategies worked at each level
        for level, details in results['level_details'].items():
            print(f"\nLevel {level}:")
            for i, attempt in enumerate(details['attempts']):
                status = "SUCCESS" if attempt['success'] else "FAILED"
                print(f"  Attempt {i+1}: {attempt['strategy']} - {status}")
                print(f"    Prompt: '{attempt['prompt'][:60]}...'")
                if attempt['success']:
                    print(f"    Password: {attempt.get('password', 'N/A')}")
        
        # Check if memory was saved
        if agent.memory.memory_file.exists():
            print(f"\nLearning data saved to: {agent.memory.memory_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_level()
