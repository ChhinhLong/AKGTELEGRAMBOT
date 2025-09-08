# YouTube Cookies Configuration

This folder is used to store YouTube cookies for bypassing certain restrictions and improving download success rates.

## How to Get YouTube Cookies

### Method 1: Browser Extension
1. Install a cookie export extension (like "Get cookies.txt LOCALLY")
2. Go to youtube.com and make sure you're logged in
3. Use the extension to export cookies as `cookies.txt`
4. Upload the file to this folder

### Method 2: Manual Export
1. Go to youtube.com in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage tab
4. Find Cookies → https://youtube.com
5. Export cookies in Netscape format

### Method 3: Admin Command
Use the `/addcookies` admin command in your bot to upload cookies file directly.

## File Format
The cookies.txt file should be in Netscape format:
```
# Netscape HTTP Cookie File
.youtube.com    TRUE    /    FALSE    1234567890    cookie_name    cookie_value
```

## When to Use Cookies
- If you encounter "Sign in to confirm you're not a bot" errors
- When downloading age-restricted content
- For improved download reliability
- When facing IP-based rate limiting

## Security Note
- Keep your cookies.txt file private
- Don't share it with others
- Regenerate cookies periodically for security