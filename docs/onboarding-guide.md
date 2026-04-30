# MPD Churn Model — Onboarding Guide for New Team Members

> **Who this is for:** Colleagues with little or no coding experience who need to access, understand, and use this project.
> **Time to complete:** ~90 minutes

---

## Part 1 — Setting Up: Getting the Code onto Your Computer

### What is a Terminal?

A **terminal** (also called a "command line" or "shell") is a text-based way to talk to your computer. Instead of clicking buttons and icons, you type commands and your computer executes them.

This might feel old-fashioned at first, but it's actually faster and more precise than clicking through menus — especially for tasks like running code, installing packages, or managing files.

**How to open a terminal:**

- **Mac:** Press `Cmd + Space`, type `Terminal`, press Enter. A window with a blinking cursor will appear.
- **Windows:** Press `Windows key`, type `PowerShell`, press Enter.

Once it's open, you'll see something like this:

```
joshbinaday@MacBook ~ %
```

That line is called the **prompt**. It's the terminal waiting for your next instruction. You type a command and press Enter to run it.

**A few things to know before you start:**

- Commands are case-sensitive. `Git` and `git` are different things.
- Nothing happens until you press Enter.
- If a command seems to hang (nothing is happening), it's usually still running. Wait for it. If it's truly stuck, press `Ctrl + C` to cancel.
- The terminal always operates inside a specific folder on your computer. You can think of it like having Finder open — there's always a "current location." The `cd` command (short for "change directory") moves you between folders.

**The most common commands you'll use:**

| Command | What it does | Example |
|---|---|---|
| `cd` | Move into a folder | `cd Documents` |
| `cd ..` | Go up one folder level | `cd ..` |
| `ls` (Mac) / `dir` (Windows) | List files in the current folder | `ls` |
| `pwd` | Print your current location | `pwd` |

You don't need to memorise all of these — the guide will tell you exactly what to type at each step.

---

### What is a "repository"?

Think of a **repository (repo)** as a shared Google Drive folder for code — except it also keeps the full history of every change ever made. We use a platform called **GitHub** to host it, and a tool called **Git** to sync it to your local machine.

When you "clone" a repo, you're downloading a full copy of it to your computer.

---

### Step 1 — Install the prerequisites

You need three things installed before you start:

1. **Git** — the version control tool
   - Download from: https://git-scm.com/downloads
   - On Mac, you can also open Terminal and run: `xcode-select --install`
   - Verify it worked: open Terminal and type `git --version` — you should see a version number

2. **VS Code** — the code editor we use
   - Download from: https://code.visualstudio.com
   - Install it like any other Mac/Windows app

3. **Python** — the language the model is written in
   - Download from: https://www.python.org/downloads (get version 3.10 or newer)
   - Verify: in Terminal type `python3 --version`

---

### Step 2 — Clone the repository

1. Open **Terminal** (Mac: press `Cmd + Space`, type "Terminal", press Enter)
2. Decide where you want the project to live. A safe place is your Documents folder:
   ```
   cd ~/Documents
   ```
3. Clone the repo (this downloads everything):
   ```
   git clone https://github.com/My-Performance-Doctor/machine-learning.git
   ```
4. Move into the project folder:
   ```
   cd machine-learning
   ```
5. You now have the full project on your machine.

> **What just happened?** Git connected to GitHub, downloaded all the files, and set up a link so you can pull future updates with one command.

---

### Step 3 — Open the project in VS Code

1. With Terminal still open and inside the `machine-learning` folder, run:
   ```
   code .
   ```
   (The dot means "open the current folder")

2. VS Code will open with the project loaded in the left sidebar (the **Explorer** panel).

> If `code .` doesn't work, open VS Code manually, go to **File > Open Folder**, and select the `machine-learning` folder.

---

## Part 2 — VS Code: A Quick Tour

### The main panels

When VS Code opens, you'll see four key areas:

```
┌──────────────────────────────────────────────────────┐
│  Activity Bar │  Explorer (file list)  │  Editor      │
│  (left icons) │                        │  (open file) │
│               │                        │              │
│               ├────────────────────────┴──────────────│
│               │  Terminal (bottom)                     │
└──────────────────────────────────────────────────────┘
```

- **Activity Bar** (far left icons) — switches between Explorer, Search, Git, and Extensions
- **Explorer** — your file and folder tree, like Finder/File Explorer
- **Editor** — where you read and edit files. Click any file in Explorer to open it here
- **Terminal** — a built-in command line. Open it with `Ctrl + `` ` (backtick) or **View > Terminal**

### Useful keyboard shortcuts

| Action | Mac | Windows |
|---|---|---|
| Open a file by name | `Cmd + P` | `Ctrl + P` |
| Search all files for text | `Cmd + Shift + F` | `Ctrl + Shift + F` |
| Open/close terminal | `Ctrl + `` ` | `Ctrl + `` ` |
| Save a file | `Cmd + S` | `Ctrl + S` |

### Recommended extensions to install

Click the Extensions icon in the Activity Bar (it looks like four squares), search for these, and install them:

- **Python** (by Microsoft) — enables Python language support
- **GitLens** — shows who changed what and when, right inside the editor
- **Markdown Preview Enhanced** — lets you read `.md` files as formatted documents (like this one)

---

## Part 3 — Understanding the Project Structure

When you look at the Explorer panel, you'll see this layout:

```
machine-learning/
├── dashboard.py          ← The main app (what you run to see the dashboard)
├── requirements.txt      ← List of Python packages the project needs
├── Dockerfile            ← Instructions for running the app in the cloud
├── data/                 ← Raw input data files (CSVs)
├── src/                  ← Source code (the model brain)
├── outputs/              ← Results the model produces
├── docs/                 ← Documentation and specs (including this file)
├── MPD_Churn_Model_Explainer.md   ← Plain-language model explainer (read this!)
└── MPD_Churn_Knowledge_Base.md    ← Deep reference knowledge base
```

### What each folder does

#### `data/` — Raw input data

This is where the patient data files live. The model reads these CSVs to do its analysis.

| File | What it contains |
|---|---|
| `fact_mpd_patients.csv` | Core patient records — ID, name, membership details, revenue |
| `patient_engagement.csv` | Aggregated engagement metrics per patient |
| `patient_sms_response.csv` | SMS send/reply history |
| `patient_vimeo_detail.csv` | Vimeo video watch events |
| `patient_fathom_detail.csv` | Fathom check-in call records |

> These files are the raw ingredients. The model processes them to produce the risk scores.

#### `src/` — Source code (the model logic)

This is where the Python code that runs the model lives.

| File | What it does |
|---|---|
| `run_test.py` | Script to run the model and generate output files |
| `test_ai_assistant.py` | Tests the AI explainability assistant feature |

> You generally don't need to edit these files. They run behind the scenes.

#### `outputs/` — Model results

After the model runs, it writes its results here. These are what the dashboard reads.

| File | What it contains |
|---|---|
| `patient_risk_scores.csv` | Every patient's risk score (0–100), tier (Critical/High/Medium/Low), and the signals that drove it |
| `patient_counterfactuals.csv` | "What would need to change for this patient to drop out of the high-risk category?" |
| `test_summary.json` | A summary of the last model run — useful for verifying the model ran successfully |

#### `docs/` — Documentation

Specs and guides for the project. Written in Markdown (`.md` files), which VS Code can render as nicely formatted documents.

| File | What it contains |
|---|---|
| `onboarding-guide.md` | This file — your starting point |
| `data_gaps_spec.md` | Notes on known gaps or issues in the data |
| `event_level_data_spec.md` | Technical spec describing the shape of the engagement data |

#### `dashboard.py` — The main app

This is the heart of what you interact with day-to-day. It's a **Streamlit** app — a Python-based web dashboard that reads the `outputs/` files and displays them in your browser.

You run it from the terminal with:
```
streamlit run dashboard.py
```

It then opens automatically in your browser.

#### `requirements.txt` — Dependencies list

A plain text file that lists every Python package the project needs (like `streamlit`, `pandas`, `plotly`). You install them all at once with:
```
pip install -r requirements.txt
```

You only need to do this once when setting up, or after someone adds a new dependency.

#### `Dockerfile` — Cloud deployment config

This file tells cloud services (like Streamlit Cloud) how to run the app in a container. You won't need to touch this unless you're deploying. Think of it as the recipe for spinning up the app on a server.

#### `MPD_Churn_Model_Explainer.md` — Start here for the model

A plain-English explanation of what the model does, what signals it uses, how the risk score is calculated, and what actions to take. **Read this before using the dashboard.**

#### `MPD_Churn_Knowledge_Base.md` — Deep reference

A more detailed reference document for anyone who wants to understand the model more deeply or contribute to it.

---

## Part 4 — Git: Day-to-Day Basics

You don't need to master Git — but you should understand three scenarios:

### Scenario 1: Getting the latest updates

When a colleague pushes new changes to GitHub, pull them to your machine:
```
git pull
```
Run this at the start of every session to make sure you're working with the latest version.

### Scenario 2: Checking what branch you're on

A **branch** is like a separate copy of the project where changes can be made safely without affecting the main version. Run:
```
git branch
```
The branch with an asterisk (*) next to it is your current branch. The production-safe version is always `main`.

### Scenario 3: Seeing what changed recently

```
git log --oneline -10
```
This shows the last 10 commits (saves) — who made them and what they said about each change.

---

## Part 5 — Running the Dashboard Locally

Once you've cloned the repo and installed Python, do this once to set up:

```bash
# Install all required packages
pip install -r requirements.txt
```

Then every time you want to open the dashboard:

```bash
# Run the app
streamlit run dashboard.py
```

Your browser will open automatically to `http://localhost:8501`. The dashboard reads from `outputs/` — if those files are present, you'll see live data.

To stop the app, go back to the terminal and press `Ctrl + C`.

---

## Quick Reference Card

| Task | Command |
|---|---|
| Get latest updates | `git pull` |
| Check current branch | `git branch` |
| See recent changes | `git log --oneline -10` |
| Install dependencies | `pip install -r requirements.txt` |
| Run the dashboard | `streamlit run dashboard.py` |
| Stop the dashboard | `Ctrl + C` in terminal |

---

## Where to Go Next

1. Read [MPD_Churn_Model_Explainer.md](../MPD_Churn_Model_Explainer.md) — understand the model before using it
2. Open `outputs/patient_risk_scores.csv` in VS Code to see raw model output
3. Run the dashboard and explore the patient list
4. Ask questions — this codebase is meant to be understood, not just used
