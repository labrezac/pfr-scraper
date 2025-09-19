# pfr-scraper

Playground for webscraping Pro-Football-Reference.

## Project layout

```
├── configs/              # Configuration files shared across scrapers and pipelines
├── data/                 # Local data lake (raw + processed datasets)
│   ├── processed/
│   └── raw/
├── logs/                 # Runtime logs emitted by scraper jobs
├── notebooks/            # Exploratory analysis and spike notebooks
├── scripts/              # Command-line entry points for running scrapers/pipelines
├── src/pfr_scraper/
│   ├── http/             # HTTP utilities that wrap the header emulator
│   ├── pipelines/        # Data processing pipelines fed by scraper outputs
│   └── scrapers/         # Concrete scraper implementations
└── tests/                # Automated tests
```

## Next steps

- Wire the header emulator package into `pfr_scraper.http.build_session` once it is published/available locally.
- Add concrete scraper implementations under `src/pfr_scraper/scrapers/`.
- Extend the test suite to cover scraper and pipeline behaviour.
