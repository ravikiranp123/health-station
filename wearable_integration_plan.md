# Wearable Integration Plan (The Local-First Way)

**Goal:** Sync Mi Band data (Sleep, Steps, Heart Rate) to HealthOS without Cloud APIs.

**Strategy:** Gadgetbridge (Android) -> Auto-Export -> Syncthing -> HealthOS Ingest Script.

## 1. Mobile Setup (Android)
*   **App:** Install **Gadgetbridge** (via F-Droid).
*   **The Hard Part (Auth Key):**
    *   Xiaomi devices are encrypted. You need a unique "Auth Key" to pair.
    *   **Method:** Use the `huami-token` script on your Mac.
        1.  Install Python dependencies: `pip3 install -r requirements.txt`.
        2.  Run: `python3 huami_token.py --method xiaomi --email <your_email> --password <your_pass> --bt_keys`.
        3.  Result: Terminal outputs a `0x...` key.
        4.  Input this key into Gadgetbridge when pairing.
*   **Automation:**
    *   Settings > Auto Export > **Enable Auto Export Database**.
    *   Path: Set to `HealthOS/inbox` (The folder synced via Syncthing).
    *   Frequency: Every 6 hours (or "On Connect").

## 2. Sync Layer (Syncthing)
*   **Mechanism:** Syncthing already monitors `HealthOS/inbox`.
*   **Result:** The file `Gadgetbridge.sqlite` (or CSV) appears in `/Users/ravi/projects/health-station/logs/inbox/` automatically.

## 3. Ingestion Layer (Mac Script)
*   **Script:** `system/scripts/ingest_wearable.py`
*   **Trigger:** Manual run or Cron job (e.g. 8 AM).
*   **Logic:**
    1.  Read `logs/inbox/Gadgetbridge.sqlite`.
    2.  Query `MI_BAND_ACTIVITY_SAMPLE` table (Steps, Intensity) and `SLEEP` table.
    3.  Compute: Total Steps, Sleep Duration (Deep/Light), Resting HR.
    4.  **Update:**
        *   `state/current_context.json` (Update `fatigue_level` based on sleep).
        *   `logs/journal/YYYY-MM-DD.md` (Append "Bio-Data" section).

## Alternative (If Gadgetbridge is too hard)
*   **Notify for Mi Band:** Can export CSV. Easier pairing.
*   **Manual CSV:** Export from Mi Fit -> Save to Drive -> Download. (High Friction).

**Recommendation:** Proceed with Gadgetbridge for a true "Life Engine".
