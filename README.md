# 🧪 A/B Test Analyzer

> A rigorous statistical tool for analyzing A/B test results. Frequentist + Bayesian inference, power analysis, and sample-size calculation — all in a live, deployed web app.

### 🔗 [**Live Demo →**](https://prakruti-ab-test-analyzer.streamlit.app/)

![Hero](images/hero.png)

---

🎯 The Problem It Solves

When two websites report the same story, such as a gold price, a budget figure, or a match score, their numbers don't always match. Checking by hand means reading both pages line by line.

Story Checker does the comparison for you and answers:

Which figures do both sources agree on?
Where do they genuinely disagree, and which exact sentences should I verify?
Is a difference important, or just rounding or a timing gap between updates?

What it does not do: it does not decide which source is true. It finds disagreements so a person can verify the specific claims that matter.

✨ Features
🔗 Paste two links: the app downloads each page and extracts the article text (or paste the text directly if a site blocks automated readers)
🔍 Claim matching: pairs up sentences from the two sources that talk about the same thing
🔴 Real conflicts: flags numbers that genuinely differ, shown side by side
🟡 Minor differences: gaps under 0.1% are labelled as likely rounding or update timing, not alarms
✅ Agreement list: every figure both sources share
📌 Optional reference check: add an official text (press release, court order) and see which source is closer to it
📄 Transparency: shows exactly what text was read from each page
🧹 Clutter filtering: drops footers, copyright lines, and repeated paragraphs before comparing
📸 Example

Comparing two live gold-rate pages for Ahmedabad:

Result	Value
Figures both sources agree on	8 (24K and 22K prices, purity levels)
Real conflicts	0
Minor rounding differences	1 (18K price: ₹10,800 vs ₹10,801, a gap of about 0.01%)

Verdict: "All main figures match. Only 1 tiny difference, most likely rounding or the sites updating at different times."

⚙️ How It Works
Fetch: download each page and keep only article paragraphs (script, footer, and navigation content is dropped).
Split: break the text into sentences.
Match: pair each sentence with the most similar sentence in the other source, using shared content words.
Extract: pull out numbers (normalising formats like ₹14,400.00 and ₹14,400, and units like 12 percent and 12%).
Compare: if both sentences contain numbers and neither set contains the other, it's a conflict.
Classify: if the numbers differ by 0.1% or less, it's a minor difference. Anything larger is a real conflict.

It is rule-based Python with no AI model involved, so results are deterministic and easy to explain.

⚠️ Limitations
It compares numbers. Differences that are only in wording are not detected.
Sentence matching uses shared words, so on pages that list many similar items it can occasionally pair the wrong lines.
Some sites block automated readers. The paste-text option is the fallback.
"Closer to the reference" is only as reliable as the reference the user provides.
Years and dates are ignored when counting agreed figures.
🛠️ Tech Stack
Python (standard library re, html.parser, dataclasses)
Streamlit for the web app
requests for downloading pages
pytest for unit tests
📁 Project Structure
ab-test-analyzer/
├── app/
│   └── streamlit_app.py        # Story Checker web app
├── src/
│   ├── story_compare.py        # Comparison engine (used by the app)
│   ├── frequentist.py          # z-test and Welch's t-test
│   ├── bayesian.py             # Beta-Binomial inference
│   ├── power.py                # Power and sample-size analysis
│   └── data_loader.py
├── tests/                      # pytest unit tests
├── notebooks/
├── conftest.py
└── requirements.txt

The project began as an A/B test statistics toolkit. Those modules (frequentist.py, bayesian.py, power.py) are still in src/ with their tests, but the live app is the Story Checker.

🚀 Run Locally
bash
git clone https://github.com/Prakruti25/ab-test-analyzer.git
cd ab-test-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
streamlit run app/streamlit_app.py
🔮 Future Enhancements
Smarter claim matching with a language model, to catch differences in wording as well as numbers
Support for dates, units, and currencies
Better extraction of main article content from complex pages
Highlight the differing figures inside the sentences
Compare more than two sources at once
Re-attach the A/B testing statistics (z-test and Bayesian inference) to compare which of two headlines readers prefer
📄 License

See LICENSE.

## 👩‍💻 Author

**Prakruti Patel** — B.S. Computer Science (AI specialization), Indiana University Bloomington · Class of 2026

[LinkedIn](https://www.linkedin.com/in/prakruti-patel-/) · [GitHub](https://github.com/Prakruti25)

---

⭐ If this project helped you or you found it interesting, drop a star!
