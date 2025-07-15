# 🐉 DanMachi DnD Combat Simulator

**DanMachi DnD Combat Simulator** is a Python-based combat simulation framework tailored for Dungeons & Dragons (5e) inspired gameplay, specifically integrating elements from the DanMachi universe. The system is meant for resolving single-instance combat scenarios.

---

## 📂 Project Structure

```bash
.
├── data/                           # JSON data files
│   ├── player.json
│   ├── actions.json
│   ├── characters.json
│   ├── character_races.json
│   ├── enemies_danmachi_f1_f10.json
│   ├── character_classes.json
│   ├── attacks.json
│   ├── armors.json
│   └── spells.json
│
├── simulator/                      # Core source code for simulator
│   ├── main.py                     # Main executable file
│   ├── actions/                    # Player and NPC actions
│   ├── combat/                     # Combat management and AI logic
│   ├── core/                       # Utilities, constants, and shared content
│   ├── effects/                    # Buffs, debuffs, and effects
│   ├── entities/                   # Characters, classes, races
│   └── ui/                         # User interface components
│
├── LICENSE.md                      # License information
└── README.md                       # This readme file
```

---

## 🛠️ Getting Started

### 📋 Prerequisites

- Python 3.10 or newer
- Recommended: virtual environment (venv)

### 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/Galfurian/danmachi_dnd_combat_simulator.git
cd danmachi_dnd_combat_simulator
```

Create and activate a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies (if `requirements.txt` exists):

```bash
pip install -r requirements.txt
```

### ⚔️ Running the Simulator

Start the simulator from the `simulator` folder:

```bash
python main.py
```

---

## 🎮 Gameplay Overview

The **DnD Combat Simulator** provides:

- Tactical combat encounter against intelligent NPCs.
- Spell casting, attack mechanics, and effect handling.
- Clear, interactive command-line interface (CLI).

---

## 📁 Data Structure

All entities and actions are stored as JSON files within the `data` directory:

- **player.json**: Player character definitions.
- **actions.json**: General action definitions.
- **enemies_danmachi_f1_f10.json**: Enemies from DanMachi floors 1-10.
- Other JSON files: Classes, races, armors, spells, and more.

---

## ⚙️ Extending the Simulator

Easily extend the simulator by:

- Adding new actions, effects, or entities to the corresponding JSON files.
- Implementing new game logic in `simulator/core`.
- Customizing the AI behaviors defined in `simulator/combat/npc_ai.py`.

---

## 📝 License

This project is distributed under the terms of the license found in `LICENSE.md`.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests to enhance the project.
