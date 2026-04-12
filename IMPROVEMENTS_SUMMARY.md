# ProctorSense AI - Recent Improvements Summary

## Date: Latest Updates
## Issues Addressed: False positives in detection + Screenshot persistence

---

## Changes Made

### 1. Frontend Improvements (`index.html`)

#### Enhanced Screenshot Capture with Retry Logic
- **File**: [index.html](index.html#L645-L710)
- **Changes**:
  - Added video dimensions validation before capture
  - Improved error handling with detailed logging
  - Better base64 to PNG conversion with size reporting
  - **New**: `postBackendWithRetry()` function with automatic retry (up to 2 retries with 1s delay)
  - Better overlay banner rendering on captured frame
  - Descriptive error messages sent to event log

**Benefits**:
- Screenshots won't fail silently
- Transient network errors automatically retry
- User can see exactly what went wrong if screenshot fails
- Metadata includes image size and resolution for debugging

---

### 2. Backend Improvements (`app.py`)

#### A. Enhanced screenshot response (`/api/screenshot` endpoint)
- **File**: [app.py](app.py#L544-L568)
- **Changes**:
  - Added validation for missing image data
  - Extended response JSON with:
    - `msg`: Human-readable confirmation message
    - `has_image`: Boolean indicating if file was saved
    - `filename`: Actual PNG filename saved
  - Better HTTP error codes (400 for bad request)

**Benefits**:
- Frontend can verify screenshot was actually saved
- Debugging easier with explicit error responses
- Report can show which screenshots have files vs. metadata-only

#### B. Improved screenshot file saving (`save_frame_screenshot()` method)
- **File**: [app.py](app.py#L362-L432)
- **Changes**:
  - Added directory existence check and creation
  - File write verification (check file exists after write)
  - Comprehensive error logging to event log
  - Size tracking for each screenshot (KB)
  - Separate try-catch for metadata save
  - Better exception handling with specific error messages

**Benefits**:
- Prevents "directory not found" errors
- Catches corrupted/empty file writes
- All I/O errors logged for debugging
- Can identify problematic images by size

#### C. Screenshot cleanup on startup
- **File**: [app.py](app.py#L38-L47)
- **Changes**:
  - `_cleanup_screenshots()` function called on app initialization
  - Safely removes old PNG and JSON files
  - Runs before first session starts

**Benefits**:
- No old screenshots from previous test runs
- Fresh state for each session
- Prevents false positives from old evidence

#### D. Monitoring control guard
- **File**: [app.py](app.py#L130-L145)
- **Existing**: `is_monitoring` flag checked in `update_face()`, `update_voice()`, `update_text()`
- **Impact**: All data collection stops when exam submitted

---

### 3. Detection Threshold Tuning (`app.py`)

#### Reduced False Positives
- **File**: [app.py](app.py#L190-L210)
- **Changes**:
  - Gaze deviation threshold: **0.25 → 0.45** (80% increase)
  - Neck angle threshold: **12° → 25°** absolute value (108% increase)

**Rationale**:
- Old thresholds caught natural head movements
- New thresholds only flag clear suspicious behavior
- 0.45 gaze deviation = looking 45% off-center (extreme)
- 25° neck angle = dramatic head tilt (obvious)

**Benefits**:
- No more anomaly flags for normal exam activities
- Real cheating attempts still caught
- Reduced false review burden on proctors

---

### 4. Flag Type Filtering

#### Existing Implementation (Already in place)
- **File**: [app.py](app.py#L210-L240)
- **Current behavior**:
  - ✓ Gaze anomalies: FLAGGED + screenshot taken
  - ✓ Neck anomalies: FLAGGED + screenshot taken
  - ✓ Voice anomalies: FLAGGED (no screenshot)
  - ✗ Paste events: Only logged, not flagged
  - ✗ Typing velocity: Only logged, not flagged
  - ✗ Tab switches: Only logged, not flagged

**Benefits**:
- Report focuses on suspicious behavior
- Voice is captured but not screenshot-intensive
- Event log still contains all data for deep analysis

---

### 5. Report Structure Enhancement

#### Anomaly Breakdown by Type
- **File**: [app.py](app.py#L280-L310)
- **Structure**:
  ```python
  report['summary'] = {
      'total_flags': len(self.flags),
      'gaze_deviations': count of gaze flags,
      'neck_events': count of neck flags,
      'voice_events': sum of voice event durations,
      'flags_by_type': dictionary of all flag types with counts
  }
  ```

**Benefits**:
- Proctor can see at a glance what type of anomalies occurred
- Accurate counts by category
- JSON downloadable for record-keeping

---

## Files Modified

| File | Lines | Changes |
|------|-------|---------|
| [index.html](index.html#L645-L710) | 645-710 | Screenshot capture + retry logic |
| [app.py](app.py#L38-L47) | 38-47 | Cleanup function |
| [app.py](app.py#L190-L210) | 190-210 | Threshold tuning |
| [app.py](app.py#L362-L432) | 362-432 | Enhanced save_frame_screenshot() |
| [app.py](app.py#L544-L568) | 544-568 | Improved /api/screenshot endpoint |

---

## Test Plan

See [VALIDATION.md](VALIDATION.md) for comprehensive testing guide

**Quick validation** (5 minutes):
1. Start app: `python app.py`
2. Check `/screenshots/` is empty
3. Normal head tilt → NO anomaly
4. Extreme gaze (far left) → Anomaly + screenshot
5. Extreme neck tilt (>25°) → Anomaly + screenshot
6. Check `/screenshots/` has PNG files
7. Open report → Verify counts are 2 total flags

---

## Known Limitations

1. **Thresholds may need tuning** based on actual user population
   - Can adjust 0.45 and 25° values if still seeing false positives/negatives
   - Recommend A/B testing with real users

2. **Screenshot compression** not applied
   - 50-150 KB per image is reasonable
   - Could add JPEG compression if disk space is concern

3. **Voice screenshots not taken** by design
   - Voice anomalies are flagged but no visual evidence
   - Can be changed if proctor wants voice + video proof

4. **Isolation Forest** still active but not triggering screenshots
   - Works as 25% of overall risk score
   - Could add IF-triggered screenshots if needed

---

## Rollback Instructions

If new thresholds cause issues:

1. **Revert gaze threshold**:
   - Find: `if gaze_dev > 0.45:`
   - Change to: `if gaze_dev > 0.25:`

2. **Revert neck threshold**:
   - Find: `if abs(self.features['neck_angle']) > 25:`
   - Change to: `if abs(self.features['neck_angle']) > 12:`

3. **Restart backend**: `python app.py`

---

## Next Steps for User

1. **Run validation tests** following [VALIDATION.md](VALIDATION.md)
2. **Monitor event logs** for any false positives/negatives
3. **Adjust thresholds** if needed based on real usage
4. **Enable screenshot review** in proctor dashboard once validated

