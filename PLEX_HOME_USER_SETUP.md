# Plex Home User Setup Guide

## Overview

SidecarEQ now supports Plex Media Server integration using **Home Users** (managed accounts), providing a simple, privacy-friendly setup that doesn't require Plex account credentials or hardcoded configuration.

## Key Features

✅ **Auto-Discovery**: Automatically finds Plex servers on your local network  
✅ **No Account Login**: Direct server connection without Plex.tv authentication  
✅ **Home User Support**: Works with managed Plex users (guest or PIN-protected)  
✅ **Privacy First**: All settings stored locally, never in code  
✅ **Portable**: Anyone can download and configure for their own server  

## How It Works

### 1. Server Discovery

**Option A: Auto-Discovery (Recommended)**
1. Open Settings → Manage Plex Servers
2. Click "Scan Network"
3. Select your server from the discovered list
4. Configure Home Users (see step 2)

**Option B: Manual Entry**
1. Open Settings → Manage Plex Servers
2. Enter server IP address (e.g., `192.168.68.57`)
3. Default port is `32400`
4. Click "Connect to Server"

### 2. Configure Home Users

After connecting to a server, you'll configure which **Home Users** to enable:

**For Each User:**
- Check the "Enable" box
- Enter the username (e.g., `MusicMan`, `Billy_Nimbus`)
- **Optional**: Enter 4-digit PIN if the user has one

**Example Configuration:**

| Enabled | Username      | PIN    | Notes                    |
|---------|---------------|--------|--------------------------|
| ✅       | MusicMan      |        | Guest user, no PIN       |
| ✅       | Billy_Nimbus  | 1234   | Admin user with PIN      |

### 3. Accessing Your Music

Once configured, Plex servers appear in the **Source dropdown** alongside local folders:

```
🏠 Home Folder
🎵 Music Folder  
📁 Choose Folder...
─────────────────
🎬 Downstairs        ← Your Plex server
```

When you select a Plex server:
1. Choose which Home User to connect as
2. Enter PIN if required (only asked once, stored securely)
3. Browse and select music from that user's libraries

## Technical Details

### Storage Format

All configuration is stored in `~/.sidecar-eq/config.json` (never in code):

```json
{
  "plex_servers": [
    {
      "name": "Downstairs",
      "host": "192.168.68.57",
      "port": "32400",
      "users": [
        {
          "username": "MusicMan",
          "pin": "",
          "enabled": true
        },
        {
          "username": "Billy_Nimbus",
          "pin": "1234",
          "enabled": true
        }
      ]
    }
  ]
}
```

### Connection Method

- Uses `PlexServer` direct connection: `http://[IP]:32400`
- No `MyPlexAccount` authentication required
- Supports guest access (no credentials needed)
- PIN validation happens client-side for simplicity

### Network Discovery

Uses Plex GDM (Good Day Mate) protocol to find servers:
- Broadcasts UDP multicast on port 32414
- Plex servers respond with their connection info
- Works on local network without internet access

## Privacy & Portability

### What's in the Code (Public)
- Generic Plex discovery protocol
- UI for configuring servers/users
- Storage logic (but not your data)
- ✅ Safe to commit to GitHub

### What's in Local Config (Private)
- Your server IP address
- Your Home User names
- User PINs (if any)
- ❌ Never committed (in `.gitignore`)

### For Other Users
When someone else downloads your code:
1. They run the app
2. It discovers **their** Plex server
3. They configure **their** users
4. Everything stays on their machine
5. Your configuration never appears

## Comparison to Old Approach

| Feature | Old (MyPlexAccount) | New (Home Users) |
|---------|---------------------|------------------|
| Login Required | ✅ Username/Password | ❌ No login for guests |
| Guest Access | ❌ No | ✅ Yes (MusicMan) |
| PIN Support | ❌ No | ✅ Yes (4-digit) |
| Server Discovery | Manual | ✅ Auto-discover |
| Privacy | Credentials in config | ✅ No credentials needed |
| Portability | ❌ Account-specific | ✅ Works for anyone |

## Troubleshooting

### "No Servers Found" on Auto-Discovery
- Ensure Plex Media Server is running
- Check that server and computer are on same network
- Firewall may block GDM broadcasts (port 32414)
- **Workaround**: Use manual IP entry

### "Connection Failed" on Manual Entry
- Verify IP address is correct
- Check port (default: 32400)
- Ensure Plex server is running
- Try accessing `http://[IP]:32400/web` in browser

### "No Users Configured"
- You must enable at least one user with a username
- Leave PIN blank for guest users
- Enter 4-digit PIN for protected users

### "Incorrect PIN"
- Double-check PIN in Plex settings
- PIN is case-sensitive (numeric only)
- Re-save user configuration if needed

## Future Enhancements

- [ ] Auto-detect Home Users from server (requires token)
- [ ] Encrypt PINs in local storage
- [ ] Support Plex offline sync
- [ ] Remember last-used user per server
- [ ] Support multiple servers simultaneously

## Example Use Cases

### Personal Music Server
- **User**: Just you
- **Setup**: Enable one Home User (yourself)
- **PIN**: Optional for privacy

### Family Server
- **Users**: Multiple family members
- **Setup**: Enable users for each person
- **PINs**: Admin users have PINs, kids don't

### Public/Guest Server
- **User**: MusicMan (no PIN)
- **Setup**: Everyone uses same guest account
- **Access**: No authentication needed

## Related Documentation

- [Plex Home Users Official Guide](https://support.plex.tv/articles/203815766-what-is-plex-home/)
- [Plex API Documentation](https://python-plexapi.readthedocs.io/)
- [SidecarEQ Setup Guide](README.md)

---

**Last Updated**: October 18, 2025  
**Version**: SidecarEQ 1.1.0+plex
