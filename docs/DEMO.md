# AniGenerator Showcase & Demo

AniGenerator transforms dense, static documents into engaging, professional whiteboard animations completely autonomously. 

Below is a demonstration of the end-to-end pipeline, showcasing how the system processes raw text into a final rendered video.

---

## 1. The Input
**Source Material:** Users provide raw text or upload a document (`.pdf`, `.txt`, `.docx`). 

For this demo, we use the provided `sample_input.txt` found in the repository root:

```text
1.1. What is Bitcoin?
Bitcoin is a digital cash system. It allows for people to move bitcoins, the currency unit of Bitcoin, between each other without using a bank or any other trusted third party. It resembles traditional bank notes and coins, but it’s purely digital...
```

---

## 2. Pipeline Execution
Once the input is submitted, the FastAPI backend orchestrates a multi-stage autonomous pipeline:

### A. Semantic Analysis & Storyboarding (Gemini LLM)
The system analyzes the document's semantics and structures it into discrete scenes. It generates pedagogical narration and identifies the optimal visual metaphor for each segment.

### B. Asset Retrieval (`icon_fetcher.py`)
To ensure visual consistency and a premium aesthetic, the system bypasses unpredictable AI image generation. Instead, it programmatically fetches clean, high-quality vector assets mapped to the LLM's visual metaphors.

### C. Audio Synthesis & Choreography
The generated narration is converted to high-fidelity speech (TTS). The system calculates exact millisecond timings (`draw_start_ms`, `draw_duration_ms`, `hold_ms`) to perfectly synchronize the whiteboard drawing animation with the spoken audio.

---

## 3. The Render Engine
The animation is built using React and rendered via **Remotion** in a headless Chromium environment.

*   **Premium Physics:** Instead of simple linear paths, our `SvgDrawer` utilizes staggered, spring-based physics. This gives the whiteboard strokes and fills a fluid, organic, and highly professional feel.
*   **Continuous Canvas:** Scene transitions utilize smooth pan-and-scale canvas movements to simulate an expansive, real-world whiteboard.
*   **Parallel Processing:** To achieve sub-3-minute generation times, scenes are chunked and rendered in parallel across isolated browser instances, then seamlessly stitched together using FFmpeg.

---

## 4. The Output
The final artifact is a broadcast-ready `.mp4` file. 

*(Note: Add an animated GIF or video link here representing the final Bitcoin demo output)*

`![Demo Animation Output](../assets/demo_placeholder.gif)`

---

## 🚀 Run the Demo Locally

Want to see it in action? You can run this exact pipeline on your local machine:

1. **Start the Backend:**
   ```bash
   APP_ENV=development DATABASE_URL=sqlite:///./anigen.db uvicorn backend.main:app --reload --port 8000
   ```
2. **Start the Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Generate:** Open the local web interface, paste the contents of `sample_input.txt`, and watch the magic happen.
