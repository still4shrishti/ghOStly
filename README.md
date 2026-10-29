# 👻 ghOStly

An eerie and innovative **2D Action-Shooter Game** where your own desktop environment turns against you! Upon launch, the game captures a snapshot of your screen and mutates your apps, folders, and text into hostile anomalies. 

Will you exorcise the ghosts haunting your desktop, or will you succumb to the monster within?

---

## 🔥 Features

* **Desktop Camouflage Mechanic:** The game dynamically crops your real desktop icons and turns them into floating, twitching entities.
* **The Little Exorcist (Hero):** Control a robed wizard holding a glowing lantern that illuminates the dark voids left by your missing desktop items.
* **Intense Final Boss Fight:** Once the minor entities are cleared, the desktop fragments converge into the center to assemble **"The Desktop Beast"**—a towering humanoid titan plated with your own icons.
* **Cinematic Horror Twist:** A scripted atmospheric ending sequence that shifts the focus directly onto the player.
* **Immersive Visuals:** Features dynamic lighting glows, active vignette shading, tactical screen shakes, and eerie screen-darkening flickers.

---

## 🕹️ Controls

| Action | Input |
| :--- | :--- |
| **Movement** | `W`, `A`, `S`, `D` or `Arrow Keys` |
| **Aiming** | Move your mouse cursor |
| **Shoot Magic Orb** | `Spacebar` or `Left Mouse Click` |
| **Exit Game** | `ESC` (Escape Key) |

---

## 🛠️ Installation & Setup

Follow these steps to deploy and run the game on your system:

### 1. Prerequisites
Ensure you have **Python 3.x** installed on your machine.

### 2. Install Dependencies
Open your terminal or Command Prompt (CMD) and execute the following command:
```bash
pip install numpy opencv-python mss pygame
```

### 3. Audio Asset Setup (Optional but highly recommended)
Place your audio files (`.mp3`, `.wav`, or `.ogg`) in the same directory as the script using these exact filenames:
* `bgm` — Background ambient loops
* `wake` — Entity awakening sound
* `shoot` — Magic projectile sound
* `purify` — Cleansing/Defeating an enemy
* `hurt` — Player taking damage
* `lose` — Game over music/sound effect

### 4. Run the Game
```bash
python game.py
```


---

## 🎭 Gameplay Flow

1. **The Ghost Menu:** A small, floating window titled "Boo..." appears. You can move this window anywhere on your screen. Clicking **START** unloads the menu.
2. **The Desktop Capture:** The engine waits 0.5 seconds for the screen to clear up, then snaps a screenshot of your primary monitor.
3. **The Cleansing Phase:** Your actual icons are cut out, leaving dark voids on your background. The entities ambush you, forcing you to shoot them down.
4. **The Awakening:** The pieces collapse into a massive boss fight.
5. **The Epilogue:** Defeating the beast initiates a slow, dark, interactive narrative sequence.

---

## 💻 Compatibility
* **Windows:** Fully optimized with native DPI awareness and automated Top-Most window positioning configurations.
* **Linux / macOS:** Supported (Windows-specific layout adjustments will automatically bypass gracefully without breaking gameplay loop functionality).

---
*Disclaimer: ghOStly only processes a temporary visual buffer of your screen. It does not modify, delete, or endanger any actual files, shortcuts, or registries on your computer.*
