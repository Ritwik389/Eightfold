# ProctorSense AI - Validation Guide

## Recent Fixes Applied

### 1. **Detection Threshold Tuning** (Reduced False Positives)
- Gaze deviation threshold: increased from **0.25 → 0.45**
- Neck angle threshold: increased from **12° → 25°**
- Impact: Normal head movements and natural eye gaze no longer trigger false anomalies

### 2. **Screenshot Persistence Improvements**
- Frontend: Enhanced error handling with retry logic (up to 2 retries on failure)
- Backend: Improved `save_frame_screenshot()` with directory verification and file write validation
- Backend: Better error logging for file I/O failures
- Extended metadata: Now includes image size in KB for debugging

### 3. **Monitoring Control**
- Anomaly detection stops immediately when assessment is submitted
- `is_monitoring` flag controls all data collection
- Old screenshots automatically deleted on app startup and reset

### 4. **Flag Filtering**
- Only gaze, neck, and voice anomalies generate flags
- Paste, typing velocity, and tab-switch events only logged (no false flags)
- Voice anomalies flagged but **no screenshots taken** for voice

---

## Validation Checklist

### Phase 1: Startup and Cleanup (2 minutes)

1. **Terminal**: Check initial screenshot directory
   ```bash
   ls -la /home/uday/code/Anomaly/screenshots/
   ```
   - ✓ Should show empty directory or only cleanup happening
   - ✓ Verify no old PNG/JSON files from previous test runs

2. **Start the application**
   ```bash
   cd /home/uday/code/Anomaly
   python app.py
   ```
   - ✓ Backend should print: `Application started. Screenshots cleaned up.` (or similar)
   - ✓ Terminal shows `* Running on http://localhost:5050`

3. **Open browser**: Navigate to `http://localhost:5050`
   - ✓ Permission overlay appears
   - ✓ Click "Grant Access & Begin"
   - ✓ Camera feed appears with face mesh overlays
   - ✓ Backend status shows "OK"

---

### Phase 2: Test False Positive Reduction (3 minutes)

**Objective**: Verify that normal behavior does NOT trigger anomalies

4. **Normal head movement** (natural exam behavior)
   - Tilt head left and right (small movements, < 20°)
   - Nod head gently
   - Look at different areas of screen naturally
   - ✗ NO anomalies should be flagged
   - ✗ NO screenshots should be captured
   - ✓ Chips show "Gaze: Forward", "Neck: Normal"
   - ✓ Anomaly meters stay at 0%

5. **Natural eye gaze** (reading from screen)
   - Look at Q1, then Q2, then Q3
   - Brief glances left/right to read code
   - ✗ NO gaze anomaly flags
   - ✗ Event log shows no anomalies

6. **Check screenshot directory** (should still be empty)
   ```bash
   ls -la /home/uday/code/Anomaly/screenshots/ | wc -l
   ```
   - ✓ Should show 0-1 items (just `.` and `..`)

---

### Phase 3: Test Actual Anomaly Detection (3 minutes)

**Objective**: Verify that REAL anomalies ARE detected

7. **Trigger eye anomaly** (extreme gaze deviation)
   - Look far to the right, hold for 2 seconds
   - Look back to center
   - ✓ "GAZE" anomaly should be flagged
   - ✓ Screenshot should appear in "Evidence Screenshots" section
   - ✓ Flag appears in "Active Flags" with timestamp

8. **Trigger neck anomaly** (extreme head tilt)
   - Tilt head >25° to one side
   - Hold for 2 seconds
   - ✓ "NECK" anomaly should be flagged
   - ✓ Screenshot should be captured
   - ✓ Screenshot file saved to `/screenshots/frame_000X_neck_HHMMSS.png`

9. **Check screenshot files**
   ```bash
   ls -la /home/uday/code/Anomaly/screenshots/ | grep -E "(frame.*\.png|_meta\.json)"
   ```
   - ✓ Should see 2 PNG files + 2 JSON metadata files
   - Example: `frame_0000_gaze_152530.png` + `frame_0000_gaze_152530_meta.json`

10. **Verify file contents**
    ```bash
    file /home/uday/code/Anomaly/screenshots/frame_*.png
    ```
    - ✓ Each should be a valid PNG file (not corrupt)
    - ✓ File size > 10KB (not empty)

11. **View metadata**
    ```bash
    cat /home/uday/code/Anomaly/screenshots/frame_*_meta.json | head -20
    ```
    - ✓ JSON contains: `id`, `type` ("gaze"/"neck"), `has_image: true`, `img_filename`

---

### Phase 4: Test Voice Anomaly (2 minutes)

**Objective**: Verify voice flags are raised but NO screenshots taken

12. **Trigger voice anomaly**
    - Speak/hum for 3+ seconds
    - Should register as speech in waveform
    - ✓ Voice flag should appear in "Active Flags"
    - ✓ Waveform should show activity (animated bars)
    - ✗ NO screenshot should be captured for voice

13. **Check screenshots**
    ```bash
    ls -la /home/uday/code/Anomaly/screenshots/ | grep voice
    ```
    - ✓ Should return NO results (no voice screenshots)

---

### Phase 5: Test Report Accuracy (2 minutes)

14. **Click "View Full Report →"**
    - ✓ Modal opens showing "Anomaly Report"
    - ✓ Summary section shows:
      - Total flags: 3 (gaze + neck + voice)
      - Gaze deviations: 1
      - Voice events: 1
      - Paste events: 0
    - ✓ Evidence section shows 2 screenshots (gaze + neck, NOT voice)

15. **Verify screenshot display**
    - ✓ Both screenshots visible with thumbnails
    - ✓ Each labeled with correct type ("GAZE ANOMALY", "NECK ANOMALY")
    - ✓ Timestamps shown correctly
    - ✓ Can click to verify image content

16. **Download report JSON**
    - ✓ Report modal → "Download Report JSON"
    - ✓ File downloads as `anomaly_report_CS-2047.json`
    - ✓ Open and verify structure:
    ```json
    {
      "summary": {
        "total_flags": 3,
        "gaze_deviations": 1,
        "neck_events": 1,
        "voice_events": 1,
        "flags_by_type": {
          "gaze": 1,
          "neck": 1,
          "voice": 1
        }
      },
      "screenshots": [
        {
          "id": "frame_0000_gaze_...",
          "type": "gaze",
          "has_image": true
        },
        {
          "id": "frame_0001_neck_...",
          "type": "neck",
          "has_image": true
        }
      ]
    }
    ```

---

### Phase 6: Test Submission Flow (2 minutes)

17. **Answer a question**
    - Select Q1 answer
    - Type answer to Q4 (code editor)
    - ✓ Monitoring continues normally

18. **Submit assessment**
    - Click "Submit Assessment" button
    - ✓ Backend logs: "Assessment submitted. Monitoring stopped."
    - ✓ Status badge changes
    - ✓ Report modal opens showing final counts

19. **Trigger anomaly AFTER submission**
    - Tilt head dramatically left (>25°)
    - Speak loudly
    - ✗ NO new anomalies should be recorded
    - ✓ Flag count remains same

20. **Verify submission stopped monitoring**
    - Close browser
    - Run: `curl http://localhost:5050/api/report`
    - ✓ JSON shows final flags count (should NOT increase)

---

### Phase 7: Test Reset and Restart (2 minutes)

21. **Reset the session**
    ```bash
    curl -X POST http://localhost:5050/api/reset
    ```
    - ✓ Returns: `{"ok": true}`
    - ✓ Backend logs session reset

22. **Check screenshots deleted**
    ```bash
    ls -la /home/uday/code/Anomaly/screenshots/
    ```
    - ✓ Directory empty (all PNG/JSON files deleted)

23. **Restart browser**
    - Refresh `http://localhost:5050`
    - ✓ Permission overlay appears again
    - ✓ Camera initializes
    - ✓ No old flags shown
    - ✓ No old screenshots in Evidence section

---

## Debugging Checklist

If any test fails, use these commands to diagnose:

### Screenshot Files Not Created
```bash
# Check directory permissions
ls -ld /home/uday/code/Anomaly/screenshots/
chmod 755 /home/uday/code/Anomaly/screenshots/

# Check write access
touch /home/uday/code/Anomaly/screenshots/test.txt && rm $_

# Monitor file creation in real-time
watch -n 0.5 'ls -la /home/uday/code/Anomaly/screenshots/'
```

### Backend Errors
```bash
# Check backend logs for file I/O errors
# Terminal should show error messages like:
# "Screenshot save error (gaze): [Errno 2] No such file or directory"

# Verify base64 encoding working:
python3 -c "import base64; print(len(base64.b64decode('base64string')))"
```

### False Positives Still Occurring
```bash
# Check thresholds were applied correctly
grep -n "gaze_dev > 0.45" /home/uday/code/Anomaly/app.py
grep -n "abs.*neck_angle.*> 25" /home/uday/code/Anomaly/app.py

# Expected: Lines should show 0.45 and 25, not old values
```

### Screenshots Not Displaying in Report
```bash
# Check backend can serve screenshot files
curl http://localhost:5050/screenshots/frame_0000_gaze_HHMMSS.png > /tmp/test.png
file /tmp/test.png  # Should be "PNG image"
```

### Monitoring Not Stopping on Submit
```bash
# Check is_monitoring flag in backend
grep -n "is_monitoring = False" /home/uday/code/Anomaly/app.py

# Verify it's checked during capture:
grep -n "if.*is_monitoring" /home/uday/code/Anomaly/app.py
```

---

## Expected Behavior Summary

| Scenario | Threshold | Outcome | Screenshot |
|----------|-----------|---------|-----------|
| Normal eye gaze (< 0.45 deviation) | gaze_dev ≤ 0.45 | ✓ No flag | ✗ No |
| Extreme eye deviation (> 0.45) | gaze_dev > 0.45 | ✓ Flag | ✓ Yes |
| Normal head tilt (< 25°) | neck_angle ≤ 25° | ✓ No flag | ✗ No |
| Extreme neck tilt (> 25°) | neck_angle > 25° | ✓ Flag | ✓ Yes |
| Speech/VAD detected | voice > threshold | ✓ Flag | ✗ No |
| Paste event | paste detected | ✗ No flag* | ✗ No |
| Fast typing | velocity > threshold | ✗ No flag* | ✗ No |
| Tab switch | visibility changed | ✗ No flag* | ✗ No |

*Logged to event log only, not flagged

---

## Success Criteria

✅ **All tests pass if:**
1. Normal behavior triggers NO anomalies (Phase 2)
2. Real anomalies ARE detected and flagged (Phase 3)
3. Screenshots saved to disk with correct filenames and valid PNG format
4. Metadata JSON files created alongside PNG files
5. Report shows accurate counts matching actual flags raised
6. Voice anomalies flagged but NO screenshots taken
7. Monitoring stops when exam submitted (no new flags after submit)
8. Old screenshots deleted on reset and restart
9. File sizes are reasonable (not empty, typically 50-150 KB per screenshot)

---

## Support

If issues persist, check:
- Backend terminal for specific error messages
- Browser console (F12 → Console tab) for frontend errors
- `/home/uday/code/Anomaly/screenshots/` directory for file artifacts
- Latest log entries in event log panel

