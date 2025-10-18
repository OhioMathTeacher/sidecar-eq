#!/usr/bin/env python3
"""Get a fresh Plex token interactively.

This script will:
1. Ask for your Plex username/email and password
2. Authenticate with Plex
3. Display your token
4. Optionally update your .env file

Usage:
    python get_plex_token.py
"""

import sys
from pathlib import Path

try:
    from plexapi.myplex import MyPlexAccount
except ImportError:
    print("❌ plexapi not installed!")
    print("Install with: pip install plexapi")
    sys.exit(1)

import getpass


def get_token_interactive():
    """Get Plex token by logging in."""
    print("=" * 60)
    print("Plex Token Generator")
    print("=" * 60)
    print("\nThis will log into your Plex account and get a fresh token.")
    print("Your credentials are NOT stored - only the token.\n")
    
    # Get credentials
    username = input("Plex username or email: ").strip()
    password = getpass.getpass("Plex password: ")
    
    if not username or not password:
        print("❌ Username and password required!")
        return None
    
    try:
        print("\n🔐 Authenticating with Plex...")
        account = MyPlexAccount(username, password)
        
        print(f"✅ Logged in as: {account.username}")
        print(f"   Email: {account.email}")
        
        token = account.authenticationToken
        print(f"\n🎫 Your Plex Token:")
        print(f"   {token}")
        
        return token
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None


def list_servers(token):
    """List available Plex servers."""
    try:
        from plexapi.myplex import MyPlexAccount
        account = MyPlexAccount(token=token)
        
        print("\n" + "=" * 60)
        print("Your Plex Servers:")
        print("=" * 60)
        
        resources = account.resources()
        servers = [r for r in resources if r.provides == 'server']
        
        if not servers:
            print("❌ No servers found")
            return None
        
        for i, server in enumerate(servers, 1):
            print(f"\n{i}. {server.name}")
            print(f"   Owned by: {server.owned}")
            
            # Try to get connections
            connections = server.connections
            if connections:
                print(f"   Connections:")
                for conn in connections:
                    local = "🏠 Local" if conn.local else "🌐 Remote"
                    print(f"      {local}: {conn.uri}")
        
        return servers[0] if servers else None
        
    except Exception as e:
        print(f"❌ Failed to list servers: {e}")
        return None


def update_env_file(token, server_url=None):
    """Update .env file with new token."""
    env_path = Path(".env")
    
    print("\n" + "=" * 60)
    print("Update .env File")
    print("=" * 60)
    
    response = input("\nUpdate .env file with this token? (y/n): ").lower().strip()
    
    if response != 'y':
        print("⏭️  Skipping .env update")
        return
    
    try:
        # Read existing .env
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        
        # Update or add PLEX_TOKEN
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('PLEX_TOKEN='):
                lines[i] = f'PLEX_TOKEN={token}'
                updated = True
                print(f"✅ Updated PLEX_TOKEN")
            elif server_url and line.startswith('PLEX_BASEURL='):
                lines[i] = f'PLEX_BASEURL={server_url}'
                print(f"✅ Updated PLEX_BASEURL")
        
        if not updated:
            lines.append(f'PLEX_TOKEN={token}')
            print(f"✅ Added PLEX_TOKEN")
        
        if server_url and not any(l.startswith('PLEX_BASEURL=') for l in lines):
            lines.append(f'PLEX_BASEURL={server_url}')
            print(f"✅ Added PLEX_BASEURL")
        
        # Write back
        env_path.write_text('\n'.join(lines) + '\n')
        print(f"\n✅ .env file updated!")
        
    except Exception as e:
        print(f"❌ Failed to update .env: {e}")


def main():
    """Main entry point."""
    print("\n🎵 SidecarEQ - Plex Token Generator\n")
    
    # Get token
    token = get_token_interactive()
    if not token:
        return 1
    
    # List servers
    server = list_servers(token)
    
    # Get server URL
    server_url = None
    if server and server.connections:
        # Prefer local connection
        local_conns = [c for c in server.connections if c.local]
        if local_conns:
            server_url = local_conns[0].uri
        else:
            server_url = server.connections[0].uri
        
        print(f"\n📍 Recommended server URL: {server_url}")
    
    # Update .env
    update_env_file(token, server_url)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL DONE!")
    print("=" * 60)
    print(f"\nYour token: {token}")
    if server_url:
        print(f"Server URL: {server_url}")
    
    print("\n💡 You can now run: python test_plex_playback.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
