# ProjectManorama — Malayalam News Ticker Generation & Editorial Review

ProjectManorama is a web application that converts Malayalam news announcements and press releases into concise, broadcast-style news tickers.

The application allows editors to generate, review, edit, reorder, approve and export news tickers.

Each ticker must contain **no more than 10 words** and remain faithful to the original announcement.

## Features

- **Malayalam News Processing:** Accepts Malayalam news announcements and generates Malayalam tickers.
- **Single and Batch Input:** Supports individual announcements and multiple announcements in one session.
- **Offline Generation:** Uses a rule-based Python generator without external AI services.
- **10-Word Limit:** Enforces a maximum of 10 whitespace-separated words per ticker.
- **Source Verification:** Displays each ticker alongside its original announcement.
- **Editorial Review:** Allows editors to modify generated tickers before approval.
- **Reordering:** Supports arranging tickers in the desired broadcast order.
- **Alternative Tickers:** Provides alternative source-based ticker suggestions when available.
- **Regeneration:** Allows editors to request another available ticker.
- **Fact-Checking Warnings:** Checks for unsupported numbers, missing qualifications and wording differences.
- **Approval Workflow:** Editors can approve tickers after reviewing them.
- **JSON Export:** Exports approved tickers in a structured, machine-readable format.
- **Live News Ticker:** Displays approved news tickers in a scrolling broadcast-style interface.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Ticker Generation | Rule-based Malayalam text processing |
| Validation | Python-based checks |
| Export | JSON |
| Authentication | Not required |
| External API | Not required |

The application does not require an API key, external AI model or internet connection during normal local operation.

## Installation and Execution

### 1. Clone the Repository

```bash
git clone https://github.com/Sharoneb28/ProjectManorama.git
cd ProjectManorama
```

### 2. Install Dependencies

Ensure Python is installed.

```bash
pip install -r requirements.txt
```

### 3. Start the Application

```bash
python app.py
```

Open the application in your browser:

`http://localhost:5000`

## How to Use

### Step 1: Enter News Announcements

Users can enter a Malayalam announcement directly or import multiple announcements.

The application also provides sample announcements for testing.

### Step 2: Generate News Tickers

Click **Generate Tickers**.

The application processes the announcements and attempts to generate a short Malayalam ticker for each.

Each ticker is limited to 10 words.

### Step 3: Review the Results

The editor can:

1. Read the generated ticker.
2. Compare it with the original announcement.
3. Check the word count and validation warnings.
4. Edit the ticker if necessary.
5. Select an alternative ticker when available.
6. Regenerate the ticker.
7. Change the ticker order.

### Step 4: Approve Tickers

After reviewing the generated content, the editor can mark suitable tickers as approved.

The editor remains responsible for confirming factual accuracy.

### Step 5: Export Approved Tickers

Click **Export Approved** to download the approved tickers in JSON format.

The exported data includes ticker text, position, source announcement and word count.

## Malayalam Ticker Generation

The generator is implemented in `ticker_service.py`.

It follows a conservative, source-based approach.

### 1. Text Preprocessing

The input announcement is normalized using Unicode NFC normalization.

The application separates the announcement into sentences while attempting to preserve Malayalam initials and abbreviations.

### 2. Sentence Selection

Sentences are scored using indicators such as:

- News-related Malayalam keywords
- Important developments
- Numerical information
- Denials and uncertainty
- Sentence position

The generator attempts to identify newsworthy content rather than selecting sentences solely by length.

### 3. Ticker Extraction

The generator prefers complete sentences containing 10 words or fewer.

For longer sentences, it attempts to extract suitable shorter clauses.

It avoids arbitrary truncation when this could remove important context.

If no suitable short excerpt is available, the generator may request manual editorial review.

### 4. Fact Validation

The `check()` function performs automated checks.

| Validation | Purpose |
|---|---|
| Word count | Ensures the ticker does not exceed 10 words |
| Malayalam detection | Checks whether Malayalam characters are present |
| Number verification | Detects numbers absent from the source |
| Source matching | Flags wording that is not an exact source excerpt |
| Denial detection | Warns when a relevant denial may be missing |
| Uncertainty detection | Warns when relevant qualifications may be missing |

**Important:** These checks cannot guarantee semantic correctness. Human editorial review is required.

## Example

### Input Announcement

കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു.

### Generated Ticker

കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു

**Word Count:** 6/10

### Example With Denial

**Input:**

പോലീസ് മൂന്ന് പേരെ അറസ്റ്റ് ചെയ്തെന്ന റിപ്പോർട്ടുകൾ നിഷേധിച്ചു.

**Generated Ticker:**

പോലീസ് മൂന്ന് പേരെ അറസ്റ്റ് ചെയ്തെന്ന റിപ്പോർട്ടുകൾ നിഷേധിച്ചു

**Word Count:** 7/10

The ticker preserves the denial rather than incorrectly reporting an arrest as a confirmed event.

## Sample News Announcements

The project includes Malayalam sample announcements covering:

- Cheranalloor accident
- Andhra–Odisha rain warnings
- Government announcements
- Police denials
- Dengue cases
- School holidays
- Infrastructure development
- Company announcements
- Weather forecasts
- Road accidents

These samples help evaluate ticker generation, factual preservation and word-count enforcement.

## Testing

To run the automated tests:

```bash
python -m unittest discover -s tests -v
```

Some tests may need updating if they were originally written for the English-language generator.

The application should also be tested manually using long Malayalam announcements, particularly those containing allegations, uncertainty, abbreviations and multiple newsworthy developments.

## JSON Export Format

Example:

```json
{
  "schema_version": "1.0",
  "exported_at": "2026-10-28T06:25:08.480Z",
  "max_words": 10,
  "count": 1,
  "tickers": [
    {
      "position": 1,
      "id": "a1",
      "ticker": "കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു",
      "word_count": 6,
      "edited": false,
      "generated_ticker": "കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു",
      "source_text": "കേരള സർക്കാർ പുതിയ വിദ്യാഭ്യാസ പദ്ധതി പ്രഖ്യാപിച്ചു.",
      "flags": []
    }
  ]
}
```

## Project Structure

```text
ProjectManorama/
│
├── app.py
├── ticker_service.py
├── requirements.txt
├── README.md
│
├── static/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── samples.txt
│
├── samples/
│   └── announcements.txt
│
└── tests/
    └── test_ticker_service.py
```

## Limitations

The application uses rule-based processing rather than a trained Malayalam language model.

Consequently:

- It may not always identify the most important development in a long article.
- It may generate a grammatically incomplete or less informative ticker.
- It cannot reliably understand every Malayalam sentence.
- It may flag valid editorial paraphrases for review.
- It cannot independently verify the truth of the original announcement.
- Some complex announcements require manual editing.

The system therefore uses a **human-in-the-loop editorial workflow**, where generated tickers are reviewed before approval.

## Conclusion

ProjectManorama demonstrates an offline Malayalam news ticker generation and editorial review workflow.

It combines source-based text extraction, basic factual validation, editorial controls and structured JSON export to support broadcast news preparation.

The project prioritizes factual faithfulness, transparency and human editorial oversight.

---

**Project:** ProjectManorama  
**Category:** Malayalam News Ticker Generation and Editorial Review  
**Technology:** Python, Flask, HTML, CSS, JavaScript
