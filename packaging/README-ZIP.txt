Video Workbench - Windows zip package

How to run:
1. Extract the whole zip package to a normal folder, for example Desktop\video-workbench.
2. Double-click start-video-workbench.bat.
3. The browser should open http://127.0.0.1:7860 automatically.

Do not:
- Do not run files directly inside the zip preview window.
- Do not move video-workbench.exe away from the _internal folder.
- Do not delete the _internal folder.

Data and config:
- Local projects are saved in the workspace folder beside video-workbench.exe.
- Optional API configuration can be put in .env beside video-workbench.exe.
- If startup fails, check startup-error.log in this folder.

Bundled dependencies:
- Python runtime
- FFmpeg / FFprobe
- Static web UI and default assets
