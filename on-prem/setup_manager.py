#!/usr/bin/env python3
"""
Setup State Manager for Cross-System Development
Tracks setup progress across Windows desktop and macOS laptop
"""

import json
import os
import sys
import platform
from datetime import datetime
from typing import Dict, List, Optional

class SetupStateManager:
    def __init__(self, state_file: str = "setup_state.json"):
        self.state_file = state_file
        self.current_system = self._detect_system()
        self.state = self._load_state()
    
    def _detect_system(self) -> str:
        """Detect current system type"""
        system = platform.system().lower()
        if system == "darwin":
            return "macos-laptop"
        elif system == "windows":
            return "windows-desktop"
        else:
            return f"{system}-unknown"
    
    def _load_state(self) -> Dict:
        """Load setup state from file"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        else:
            return self._create_default_state()
    
    def _create_default_state(self) -> Dict:
        """Create default state structure"""
        return {
            "setup_progress": {
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "current_system": self.current_system,
                "setup_phase": "initial",
                "completed_steps": [],
                "aws_resources": {
                    "opensearch_domain": None,
                    "s3_bucket": None,
                    "lambda_function": None,
                    "api_gateway": None,
                    "secrets_manager": None
                },
                "environment_variables": {},
                "next_steps": [
                    "Configure AWS CLI",
                    "Request Bedrock model access",
                    "Create OpenSearch domain"
                ],
                "notes": []
            },
            "systems": {
                "windows-desktop": {
                    "aws_cli_configured": False,
                    "python_version": None,
                    "git_configured": False,
                    "last_active": None
                },
                "macos-laptop": {
                    "aws_cli_configured": False,
                    "python_version": None,
                    "git_configured": False,
                    "last_active": None
                }
            }
        }
    
    def save_state(self):
        """Save current state to file"""
        self.state["setup_progress"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.state["setup_progress"]["current_system"] = self.current_system
        self.state["systems"][self.current_system]["last_active"] = datetime.utcnow().isoformat() + "Z"
        
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def mark_step_complete(self, step: str, details: Optional[str] = None):
        """Mark a setup step as complete"""
        if step not in self.state["setup_progress"]["completed_steps"]:
            self.state["setup_progress"]["completed_steps"].append(step)
        
        if details:
            self.add_note(f"Completed: {step} - {details}")
        
        self.save_state()
        print(f"✅ Marked complete: {step}")
    
    def add_aws_resource(self, resource_type: str, resource_id: str, details: Optional[str] = None):
        """Add AWS resource information"""
        self.state["setup_progress"]["aws_resources"][resource_type] = resource_id
        self.add_note(f"Created AWS resource: {resource_type} = {resource_id}")
        if details:
            self.add_note(f"  Details: {details}")
        self.save_state()
    
    def add_note(self, note: str):
        """Add a note to the setup progress"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        self.state["setup_progress"]["notes"].append({
            "timestamp": timestamp,
            "system": self.current_system,
            "note": note
        })
    
    def update_conversation_context(self, summary: str, focus: str = None, decisions: List[str] = None):
        """Update conversation context for Kiro handoffs"""
        if "conversation_context" not in self.state:
            return
        
        # Update session summary
        session = self.state["conversation_context"]["current_session"]
        session["last_summary"] = summary
        session["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        if focus:
            self.state["conversation_context"]["for_next_kiro_instance"]["current_focus"] = focus
        
        if decisions:
            session["key_decisions"].extend(decisions)
        
        # Add to recent work
        work_entry = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "system": self.current_system,
            "work_done": summary,
            "details": f"Session updated from {self.current_system}"
        }
        
        recent_work = self.state["project_context"]["recent_work"]
        recent_work.append(work_entry)
        
        # Keep only last 5 entries
        self.state["project_context"]["recent_work"] = recent_work[-5:]
        
        self.save_state()
    
    def set_environment_variable(self, key: str, value: str):
        """Store environment variable for cross-system use"""
        self.state["setup_progress"]["environment_variables"][key] = value
        self.save_state()
    
    def update_system_info(self, **kwargs):
        """Update current system information"""
        for key, value in kwargs.items():
            self.state["systems"][self.current_system][key] = value
        self.save_state()
    
    def get_status(self) -> str:
        """Get current setup status"""
        progress = self.state["setup_progress"]
        current_system = self.state["systems"][self.current_system]
        
        status = f"""
🔧 NEJM Research System Setup Status
=====================================

Current System: {self.current_system}
Setup Phase: {progress['setup_phase']}
Last Updated: {progress['last_updated']}

✅ Completed Steps ({len(progress['completed_steps'])}):
"""
        for step in progress["completed_steps"]:
            status += f"   • {step}\n"
        
        status += f"\n📋 Next Steps ({len(progress['next_steps'])}):\n"
        for i, step in enumerate(progress["next_steps"], 1):
            status += f"   {i}. {step}\n"
        
        status += f"\n☁️ AWS Resources:\n"
        for resource, value in progress["aws_resources"].items():
            icon = "✅" if value else "⏳"
            status += f"   {icon} {resource}: {value or 'Not created'}\n"
        
        status += f"\n💻 System Status:\n"
        for system, info in self.state["systems"].items():
            active = "🟢" if system == self.current_system else "⚪"
            status += f"   {active} {system}:\n"
            status += f"      AWS CLI: {'✅' if info['aws_cli_configured'] else '❌'}\n"
            status += f"      Python: {info['python_version'] or '❌'}\n"
            status += f"      Git: {'✅' if info['git_configured'] else '❌'}\n"
            status += f"      Last Active: {info['last_active'] or 'Never'}\n"
        
        if progress["notes"]:
            status += f"\n📝 Recent Notes:\n"
            for note in progress["notes"][-5:]:  # Show last 5 notes
                status += f"   • [{note['system']}] {note['note']}\n"
        
        # Add conversation context if available
        if "conversation_context" in self.state:
            ctx = self.state["conversation_context"]
            status += f"\n🤖 For New Kiro Instance:\n"
            status += f"   Project: {self.state.get('project_context', {}).get('name', 'NEJM Research System')}\n"
            status += f"   Current Focus: {ctx.get('for_next_kiro_instance', {}).get('current_focus', 'AWS deployment')}\n"
            status += f"   User: {ctx.get('user_profile', {}).get('name', 'jbsmith22')} ({ctx.get('user_profile', {}).get('workflow', 'cross-system development')})\n"
            status += f"   📖 See KIRO_CONTEXT.md for complete conversation context\n"
        
        return status
    
    def get_next_commands(self) -> List[str]:
        """Get the next commands to run based on current system and progress"""
        commands = []
        current_system = self.state["systems"][self.current_system]
        
        # Check what's needed on current system
        if not current_system["aws_cli_configured"]:
            if self.current_system == "macos-laptop":
                commands.extend([
                    "# Install AWS CLI on macOS:",
                    "brew install awscli",
                    "aws configure"
                ])
            else:  # Windows
                commands.extend([
                    "# Install AWS CLI on Windows:",
                    "# Download from: https://awscli.amazonaws.com/AWSCLIV2.msi",
                    "# Then run: aws configure"
                ])
        
        if not current_system["python_version"]:
            commands.append("python --version  # Check Python version")
        
        # Add AWS-specific next steps
        aws_resources = self.state["setup_progress"]["aws_resources"]
        if not aws_resources["opensearch_domain"]:
            commands.append("# Create OpenSearch domain (see README AWS setup)")
        
        return commands

def main():
    """Main CLI interface"""
    manager = SetupStateManager()
    
    if len(sys.argv) < 2:
        print(manager.get_status())
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print(manager.get_status())
    
    elif command == "next":
        commands = manager.get_next_commands()
        print("🚀 Next Commands to Run:")
        print("=" * 25)
        for cmd in commands:
            print(cmd)
    
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Usage: python setup_manager.py complete <step_name> [details]")
            return
        step = sys.argv[2]
        details = sys.argv[3] if len(sys.argv) > 3 else None
        manager.mark_step_complete(step, details)
    
    elif command == "aws-resource":
        if len(sys.argv) < 4:
            print("Usage: python setup_manager.py aws-resource <type> <id> [details]")
            return
        resource_type = sys.argv[2]
        resource_id = sys.argv[3]
        details = sys.argv[4] if len(sys.argv) > 4 else None
        manager.add_aws_resource(resource_type, resource_id, details)
    
    elif command == "note":
        if len(sys.argv) < 3:
            print("Usage: python setup_manager.py note <message>")
            return
        note = " ".join(sys.argv[2:])
        manager.add_note(note)
        manager.save_state()
        print(f"📝 Added note: {note}")
    
    elif command == "system-info":
        # Update system information
        import subprocess
        try:
            python_version = subprocess.check_output([sys.executable, "--version"], 
                                                   text=True).strip()
            manager.update_system_info(python_version=python_version)
            
            # Check if AWS CLI is available
            try:
                subprocess.check_output(["aws", "--version"], text=True)
                manager.update_system_info(aws_cli_configured=True)
            except:
                manager.update_system_info(aws_cli_configured=False)
            
            print("✅ Updated system information")
        except Exception as e:
            print(f"❌ Error updating system info: {e}")
    
    elif command == "context":
        # Display conversation context for Kiro handoffs
        if "conversation_context" in manager.state:
            ctx = manager.state["conversation_context"]
            proj = manager.state.get("project_context", {})
            
            print("🤖 Conversation Context for Kiro")
            print("=" * 35)
            print(f"Project: {proj.get('name', 'NEJM Research System')}")
            print(f"Description: {proj.get('description', 'AI-powered medical literature research')}")
            print(f"Current Goal: {proj.get('current_goal', 'AWS deployment setup')}")
            print()
            print(f"User: {ctx.get('user_profile', {}).get('name', 'jbsmith22')}")
            print(f"Systems: {', '.join(ctx.get('user_profile', {}).get('systems', ['Windows', 'macOS']))}")
            print(f"Workflow: {ctx.get('user_profile', {}).get('workflow', 'Cross-system development')}")
            print()
            print("Recent Work:")
            for work in proj.get('recent_work', [])[-3:]:
                print(f"  • [{work.get('system', 'unknown')}] {work.get('work_done', 'Work completed')}")
            print()
            print("Next Likely Requests:")
            for req in ctx.get('for_next_kiro_instance', {}).get('next_likely_requests', [])[:5]:
                print(f"  • {req}")
            print()
            print("📖 See KIRO_CONTEXT.md for complete details")
        else:
            print("❌ No conversation context available")
    
    elif command == "conversation":
        # Update conversation context
        if len(sys.argv) < 3:
            print("Usage: python setup_manager.py conversation <summary> [focus] [decision1,decision2,...]")
            print("Example: python setup_manager.py conversation 'Deployed Lambda function successfully' 'API Gateway setup' 'Use Claude 3 Sonnet,Increase Lambda memory to 1024MB'")
            return
        
        summary = sys.argv[2]
        focus = sys.argv[3] if len(sys.argv) > 3 else None
        decisions = sys.argv[4].split(',') if len(sys.argv) > 4 else None
        
        manager.update_conversation_context(summary, focus, decisions)
        print(f"✅ Updated conversation context: {summary}")
        if focus:
            print(f"   New focus: {focus}")
        if decisions:
            print(f"   Decisions: {', '.join(decisions)}")
    
    else:
        print(f"""
Usage: python setup_manager.py <command>

Commands:
  status              Show current setup status
  next               Show next commands to run
  complete <step>    Mark a step as complete
  aws-resource <type> <id>  Record AWS resource creation
  note <message>     Add a note
  system-info        Update current system information
  context            Show conversation context for Kiro handoffs
  conversation <summary> [focus] [decisions]  Update conversation context

Examples:
  python setup_manager.py status
  python setup_manager.py context
  python setup_manager.py complete "AWS CLI configured"
  python setup_manager.py aws-resource opensearch_domain "search-nejm-research-abc123"
  python setup_manager.py note "Started OpenSearch domain creation"
  python setup_manager.py conversation "Deployed Lambda successfully" "API Gateway setup"
""")

if __name__ == "__main__":
    main()