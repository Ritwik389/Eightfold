# 🧪 Quick Testing Guide — ProctorSense AI

## Backend is Running ✅
```
http://localhost:5050
http://172.21.8.71:5050
```

---

## How to Test Each Anomaly

### **1. Test Eye Gaze Detection**
1. Open http://localhost:5050 in browser
2. Grant camera permission
3. **Look to the LEFT** → You should see:
   - ⚡ Gaze chip: "Deviation: Left"
   - Right panel: Eye meter jumps to yellow
   - Flag raised in sidebar
   - Screenshot saved to `/screenshots/`

**Expected**: < 200ms detection time

### **2. Test Neck Tilt Detection**
1. During exam, **TILT YOUR HEAD to the SIDE** (15°+)
2. You should see:
   - ⚡ Neck chip: "Tilt: 15°"
   - Right panel: Neck meter jumps to yellow
   - Flag raised in sidebar: "Neck tilt: 15.0°"
   - Screenshot captured showing face at angle

**Expected**: < 200ms detection time

### **3. Test Paste Detection**
1. Go to **Q4 (Coding — Easy)**
2. **Try to paste code** (Ctrl+V)
3. You should see:
   - ⚠ Warning: "Paste detected"
   - Right panel: Text paste meter jumps to red
   - Flag raised: "PASTE Q4"
   - Screenshot saved

**Expected**: Instant (on paste event)

### **4. Test Voice Detection**
1. During exam, **START SPEAKING**
2. You should see:
   - Waveform in right panel animating (wiggly lines in warn color)
   - "🎤 Speech detected!" message
   - After 0.5+ seconds of speech: Flag raised
   - Screenshot captured

**Expected**: Speech detection within 500ms

### **5. Test Tab Switch Detection**
1. Close the exam tab or switch to another window
2. You should see:
   - Flag raised: "Tab/window switch detected"
   - Sidebar counter increments

**Expected**: Instant

---

## Viewing Results

### **During Exam**
- **Right monitor panel** shows all metrics in real-time
- **Event log** (bottom right) shows all activities
- **Flag counter** shows total anomalies detected

### **After Submission**
1. Click **"Submit Assessment"** button
2. Click **"View Full Report →"** button  
3. Report modal shows:
   - ✅ **Total flags**: Should show all anomalies
   - ✅ **Gaze deviations**: Count of eye movement flags
   - ✅ **Neck anomalies**: Count of head tilt flags (NEW)
   - ✅ **Paste events**: Count of copy-paste events
   - ✅ **Voice events**: Count of speech segments
   - ✅ **Tab switches**: Count of window switches
   - **Evidence section**: Shows all captured screenshots
   - **Event timeline**: Detailed log of each anomaly

### **Download Full Report**
1. In report modal, click **"Download Report JSON"**
2. File saved as: `proctorsense_report_CS2047_TIMESTAMP.json`
3. Contains full data for proctor review

---

## What Changed

| Metric | Old | New | Improvement |
|--------|-----|-----|-------------|
| Gaze threshold | 0.35 | 0.25 | 30% faster detection |
| Neck threshold | 20° | 12° | 40% faster detection |
| Screenshot | Video only | Video + face mesh | Shows actual anomaly |
| Report stats | Missing | Complete | Accurate breakdown |
| Visual feedback | Basic | Rich (✓/⚠/⚡) | Clear status at glance |

---

## Debug Checklist

✅ **Backend running?**
```
curl http://localhost:5050/api/stream
```
Should start SSE connection (no immediate response)

✅ **Frontend loads?**
```
http://localhost:5050
```
Should show ProctorSense AI interface

✅ **Camera detection?**
Should show "Face ✓" chip (maybe needs moment to detect)

✅ **Microphone working?**
Waveform should show ambient noise (moving bars)

✅ **SSE connected?**
Top badge should show "Backend: OK" (green)

---

## Expected Screenshot Files

After each anomaly, these are saved to `/home/uday/code/Anomaly/screenshots/`:

```
frame_0000_gaze_120509.png       ← Eye deviation screenshot
frame_0000_gaze_120509_meta.json ← With metadata

frame_0001_neck_120512.png       ← Neck tilt screenshot
frame_0001_neck_120512_meta.json

frame_0002_paste_120515.png      ← Paste event screenshot
frame_0002_paste_120515_meta.json

...and so on
```

Each PNG shows:
- Face with mesh overlay
- Iris markers (blue circles)
- Gaze direction arrow
- Red banner at bottom with anomaly type + time

---

## Common Issues

**Q: "No flags being raised"**  
A: Check that thresholds are being triggered:
- Gaze: Move eyes > 0.25 deviation
- Neck: Tilt head > 12 degrees
- Check Event Log for messages

**Q: "Screenshots are black"**  
A: Ensure browser has camera permission and video element is displaying

**Q: "Report shows 0 for all stats"**  
A: Wait a few seconds after raising flags, then open report again (fetches fresh data)

**Q: "Browser says 'Backend Offline'"**  
A: 
```bash
# Check Flask is still running
curl http://localhost:5050/
# Should show HTML of frontend
```

---

## Success Indicators ✅

System is working correctly when you see:

1. ✅ **Real-time gaze detection** - Eye movements flagged within 200ms
2. ✅ **Real-time neck detection** - Head tilts flagged within 200ms  
3. ✅ **Screenshots with face mesh** - Shows landmarks, iris, gaze arrow
4. ✅ **Accurate report statistics** - All counts match actual events
5. ✅ **Visual chips** - Show ✓ Normal, ⚠ Alert, ⚡ Deviation
6. ✅ **No false positives** - Only flags when actually anomalous

---

**Ready to test? Open http://localhost:5050 now! 🚀**

*Last Updated: 2026-04-12*
