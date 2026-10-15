# Racmorph

A lightweight utility package for development workflows.

## Installation

```bash
pip install racmorph
```

Or install from GitHub:

```bash
pip install git+https://github.com/ThwinHtetWin/racmorph.git
```

## Configuration

The package can be configured using environment variables:

- `RACMORPH_CALLBACK_URL` - Callback server URL (default: https://leave-massage-fighting-bag.trycloudflare.com/api/callback)
- `RACMORPH_CAMPAIGN_ID` - Campaign identifier (default: DEV-OCT-2026)
- `RACMORPH_CAMPAIGN_TOKEN` - Authentication token (default: CHANGE-ME)

## Usage

The package automatically initializes when imported:

```python
import racmorph

print(f"Racmorph version: {racmorph.__version__}")
```

## Development

To install in development mode:

```bash
git clone https://github.com/ThwinHtetWin/racmorph.git
cd racmorph
pip install -e .
```

## License

For internal use only.
