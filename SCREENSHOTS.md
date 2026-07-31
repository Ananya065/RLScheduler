# Screenshots

This section is intentionally left as a template — screenshots depend on your
actual terminal theme, screen size, and the workload you run, so pre-made
images here would misrepresent your specific setup. Fill it in after your
first run:

## How to capture these

1. **Dashboard — Live Replay view**
   Open `dashboard/scheduler_dashboard.html`, let a workload load, and
   screenshot the Gantt chart + queue lanes + metrics panel.
   → Save as `docs/screenshots/dashboard_replay.png`

2. **Dashboard — Compare view**
   Click "Compare Algorithms" in the sidebar.
   → Save as `docs/screenshots/dashboard_compare.png`

3. **Dashboard — Workload Setup (Custom Process Input)**
   Click "Workload Setup" → "Custom Process Input" tab.
   → Save as `docs/screenshots/dashboard_custom_input.png`

4. **PDF report cover page**
   Run `python main.py`, open `results/scheduling_report.pdf`, screenshot
   or export page 1.
   → Save as `docs/screenshots/pdf_report_cover.png`

5. **CLI output**
   Screenshot the terminal after running `python main.py`.
   → Save as `docs/screenshots/cli_output.png`

## Suggested README embed

Once captured, reference them in the main README like this:

```markdown
![Dashboard Replay View](docs/screenshots/dashboard_replay.png)
![Algorithm Comparison](docs/screenshots/dashboard_compare.png)
```
