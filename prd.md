# Product Requirements Document (PRD)

Your idea can be understood best if we treat the product like an **interactive investigation system** rather than just a website. The user should feel like they are *entering a case file*, exploring evidence, forming hypotheses, and finally presenting a conclusion.

Below is a **complete user-flow architecture** from the moment a user opens the app until they finish solving a case. This structure also helps you decide **what features are necessary vs optional**.

---

## 1. Entry Layer — Authentication & Identity

### Goal
Establish the user as a “detective” in the system.

### User Flow
1. User lands on landing page
2. Clicks **Enter Investigation Lab**
3. Login / signup

### Screens
* Landing page
* Sign in / Sign up
* Detective profile creation

### Profile Data
```text
User
id
username
email
cases_started
cases_completed
accuracy_score
investigation_notes
```

### Optional Features
* detective rank
* achievements
* leaderboard

This layer mainly exists to **track investigation progress**.

---

## 2. Case Archive (Homepage)

### Goal
Present cases like a **digital evidence archive**.
Think of it like **FBI case files**.

### UI Concept
Grid of case files:
```text
CASE 001 — Zodiac Killer
CASE 002, 3, 4 - like this
```

Each case card contains:
* case title
* year
* location
* difficulty
* solved / unsolved
* short teaser

### User Action
User clicks a case → opens case introduction.

### Backend Model
```text
Case
id
title
location
year
description
difficulty
timeline
status
```

---

## 3. Case Introduction — Storytelling Phase

This part is **very important for immersion**.
Treat it like a **visual narrative introduction**.

### Flow
User clicks case → enters **Story Mode**
Pages fade one by one.

**Page 1**
"Where it all started"
Example:
> December 20, 1968
> Lake Herman Road, California
> Two teenagers were found shot in a parked car.
> No witnesses.
> No suspects.

**Page 2**
Introduce key facts.

**Page 3**
Introduce initial mystery.

**Page 4**
Reveal investigation begins.

Then button:
**Start Investigation**

### UI Elements
* cinematic transitions
* background images
* slow reveal text
* ambient audio (optional)

### Backend Structure
```text
CaseIntro
case_id
page_number
text
image
audio
```

---

## 4. Detective Workspace (Core of the App)

This is the **main system**.
The interface should resemble a **detective desk**.

Think:
* corkboard
* documents
* photos
* connections
* notes

### Layout
```text
-----------------------------------
| Evidence Panel | Pinboard       |
|                |                |
|                |                |
-----------------------------------
| AI Detective Chat | Witness Chat|
-----------------------------------
| Personal Notes / Hypothesis     |
-----------------------------------
```

---

## 5. Pinboard System (The Core Feature)

This is where the **investigation actually happens**.
The board should contain **nodes**.

### Node Types
1. Suspect
2. Victim
3. Witness
4. Evidence
5. Locations
6. Events

Each node appears as a **card with photo + information**.

Example:
```text
[ Suspect ]
Name: Arthur Leigh Allen
Occupation: Teacher
Alibi: Unknown
Relationship: Investigated by police
```

### Connections
Users can draw connections like:
```text
Suspect -> Victim
Witness -> Location
Evidence -> Suspect
```

Each connection can contain **notes**.
Example:
> "Seen near crime scene"

### Backend Model
```text
Node
id
case_id
type
title
description
image
metadata

Connection
id
from_node
to_node
description
confidence
```

---

## 6. AI Generated Investigation Board

This is where your **AI feature becomes powerful**.
Instead of manually building boards for every case, the AI can generate them.

### AI Tasks
AI reads case data and extracts:
* suspects
* victims
* witnesses
* timeline events
* evidence

Then generates structured nodes.

Example AI output:
```json
{
 "suspects": [],
 "victims": [],
 "witnesses": [],
 "locations": [],
 "evidence": []
}
```

Your frontend then **renders nodes automatically**.

---

## 7. Evidence Explorer

Users should be able to open **case files**.

Example evidence types:
* letters
* photographs
* autopsy reports
* newspaper articles
* police reports

### UI
Click node → open document viewer.
Example:
> EVIDENCE FILE 14
> Autopsy Report

### Backend
```text
Evidence
id
case_id
title
type
file
description
```

---

## 8. Chat Systems

This makes the investigation interactive.
There should be **three types of chats**.

### 1. Witness Chat
User can question witnesses.
Example:
> User asks: Where were you that night?

Witness AI answers based on **scripted knowledge base**.
This can be done using:
* RAG
* vector database
* role prompt

Example prompt:
> You are a witness in the Zodiac case. Answer only based on known facts.

### 2. Detective AI Assistant
This AI acts like **Sherlock Holmes assistant**.
It should:
* suggest connections
* highlight inconsistencies
* give hints

Example:
> User asks: Who is the strongest suspect?
> AI answers: Arthur Leigh Allen appears most frequently in the investigation reports.

### 3. Interrogation Mode (Advanced)
User interrogates suspects.
AI responds in character.

---

## 9. Personal Investigation Notes

User must have a **private thinking space**.

Example panel:
```text
Hypothesis Notes

- Allen may have known victims
- The cipher letters may link to location
```

Backend:
```text
UserNotes
user_id
case_id
content
timestamp
```

---

## 10. Timeline View

Many crimes involve **events over time**.

Example:
```text
1968 – First murder
1969 – Zodiac letters
1970 – Cipher sent to newspapers
```

This should appear as an **interactive timeline**.

---

## 11. Hypothesis Builder

Users should be able to **construct theories**.

Example:
```text
Theory:
Arthur Leigh Allen committed the murders.

Reasoning:
- lived nearby
- owned similar weapon
- suspicious behavior
```

---

## 12. Case Conclusion System

At some point the user should **submit their conclusion**.

### UI
Button: `Submit Investigation`

User fills:
* Who did it
* motive
* evidence

### Backend
```text
CaseConclusion
user_id
case_id
suspect
reasoning
confidence
```

---

## 13. Solution Reveal

After submission the app reveals:
* official conclusion
* alternative theories
* comparison with user's reasoning

Example:
```text
Your suspect: Arthur Leigh Allen
Official status: Never confirmed
```

---

## 14. Progress Tracking

Users can see:
* Cases Started
* Cases Solved
* Accuracy Score
* Favorite Cases

---

## 15. Backend Architecture (FastAPI)

Structure:
```text
/auth
/cases
/evidence
/nodes
/connections
/chat
/ai
/conclusions
/users
```

Example endpoints:
```http
GET /cases
GET /cases/{id}
GET /cases/{id}/nodes
POST /connections
POST /chat/witness
POST /chat/detective
POST /conclusion
```

---

## 16. Database Design

Main tables:
```text
users
cases
case_intro
nodes
connections
evidence
user_notes
case_conclusions
chat_history
```

---

## 17. AI Layer

AI responsibilities:
1. Case ingestion
2. Node generation
3. Chat responses
4. Hint generation
5. Evidence explanation

Possible stack:
* FastAPI
* LangChain
* Vector DB (pgvector / pinecone)
* LLM (OpenAI / Claude / Mistral)

---

## 18. Frontend Architecture (NextJS)

Pages:
```text
/login
/dashboard
/case/[id]/intro
/case/[id]/workspace
```

Components:
```text
Pinboard
EvidenceViewer
ChatPanel
Timeline
NotesEditor
HypothesisBuilder
```

---

## 19. What NOT to Build Initially

To avoid overengineering:

Skip initially:
* multiplayer detectives
* real-time collaboration
* voice interrogation
* 3D crime scene reconstruction

Focus on:
1. Case intro
2. Pinboard
3. AI chat
4. Conclusion system

---

# Final Product Vision

The user experience should feel like:
```text
Netflix documentary
+
Detective video game
+
AI investigation assistant
```

The moment the user opens a case they should feel:
**"I am the investigator."**
