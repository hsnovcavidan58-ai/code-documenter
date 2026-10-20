# Code Documenter

A professional, single-file GUI tool built with Python that turns a project folder into a full textual documentation (folder tree + contents of every source file + metadata for images/binary files).

## Features
<img width="1853" height="1037" alt="Screenshot From 2026-10-20 18-47-32" src="https://github.com/user-attachments/assets/cfa2c1b8-6c90-49ea-807c-6147f7c8e82e" />
<img width="1853" height="1037" alt="Screenshot From 2026-10-20 18-47-18" src="https://github.com/user-attachments/assets/259a00c0-82a2-4ee5-89e8-6cb169c0b282" />

*   **Interactive UI:** Modern, card-based layout with smooth hover animations.
*   **Drag & Drop:** Support for dropping folders directly into the app (requires `tkinterdnd2`).
*   **Auto-Refresh:** Automatically detects file changes and updates the documentation.
*   **Smart Filtering:** Skips build directories (e.g., `node_modules`, `.git`) and hidden files by default.
*   **Image Metadata:** Extracts image dimensions without loading the entire file into memory.
*   **Single File:** Easy to run and distribute.

## Requirements
*   Python 3.8 or higher.
*   Optional dependencies (for full functionality):
    *   `tkinterdnd2` (for drag-and-drop)
    *   `Pillow` (for accurate image dimension extraction)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/code-documenter.git
   cd code-documenter
