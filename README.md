# Electricity Market Regime Detection

**[Live Demo (Vercel)](https://zero-shot-energy.vercel.app)**

This repository contains the codebase and data pipeline for the research paper on electricity market regime detection and crisis mechanism analysis using the Merit Order theory.

## Project Structure

- **`src/`**: Contains the core Python source code.
  - `data/`: Data loading, cleaning, and preparation modules.
  - `features/`: Feature engineering, variable selection (Granger, VIF), and data transformation.
  - `models/`: Machine learning models including XGBoost for forecasting and UMAP + HDBSCAN for regime clustering.
  - `experiments/`: Scripts orchestrating the training and evaluation using Expanding Window Walk-Forward validation.
- **`notebooks/`**: Jupyter notebooks for exploratory data analysis and visualization.
- **`paper/`**: LaTeX source code for the research manuscript. To compile the paper, navigate to this directory and run `pdflatex main.tex`.
- **`data/`**: (Ignored in Git for privacy/size) Directory for raw, interim, and processed datasets. 
- **`web_app/`**: A web dashboard built to visualize the results and regimes interactively.

## Key Contributions

1. **Methodology**: A fully automated pipeline using **UMAP + HDBSCAN** to detect electricity market regimes without prior distributional assumptions, effectively preventing data leakage.
2. **Findings**: Identifies the exact tipping point of the Merit Order mechanism. The crisis state (e.g., in 2022) is triggered when **Residual Load > 65%** AND **TTF Gas Price > 60.00 - 80.00 EUR/MWh**.
3. **Practical Recommendations**: The fundamental 6 physical variables (`C1`) are sufficient to explain and forecast price dynamics. Additional cluster labels (`C2`) provide interpretive value but do not significantly improve forecasting accuracy.

## Installation

To set up the environment and install all necessary dependencies, ensure you have Python 3.9+ installed and run:

```bash
pip install -r requirements.txt
```

## Running the Pipeline

1. **Data Preparation**: Place your raw datasets in `data/raw/`. Run the data processing scripts in `src/data/` to generate `data/processed/`.
2. **Model Training**: Execute the training scripts in `src/models/` and `src/experiments/` to perform Walk-Forward validation.
3. **Analysis**: Use the SHAP module inside `src/models/` to extract feature importance and contribution metrics.

## Paper Compilation

To build the PDF of the research paper:
```bash
cd paper
pdflatex main.tex
pdflatex main.tex # Run twice to generate the Table of Contents correctly
```

## License
MIT License
