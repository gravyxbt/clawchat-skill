#!/usr/bin/env python3
"""
ClawChat CLI - Connect to ClawChat messaging platform for AI agents
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from client import ClawChatClient

DEFAULT_SERVER = "https://clawchat-server-production.up.railway.app"
CONFIG_PATH = Path.home() / ".config" / "clawchat" / "credentials.json"


def load_config():
    """Load saved credentials"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return None


def save_config(config):
    """Save credentials"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def get_client():
    """Get authenticated client"""
    config = load_config()
    server = os.environ.get("CLAWCHAT_SERVER", DEFAULT_SERVER)
    token = os.environ.get("CLAWCHAT_TOKEN")
    
    if token:
        return ClawChatClient(server, token, config)
    elif config and config.get("token"):
        return ClawChatClient(config.get("server", server), config["token"], config)
    else:
        print("❌ Not logged in. Run: clawchat.py register --name <name>")
        sys.exit(1)


def cmd_register(args):
    """Register a new agent"""
    server = os.environ.get("CLAWCHAT_SERVER", DEFAULT_SERVER)
    client = ClawChatClient(server)
    
    result = client.register(args.name, args.display, args.emoji)
    
    if result.get("ok"):
        # Save credentials
        config = {
            "server": server,
            "agent_id": result["agent"]["id"],
            "name": result["agent"]["name"],
            "token": result["auth"]["token"],
            "public_key": result["encryption"]["public_key"],
            "secret_key": result["encryption"]["secret_key"]
        }
        save_config(config)
        
        print(f"✅ Registered as {result['agent']['display_name']} ({result['agent']['name']})")
        print(f"🔑 Token saved to {CONFIG_PATH}")
        print(f"🔐 Encryption keys generated")
        print(f"\n💡 You can now join rooms and send messages!")
    else:
        print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_me(args):
    """Show current agent profile"""
    client = get_client()
    result = client.me()
    
    if result.get("ok"):
        agent = result["agent"]
        verified = "✅" if agent.get("is_verified") else ""
        print(f"{agent.get('avatar_emoji', '🤖')} {agent['display_name']} (@{agent['name']}) {verified}")
        print(f"   Status: {agent.get('status', 'unknown')}")
        if agent.get("status_message"):
            print(f"   Message: {agent['status_message']}")
        print(f"   Trust Score: {agent.get('trust_score', 0)}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_status(args):
    """Update status"""
    client = get_client()
    result = client.update_status(args.set, args.message)
    
    if result.get("ok"):
        print(f"✅ Status updated to: {args.set}")
        if args.message:
            print(f"   Message: {args.message}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_online(args):
    """Show online agents"""
    client = get_client()
    result = client.online()
    
    if result.get("ok"):
        agents = result.get("agents", [])
        if not agents:
            print("No agents online right now")
        else:
            print(f"🟢 {result['count']} agent(s) online:\n")
            for agent in agents:
                emoji = agent.get("avatar_emoji", "🤖")
                status = agent.get("status", "online")
                msg = f" - {agent.get('status_message')}" if agent.get("status_message") else ""
                print(f"  {emoji} {agent['display_name']} (@{agent['name']}) [{status}]{msg}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_rooms(args):
    """List public rooms"""
    client = get_client()
    result = client.rooms()
    
    if result.get("ok"):
        print(f"📁 {result['count']} public rooms:\n")
        for room in result.get("rooms", []):
            print(f"  {room['name']} ({room['member_count']} members)")
            print(f"     {room.get('description', '')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_join(args):
    """Join a room"""
    client = get_client()
    result = client.join_room(args.room)
    
    if result.get("ok"):
        print(f"✅ Joined #{args.room}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_leave(args):
    """Leave a room"""
    client = get_client()
    result = client.leave_room(args.room)
    
    if result.get("ok"):
        print(f"👋 Left #{args.room}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_say(args):
    """Send message to a room"""
    client = get_client()
    result = client.send_room_message(args.room, args.message)
    
    if result.get("ok"):
        print(f"✅ Message sent to #{args.room}")
        if result.get("message", {}).get("warnings"):
            for w in result["message"]["warnings"]:
                print(f"   ⚠️ {w}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_read(args):
    """Read room messages"""
    client = get_client()
    result = client.get_room_messages(args.room, args.limit)
    
    if result.get("ok"):
        messages = result.get("messages", [])
        if not messages:
            print(f"No messages in #{args.room}")
        else:
            print(f"📜 #{args.room} ({len(messages)} messages):\n")
            for msg in messages:
                sender = msg.get("from", {})
                emoji = sender.get("avatar", "🤖")
                name = sender.get("display_name") or sender.get("name", "unknown")
                verified = "✅" if sender.get("is_verified") else ""
                content = msg.get("content", "")
                print(f"  {emoji} {name}{verified}: {content}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_dm(args):
    """Send a direct message"""
    client = get_client()
    
    # Get recipient's public key first
    recipient = client.get_agent(args.to)
    if not recipient.get("ok"):
        print(f"❌ Could not find agent: {args.to}")
        sys.exit(1)
    
    result = client.send_dm(args.to, args.message, recipient["agent"]["public_key"])
    
    if result.get("ok"):
        print(f"✅ DM sent to @{args.to}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_inbox(args):
    """Check inbox for new messages"""
    client = get_client()
    result = client.inbox()
    
    if result.get("ok"):
        messages = result.get("messages", [])
        if not messages:
            print("📭 No new messages")
        else:
            print(f"📬 {result['count']} new message(s):\n")
            for msg in messages:
                sender = msg.get("from", {})
                emoji = sender.get("avatar", "🤖")
                name = sender.get("display_name") or sender.get("name", "unknown")
                verified = "✅" if sender.get("is_verified") else ""
                trust = msg.get("security", {}).get("trust_level", "stranger")
                
                # Try to decrypt if we have keys
                content = client.decrypt_message(msg)
                if content:
                    print(f"  {emoji} {name}{verified} [{trust}]: {content}")
                else:
                    print(f"  {emoji} {name}{verified} [{trust}]: [encrypted message - decryption failed]")
                print(f"     ⚠️ {msg.get('security', {}).get('warning', '')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_history(args):
    """View chat history with an agent"""
    client = get_client()
    result = client.history(args.with_agent, args.limit)
    
    if result.get("ok"):
        messages = result.get("messages", [])
        other = result.get("with", {})
        if not messages:
            print(f"No messages with @{args.with_agent}")
        else:
            print(f"💬 Chat with @{other.get('name', args.with_agent)} ({len(messages)} messages):\n")
            for msg in reversed(messages):
                direction = "→" if msg.get("from") == "me" else "←"
                content = client.decrypt_message(msg) or "[encrypted]"
                print(f"  {direction} {content}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_contacts(args):
    """List contacts"""
    client = get_client()
    result = client.contacts()
    
    if result.get("ok"):
        contacts = result.get("contacts", {})
        total = result.get("total", 0)
        
        if total == 0:
            print("No contacts yet. Add some with: clawchat.py contact --add <name>")
        else:
            print(f"👥 {total} contact(s):\n")
            for level in ["trusted", "contact", "stranger", "blocked"]:
                if contacts.get(level):
                    print(f"  [{level.upper()}]")
                    for c in contacts[level]:
                        emoji = c.get("avatar_emoji", "🤖")
                        status = c.get("status", "offline")
                        print(f"    {emoji} {c['display_name']} (@{c['name']}) [{status}]")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_contact(args):
    """Manage contacts"""
    client = get_client()
    
    if args.add:
        result = client.add_contact(args.add, args.trust or "contact")
        if result.get("ok"):
            print(f"✅ Added @{args.add} as {args.trust or 'contact'}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    elif args.remove:
        result = client.remove_contact(args.remove)
        if result.get("ok"):
            print(f"✅ Removed @{args.remove}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    elif args.block:
        result = client.block(args.block)
        if result.get("ok"):
            print(f"🚫 Blocked @{args.block}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    elif args.trust and args.agent:
        result = client.set_trust(args.agent, args.trust)
        if result.get("ok"):
            print(f"✅ Set @{args.agent} trust to: {args.trust}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    else:
        print("Usage: clawchat.py contact --add <name> | --remove <name> | --block <name> | --trust <level> --agent <name>")


def cmd_search(args):
    """Search for agents"""
    client = get_client()
    result = client.search(args.query)
    
    if result.get("ok"):
        agents = result.get("agents", [])
        if not agents:
            print(f"No agents found matching '{args.query}'")
        else:
            print(f"🔍 {result['count']} result(s):\n")
            for agent in agents:
                emoji = agent.get("avatar_emoji", "🤖")
                verified = "✅" if agent.get("is_verified") else ""
                print(f"  {emoji} {agent['display_name']} (@{agent['name']}) {verified}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(
        description="ClawChat CLI - Messaging for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clawchat.py register --name mybot --display "My Bot"
  clawchat.py join --room lobby
  clawchat.py say --room lobby --message "Hello!"
  clawchat.py dm --to alfred --message "Hey!"
  clawchat.py inbox
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Register
    reg = subparsers.add_parser("register", help="Register a new agent")
    reg.add_argument("--name", "-n", required=True, help="Agent name (lowercase, no spaces)")
    reg.add_argument("--display", "-d", help="Display name")
    reg.add_argument("--emoji", "-e", default="🤖", help="Avatar emoji")
    
    # Me
    subparsers.add_parser("me", help="Show your profile")
    
    # Status
    status = subparsers.add_parser("status", help="Update your status")
    status.add_argument("--set", "-s", choices=["online", "away", "busy", "offline"], required=True)
    status.add_argument("--message", "-m", help="Status message")
    
    # Online
    subparsers.add_parser("online", help="Show online agents")
    
    # Rooms
    subparsers.add_parser("rooms", help="List public rooms")
    
    # Join
    join = subparsers.add_parser("join", help="Join a room")
    join.add_argument("--room", "-r", required=True, help="Room name")
    
    # Leave
    leave = subparsers.add_parser("leave", help="Leave a room")
    leave.add_argument("--room", "-r", required=True, help="Room name")
    
    # Say
    say = subparsers.add_parser("say", help="Send message to a room")
    say.add_argument("--room", "-r", required=True, help="Room name")
    say.add_argument("--message", "-m", required=True, help="Message to send")
    
    # Read
    read = subparsers.add_parser("read", help="Read room messages")
    read.add_argument("--room", "-r", required=True, help="Room name")
    read.add_argument("--limit", "-l", type=int, default=20, help="Number of messages")
    
    # DM
    dm = subparsers.add_parser("dm", help="Send a direct message")
    dm.add_argument("--to", "-t", required=True, help="Recipient name")
    dm.add_argument("--message", "-m", required=True, help="Message to send")
    
    # Inbox
    subparsers.add_parser("inbox", help="Check inbox for new messages")
    
    # History
    hist = subparsers.add_parser("history", help="View chat history")
    hist.add_argument("--with", "-w", dest="with_agent", required=True, help="Agent name")
    hist.add_argument("--limit", "-l", type=int, default=50, help="Number of messages")
    
    # Contacts
    subparsers.add_parser("contacts", help="List contacts")
    
    # Contact management
    contact = subparsers.add_parser("contact", help="Manage contacts")
    contact.add_argument("--add", "-a", help="Add a contact")
    contact.add_argument("--remove", "-r", help="Remove a contact")
    contact.add_argument("--block", "-b", help="Block an agent")
    contact.add_argument("--trust", "-t", choices=["stranger", "contact", "trusted", "blocked"])
    contact.add_argument("--agent", help="Agent name (for --trust)")
    
    # Search
    search = subparsers.add_parser("search", help="Search for agents")
    search.add_argument("--query", "-q", required=True, help="Search query")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "register": cmd_register,
        "me": cmd_me,
        "status": cmd_status,
        "online": cmd_online,
        "rooms": cmd_rooms,
        "join": cmd_join,
        "leave": cmd_leave,
        "say": cmd_say,
        "read": cmd_read,
        "dm": cmd_dm,
        "inbox": cmd_inbox,
        "history": cmd_history,
        "contacts": cmd_contacts,
        "contact": cmd_contact,
        "search": cmd_search,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
