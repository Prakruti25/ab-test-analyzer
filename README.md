# 🧪 A/B Test Analyzer

> A rigorous statistical tool for analyzing A/B test results. Frequentist + Bayesian inference, power analysis, segmentation, and Simpson's Paradox detection — all in a live web app.

## 🎯 The Problem It Solves

Most "A/B test calculators" online give you a single p-value and a vibes-based conclusion. Real product decisions need more:

- Was the test **powered enough** to detect a real effect, or are we drawing conclusions from noise?
- What's the **probability the variant is actually better** (Bayesian)?
- Does the result hold up when we **segment by user type**, or is Simpson's Paradox hiding the truth?
- Are we measuring **statistical significance** or **practical significance**?

This tool answers all of those questions for any test you throw at it.

## 🛠️ Tech Stack

Python · scipy · statsmodels · Streamlit · Plotly

## 📊 Live App

_Coming soon — building in progress_

## 🚀 Run Locally

```bash
git clone https://github.com/Prakruti25/ab-test-analyzer.git
cd ab-test-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```