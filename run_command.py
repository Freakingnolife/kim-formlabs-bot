#!/usr/bin/env python3
"""
Quick command runner for OpenClaw integration
Usage: python run_command.py <command> [user_id]
"""

import sys
sys.path.insert(0, 'src')

from bot_commands import handle_command

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_command.py <command> [user_id]")
        print("Example: python run_command.py /printers 6217674573")
        sys.exit(1)
    
    command = sys.argv[1]
    user_id = int(sys.argv[2]) if len(sys.argv) > 2 else 6217674573
    
    result = handle_command(command, user_id)
    print(result)
