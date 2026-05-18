# 🧪 A/B Test Analyzer

> A rigorous statistical tool for analyzing A/B test results. Frequentist + Bayesian inference, power analysis, and sample-size calculation — all in a live, deployed web app.

### 🔗 [**Live Demo →**](https://prakruti-ab-test-analyzer.streamlit.app/)

![Hero](images/hero.png)

---

## 🎯 The Problem It Solves

Most "A/B test calculators" online give you a single p-value and a vibes-based conclusion. Real product decisions need more:

- Was the test **powered enough** to detect a real effect, or are we drawing conclusions from noise?
- What's the **probability the variant is actually better** (Bayesian)?
- What's the **expected downside** if we ship the variant and it's actually worse?
- Are we measuring **statistical significance** or **practical significance**?

This tool answers all of those for any A/B test you throw at it — with plain-English interpretation a PM can act on.

## ✨ Features

- 📈 **Two-proportion z-test** with 95% confidence interval on the lift
- 🎲 **Bayesian Beta-Binomial inference** — `P(variant > control)`, credible intervals, expected loss
- ⚡ **Power analysis** — observed power for completed tests, sample-size calculator for planning new ones
- 🟢 **Plain-English verdict** — auto-generated ship/don't-ship recommendation
- 📊 **Interactive posterior visualization** — overlapping density curves so you can *see* the uncertainty
- 🧪 **Unit-tested** — 15 passing tests across the entire stats engine

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)
![scipy](https://img.shields.io/badge/scipy-stats-8CAAE6?style=flat&logo=scipy&logoColor=white)
![statsmodels](https://img.shields.io/badge/statsmodels-0.14-3F4F75?style=flat)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-charts-3F4F75?style=flat&logo=plotly&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-15%20passing-0A9EDC?style=flat&logo=pytest&logoColor=white)


## 🧠 Statistical Methods

### Frequentist
- **Two-proportion z-test** with pooled variance for the test statistic, unpooled for the CI on the difference
- **Welch's t-test** for continuous metrics (unequal-variance safe)

### Bayesian
- **Beta-Binomial conjugate model** with `Beta(1, 1)` (uniform) prior
- **Monte Carlo sampling** (100,000 draws) for `P(variant > control)` and credible intervals
- **Expected loss** metric for risk-aware decision-making

### Power Analysis
- Sample-size formula using pooled and unpooled variances
- Observed power calculation for completed tests

## 🚀 Run Locally

```bash
git clone https://github.com/Prakruti25/ab-test-analyzer.git
cd ab-test-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v          # confirm 15 tests pass
streamlit run app/streamlit_app.py
```

## 🔮 Future Enhancements

- [ ] Sequential testing (mSPRT / AGILE) to allow peeking without inflating false-positive rate
- [ ] Multi-variant test support (A/B/C/D)
- [ ] CUPED variance reduction for continuous metrics
- [ ] Segmentation upload — auto-detect Simpson's Paradox

## 👩‍💻 Author

**Prakruti Patel** — B.S. Computer Science (AI specialization), Indiana University Bloomington · Class of 2026

[LinkedIn](https://www.linkedin.com/in/prakruti-patel-/) · [GitHub](https://github.com/Prakruti25)

---

⭐ If this project helped you or you found it interesting, drop a star!