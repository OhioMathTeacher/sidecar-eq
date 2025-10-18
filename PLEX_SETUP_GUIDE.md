# Plex Server Setup Guide for Sidecar EQ

## Overview

Sidecar EQ now supports connecting to Plex Media Servers! You can browse your Plex music libraries and add tracks directly to your playback queue.

## How to Register Your Plex Server

### Step 1: Open Plex Account Manager

1. Launch Sidecar EQ
2. Go to **Settings → Manage Plex Servers…**
3. The Plex Account Manager dialog will open

### Step 2: Sign In with Your Plex Account

1. Enter your **Plex username** (or email)
2. Enter your **Plex password**
3. Click **"Sign In & Discover Servers"**

**What happens next:**
- Sidecar EQ will sign in to your Plex account
- It will automatically discover all Plex Media Servers you have access to
- Each server will be registered and added to the list
- Your authentication token is stored locally and securely

### Step 3: Access Your Plex Servers

Once registered, your Plex servers will appear in the **source dropdown** at the top of the window:

```
🎵 Plex: Downstairs
🎵 Plex: Office Server
...
```

### Step 4: Browse and Add Music

1. Select a Plex server from the source dropdown
2. If you have multiple accounts registered for that server, you'll be asked to choose one
3. The Plex browser will open, showing your music libraries
4. Browse and select tracks to add to your queue
5. Click "Add to Queue" to start playing!

## Multiple Accounts

If you have multiple Plex accounts (e.g., guest and admin), you can register both:

1. Sign in with the first account → servers are discovered and registered
2. Sign in with the second account → additional access is registered
3. When you select a server, you'll be prompted to choose which account to use

## Managing Registered Servers

### View Registered Servers
All your registered servers appear in the Plex Account Manager list with format:
```
🎵 [Server Name] ([Username])
```

### Remove a Server
1. Select the server in the list
2. Click **"Remove Selected"**
3. Confirm the removal

The server will no longer appear in your source dropdown.

## Security & Privacy

- Your Plex credentials (username/password) are **never stored**
- Only the authentication **token** is stored locally
- Tokens are stored in your local Sidecar EQ database
- Tokens are never transmitted to anyone except Plex servers
- You can remove servers at any time to revoke access

## Troubleshooting

### "No Servers Found"
- Make sure you have access to at least one Plex Media Server
- Check that the server is running and accessible on your network
- Try signing in to Plex.tv in a browser to verify your account

### "Sign In Failed"
- Double-check your username and password
- Make sure you're using your Plex account credentials (not server credentials)
- If using email, try using your Plex username instead

### Server Not Appearing in Dropdown
- Make sure you've registered it in Settings → Manage Plex Servers
- Try closing and reopening the music source dropdown
- Restart Sidecar EQ if needed

### "No Accounts Found" When Selecting Server
- You need to register at least one account with access to that server
- Go to Settings → Manage Plex Servers and sign in

## Technical Details

### How It Works
1. You sign in with your Plex account credentials
2. Plex returns an authentication token
3. Sidecar EQ uses the token to discover available servers
4. Server information (name, address, token) is stored locally
5. When you select a server, the token is used to authenticate

### What's Stored
For each registered server/account combination:
- Server name (e.g., "Downstairs")
- Server address (e.g., "192.168.68.57:32400")
- Plex username
- Authentication token

### Data Location
All Plex account data is stored in the Sidecar EQ local database using the `store` module. It's saved in your user data directory alongside other app settings.

## Example Workflow

1. **First Time Setup:**
   - Settings → Manage Plex Servers
   - Sign in as "MusicMan" (guest account)
   - "Downstairs" server is discovered and registered
   - Sign in as "Billy_Nimbus" (admin account)
   - "Downstairs" server is registered again with admin access

2. **Daily Use:**
   - Open source dropdown at top
   - Click "🎵 Plex: Downstairs"
   - Choose "MusicMan" or "Billy_Nimbus"
   - Browse music library
   - Add tracks to queue
   - Enjoy!

## Benefits Over .env File Approach

The old method required manually editing a `.env` file with tokens. The new approach:

✅ **User-friendly** - Sign in with username/password  
✅ **Automatic discovery** - Finds all your servers  
✅ **Multi-account support** - Register multiple users per server  
✅ **GUI management** - Add/remove servers through the app  
✅ **No technical knowledge required** - No file editing needed  

## Need Help?

If you encounter issues not covered in this guide, please check:
- Your Plex server is online and accessible
- Your Plex account has the necessary permissions
- Your network allows connections to the Plex server

Happy listening! 🎵
