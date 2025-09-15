import logging
from agent.hackmerlin_agent import HackMerlinAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_clean_agent():
    print("=== Testing Clean HackMerlin Agent ===")
    
    # Test with LLM extraction
    agent = HackMerlinAgent(headless=True, use_llm_extraction=True)
    
    try:
        results = agent.play_game(max_levels=6)
        agent.print_summary()
        
        print(f"\nResults: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_clean_agent()