# Adaptive GenAI Learning Tutor — Frontend Examples

A visually rich, dark-themed React frontend for the **Adaptive GenAI Learning Tutor** project. Built with **Vite + React + Tailwind CSS** and designed to be fully compatible with a modern Vite React stack.

---

## 🎨 Design System

- **Dark theme** with deep purple / cyan accents (`#8b5cf6` → `#06b6d4`)
- **Glassmorphism** cards with `backdrop-filter` blur and semi-transparent borders
- **Gradient text & borders** for emphasis and visual hierarchy
- **Smooth animations** — fade-in, slide-in, scale-in, staggered children, pulse glows
- **Skill mastery color coding** — red (exposure) → amber (developing) → emerald (proficient) → cyan (mastered) → purple (review)
- **Source reference chips** — every recommendation and exercise shows corpus grounding

---

## 📁 Project Structure

```
frontend-examples/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.jsx              # React entry point
    ├── App.jsx               # App shell with sidebar + routing
    ├── styles/
    │   └── index.css         # Global styles, CSS variables, animations
    ├── components/
    │   ├── Sidebar.jsx         # Navigation sidebar
    │   ├── ProgressRing.jsx    # Circular progress indicator
    │   ├── SkillMasteryBar.jsx # Horizontal skill bar with state
    │   ├── SkillStateBadge.jsx # Compact status badge
    │   └── SourceRef.jsx       # Corpus citation chips
    └── pages/
        ├── Dashboard.jsx       # Learner overview & stats
        ├── Diagnostic.jsx      # Multi-turn adaptive interview UI
        ├── StudyPlan.jsx       # Visual learning roadmap
        ├── Exercise.jsx        # Practice with grading feedback
        ├── Progress.jsx        # Analytics & skill radar
        └── CorpusBrowser.jsx   # Course catalog search
```

---

## 🚀 Quick Start

### 1. Copy into a new Vite project

```bash
# Create a new Vite React project
cd /Users/dgomez/Week\ 3\ Project
npm create vite@latest tutor-ui -- --template react

# Copy the frontend files
cp -r /Users/dgomez/Documents/kimi/workspace/frontend-examples/* tutor-ui/
cd tutor-ui
```

### 2. Install dependencies

```bash
npm install
```

### 3. Run the dev server

```bash
npm run dev
```

The app opens at `http://localhost:5173`.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `react` / `react-dom` | UI framework |
| `recharts` | Radar chart & line chart for progress analytics |
| `tailwindcss` | Utility-first CSS |
| `vite` | Build tool & dev server |

---

## 🖥️ Screens Included

### 1. Dashboard (`/dashboard`)
- Overall progress ring, stats cards, skill mastery grid
- Recent activity feed, recommended next actions
- Source reference footer showing corpus grounding

### 2. Diagnostic (`/diagnostic`)
- Chat-style multi-turn interview UI
- Animated typing indicator for the tutor
- Multiple-choice options with selection states
- **Interrupt flow** — clarifying question mid-diagnostic
- Final proficiency profile result card
- Progress bar at top showing question count

### 3. Study Plan (`/study-plan`)
- Visual roadmap with collapsible modules
- Skill dependency graph (text-based flow)
- Prerequisites, course recommendations, progress bars per module
- Goal adjustment buttons (Exam Cram / Deep Mastery / Custom)
- Spaced repetition indicators

### 4. Exercise (`/exercise`)
- **Architecture scenario** exercise format (open-ended)
- Hints accordion (expandable tips without spoiling)
- Solution accordion (reference answer + explanation)
- Textarea for learner answer with character count
- **Grading feedback panel** — score, feedback, misconception tags, detailed explanation
- Source reference chips for corpus grounding
- Next action buttons (Retry, Next Exercise)

### 5. Progress (`/progress`)
- **Radar chart** — skill proficiency across all 8 GenAI topics
- **Line chart** — weekly exercise count & average score
- Spaced repetition schedule (what's due and when)
- Recent mastery transitions (exposure → developing → proficient)
- Progress rings for overall stats

### 6. Corpus Browser (`/corpus`)
- Search bar with instant filtering
- Topic filter pills (LLMs, RAG, Agents, MCP, etc.)
- Course/topic result cards with descriptions, platform, instructor
- Corpus metadata snapshot (67 courses, 17 topics, 72 instructors, 81 sources)
- Source citation links

---

## 🔌 Integration with Backend

These components are **presentation-ready** with mock data. To wire them to your actual backend:

1. **Replace mock data** in each page with API calls to your orchestrator / MCP server.
2. **Add React Router** (`react-router-dom`) and replace the `activePage` state with real routes.
3. **Connect WebSocket or SSE** for real-time diagnostic chat updates.
4. **Swap `recharts`** data props with live analytics from the learner store.

### Key data contracts (from the PRD):

- `LearnerProfile` — skills array with `status`, `proficiency`, `confidence`
- `Exercise` — `question`, `format`, `hints`, `rubric`, `solution`, `source_refs`
- `GradingResult` — `score`, `feedback`, `explanation`, `misconception_tags`, `next_action`
- `StudyPlan` — ordered modules with `prerequisites`, `courses`, `milestones`

---

## 🛠️ Customization

- Edit `src/styles/index.css` to change the color palette, animation speeds, or glassmorphism intensity.
- Modify `tailwind.config.js` to extend the theme with custom colors or breakpoints.
- Add `react-router-dom` in `App.jsx` for real URL-based navigation.

---

## 📄 License

Part of the Week 3 Project — Adaptive GenAI Learning Tutor.
