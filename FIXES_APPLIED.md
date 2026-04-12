# ProctorSense AI — False Positives & Screenshot Management Fixes

## Applied Fixes (April 12, 2026)

### 1. ✅ **Reduced False Positives in Neck Detection**
- **Previous threshold**: 12° neck angle
- **New threshold**: 20° neck angle
- **Effect**: Reduces casual head movements from triggering false alerts while still catching significant head tilts (looking at external screens/phones)
- **File**: [app.py](app.py#L154)

### 2. ✅ **Reduced False Positives in Eye Gaze Detection**
- **Previous gaze deviation threshold**: 0.25
- **New gaze deviation threshold**: 0.35
- **Effect**: Only flags significant eye movements away from screen, not natural gaze variations and blinking
- **File**: [app.py](app.py#L146)

### 3. ✅ **Score Multiplier Calibration**
- **Eye score multiplier**: 150 → 120 (reduced sensitivity)
- **Neck score multiplier**: 120 → 100 (reduced sensitivity)
- **Effect**: More conservative scoring to reflect higher thresholds

### 4. ✅ **Automatic Screenshot Cleanup on App Startup**
- Added `cleanup_old_screenshots()` function that runs when Flask app initializes
- **Location**: Executes before creating new session
- **Behavior**: 
  - All old `.png` and `_meta.json` files in `/screenshots/` folder deleted
  - Fresh screenshot folder ready for new session
  - Prevents screenshot accumulation from previous runs
- **File**: [app.py](app.py#L510-L523)

### 5. ✅ **Screenshot Storage Confirmed**
- Screenshots save to: `/home/uday/code/Anomaly/screenshots/`
- Format: 
  - **Image**: `frame_XXXX_TYPE_TIMESTAMP.png` (actual canvas frames)
  - **Metadata**: `frame_XXXX_TYPE_TIMESTAMP_meta.json` (detection data)
- **Endpoint**: `POST /api/screenshot` receives base64 canvas data from frontend

---

## Testing Verification

### Detection Thresholds
```
Gaze Deviation:     0.35 (was 0.25)  ✓
Neck Angle:         20°  (was 12°)   ✓
Eye Multiplier:     120  (was 150)   ✓
Neck Multiplier:    100  (was 120)   ✓
```

### Screenshot Management  
```
Cleanup on startup: ENABLED          ✓
Screenshot folder:  /screenshots/    ✓
Image retention:    NEW ONLY         ✓
```

---

## Expected Behavior Changes

### Before
- Minor head movements → neck anomaly flag
- Natural eye movements → gaze anomaly flag
- Old screenshots accumulating across sessions

### After
- Only significant head tilts (>20°) → anomaly flag
- Only major gaze deviations (>0.35) → anomaly flag  
- Fresh screenshot directory on each app restart
- Both audio and visual evidence saved with timestamps

---

## Configuration Summary

**File**: [app.py](app.py)  
**Lines Modified**:
- **146-154**: Gaze & neck detection thresholds + score multipliers
- **510-523**: Startup cleanup function

All changes maintain backward compatibility with existing detection pipeline while significantly reducing false positives.
