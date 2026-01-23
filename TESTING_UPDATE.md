# Testing the Self-Update Feature

## Quick Test Steps

### 1. Start the App

```bash
# Start the app in development mode
./scripts/dev.sh

# Or directly:
python3 app.py start -f
```

The app will start on `http://localhost:5050` (or your configured port).

### 2. Test the Update Check API

Open a new terminal and test the API endpoint:

```bash
# Check for updates (will use cache if available)
curl http://localhost:5050/api/update/check

# Force a fresh check (bypasses cache)
curl http://localhost:5050/api/update/check?force=true
```

**Expected Response:**
- If running as Python script: `{"error": "Updates only available for binary installations", ...}`
- If running as binary: Returns update info or `{"available": false, ...}` if already latest

### 3. Test the CLI Command

```bash
# Check for updates only
python3 app.py update --check-only

# Check and prompt for installation
python3 app.py update
```

**Expected Behavior:**
- Shows current version (1.0.7)
- Shows latest version from GitHub
- If update available, prompts for installation
- If running as script, shows message that updates are only for binaries

### 4. Test the UI Components

1. **Open the dashboard**: `http://localhost:5050`

2. **Check browser console** (F12):
   - Look for update check messages after 1 hour (or manually trigger)
   - Check for any JavaScript errors

3. **Manually trigger update check** (in browser console):
   ```javascript
   checkForUpdates(true);
   ```

4. **Test update notification banner**:
   - If an update is available, a blue banner should appear at the top
   - Test buttons: "Update Now", "Later", "×"

5. **Test update dialog**:
   - Click "Update Now" on the banner
   - Dialog should show version comparison and changelog
   - Test "Cancel" and "Install Update" buttons

### 5. Test Version Comparison Logic

You can test the version comparison function directly in Python:

```python
python3 -c "
import sys
sys.path.insert(0, '.')
from app import compare_versions

# Test cases
print('1.0.7 vs 1.0.8:', compare_versions('1.0.7', '1.0.8'))  # Should return -1
print('1.0.8 vs 1.0.7:', compare_versions('1.0.8', '1.0.7'))  # Should return 1
print('1.0.7 vs 1.0.7:', compare_versions('1.0.7', '1.0.7'))  # Should return 0
print('1.0.7 vs 1.1.0:', compare_versions('1.0.7', '1.1.0'))  # Should return -1
print('2.0.0 vs 1.9.9:', compare_versions('2.0.0', '1.9.9'))  # Should return 1
"
```

### 6. Test Update Installation (Binary Only)

**Note:** This only works when running as a compiled binary, not as a Python script.

To test the full installation flow:

1. **Build a binary first**:
   ```bash
   ./scripts/build.sh
   ```

2. **Run the binary**:
   ```bash
   ./dist/gradik start -f
   ```

3. **Test update check**:
   ```bash
   ./dist/gradik update --check-only
   ```

4. **Test update installation** (if a newer version exists on GitHub):
   ```bash
   ./dist/gradik update
   ```

### 7. Test Update Check Caching

The update check is cached for 1 hour. To test:

1. **First check** (hits GitHub API):
   ```bash
   curl http://localhost:5050/api/update/check
   ```

2. **Second check immediately** (uses cache):
   ```bash
   curl http://localhost:5050/api/update/check
   ```
   Should be faster and return cached result.

3. **Force fresh check** (bypasses cache):
   ```bash
   curl http://localhost:5050/api/update/check?force=true
   ```

### 8. Test Error Handling

Test various error scenarios:

1. **Network error** (disconnect internet):
   ```bash
   curl http://localhost:5050/api/update/check
   ```
   Should return error message gracefully.

2. **Invalid response** (mock GitHub API failure):
   - The code should handle JSON decode errors gracefully

3. **Permission error** (for installation):
   - If binary is in `/usr/local/bin` without write permissions, should show helpful error

### 9. Manual UI Testing Checklist

- [ ] Update banner appears when update is available
- [ ] Banner shows correct current and latest versions
- [ ] "Update Now" button opens dialog
- [ ] "Later" button dismisses banner
- [ ] "×" button permanently dismisses banner (for 24h)
- [ ] Update dialog shows version comparison
- [ ] Update dialog shows changelog
- [ ] Progress bar appears during installation
- [ ] Cancel button works during installation
- [ ] Success message appears after installation
- [ ] Page reloads after successful installation

### 10. Test Automatic Background Checks

The app automatically checks for updates:
- **First check**: After 1 hour of running
- **Subsequent checks**: Every 6 hours

To test this immediately, you can modify the delay in the JavaScript (temporarily):

In `app.py`, find:
```javascript
setTimeout(() => {
    checkForUpdates();
    // ...
}, 60 * 60 * 1000); // 1 hour delay
```

Change to:
```javascript
setTimeout(() => {
    checkForUpdates();
    // ...
}, 5000); // 5 seconds for testing
```

## Testing with Mock Data

To test the UI without actually hitting GitHub API, you can temporarily modify the `check_for_updates()` function to return mock data:

```python
def check_for_updates(force=False):
    # For testing - return mock update available
    return {
        'available': True,
        'current_version': '1.0.7',
        'latest_version': '1.0.8',
        'release_url': 'https://github.com/onelenyk/gradik/releases/tag/v1.0.8',
        'sha256': None,
        'changelog': 'Test changelog:\n- Feature 1\n- Feature 2\n- Bug fix',
        'error': None
    }
```

## Expected Behavior Summary

### When Running as Python Script:
- Update check API returns: `{"error": "Updates only available for binary installations"}`
- CLI command shows: "Updates are only available for binary installations"
- UI won't show update banner (no updates available for scripts)

### When Running as Binary:
- Update check works normally
- If update available: Banner appears, can install
- If no update: Shows "You're running the latest version"
- Installation: Downloads, verifies, replaces binary, restarts daemon

## Troubleshooting

### Update check not working?
- Check internet connection
- Check GitHub API is accessible: `curl https://api.github.com/repos/onelenyk/gradik/releases/latest`
- Check browser console for JavaScript errors

### Update banner not showing?
- Check if update is actually available (current version vs latest)
- Check browser console for errors
- Try manual check: `checkForUpdates(true)` in console
- Check if dismissed: `localStorage.getItem('update_dismissed')`

### Installation fails?
- Check write permissions on binary location
- Check if running as binary (not script)
- Check logs for specific error messages
- Verify binary path is correct
