import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

try:
    print("Verifying ContextPilot Architecture...")
    
    print("1. Importing context_pilot_agent (Main)...")
    from context_pilot.context_pilot_app.agent import context_pilot_agent
    print(f"   [OK] Name: {context_pilot_agent.name}")
    print(f"   Tools: {[getattr(t, 'name', str(t)) for t in context_pilot_agent.tools]}")
    
    print("\n2. Importing repo_explorer_agent (Explorer)...")
    from context_pilot.context_pilot_app.repo_explorer_agent.agent import repo_explorer_agent
    print(f"   [OK] Name: {repo_explorer_agent.name}")
    
    print("\n3. Importing exp_recored_agent (Recorder)...")
    from context_pilot.context_pilot_app.exp_recored_agent.agent import exp_recored_agent
    print(f"   [OK] Name: {exp_recored_agent.name}")
    
    print("\nVerification Passed: All agents loaded successfully.")
    
except Exception as e:
    print(f"\nVerification Failed: {e}")
    import traceback
    traceback.print_exc()
