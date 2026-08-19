# Getting Started

## Prerequisites

- **Python 3.11+** (3.12 or 3.13 recommended)
- **LLM API key** — one of: OpenAI, Azure OpenAI, or Anthropic
- **Git**
- **Optional**: `arm-none-eabi-gcc` for compilation validation (STM32 plugin)
- **Optional**: `cppcheck` for static analysis (`winget install Cppcheck.Cppcheck`)
- **Optional**: `pyocd` for firmware flashing (`uv pip install pyocd`)
- **Optional**: Docker for containerized deployment

## Installation

### Option A: Local Install

```bash
# Clone
git clone https://github.com/EchoSNS/embedforge.git
cd embedforge

# Option 1: Using uv (recommended)
uv sync

# Option 2: Using pip
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .

# Optional: RAG support
uv pip install -e ".[rag]"

# Optional: Firmware flashing
uv pip install -e ".[flash]"

# Optional: Development tools
uv pip install -e ".[dev]"
```

### Option B: Docker

```bash
docker build -t embedforge .
docker run -p 8000:8000 --env-file .env embedforge
```

## Configuration

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Edit `.env` with your LLM credentials:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
```

3. (Optional) Set your SDK path for compilation:

```env
STM32CUBE_F4_PATH=C:/STM32CubeF4
```

> **Note:** `STM32CUBE_F4_PATH` should point to the **root** of the cloned STM32CubeF4 repo, not a subdirectory. The system automatically appends the correct HAL and CMSIS include paths.

4. (Optional) Set log level for debugging:

```env
LOG_LEVEL=DEBUG
```

5. (Optional) Cost control and model routing:

```env
# Set a spending budget (USD)
EMBEDFORGE_BUDGET_USD=5.00

# Route specific stages to cheaper models (JSON)
EMBEDFORGE_STAGE_MODELS={"refiner": "gpt-4o-mini", "chat": "gpt-4o-mini"}

# Override pricing for custom deployments (JSON, per 1M tokens)
EMBEDFORGE_COST_OVERRIDES={"my-model": {"input": 2.0, "output": 8.0}}

# LLM response cache size (default: 100)
EMBEDFORGE_CACHE_SIZE=100

# Restrict SDK scan to specific directories (security)
EMBEDFORGE_SDK_ROOTS=C:/STM32CubeF4;D:/SDKs
```

See `.env.example` for all available options.

## Running

```bash
# Backend
uv run uvicorn server.main:app --reload
# Or: python app.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Your First Code Generation

1. **Select board** — Choose "NUCLEO-F446RE" from the sidebar
2. **Describe requirement** — Example: "LED blink on PA5 at 2Hz using TIM2 interrupt"
3. **Review requirements** — The AI refines your input into structured JSON. Edit if needed, then approve.
4. **Review hardware** — Pin and peripheral assignments. Approve.
5. **Review architecture** — Selected HAL drivers. Approve.
6. **Review detailed design** — Function-level specification. Approve.
7. **Get code** — Download the generated .c/.h files.

## Expected Output

For a simple LED blink, you'll get:
- `main.c` — Initialization and main loop
- `main.h` — Header with function declarations
- `stm32f4xx_it.c` — Interrupt handlers (TIM2 ISR)
- `stm32f4xx_hal_msp.c` — Clock enable and GPIO config
- `test_led_blink.c` — Unity test file (TDD)
- `mock_hal_tim.h` / `mock_hal_tim.c` — Mock stubs for testing

## Using Your Own SDK

To use a different vendor SDK (not STM32), create a plugin:

1. Create `plugins/your_sdk/`
2. Implement the 5 interfaces (see [Plugin Development](PLUGIN_DEVELOPMENT.md))
3. Set `EMBEDFORGE_PLUGIN=your_sdk` in `.env`
4. Restart the app

## SDK Scanner (Auto-Generate Plugin Data)

Instead of manually writing plugin code, you can use the SDK Scanner to auto-generate capability profiles:

1. Navigate to **Settings** (gear icon in sidebar)
2. Enter the path to your SDK headers (e.g. `C:/STM32CubeF4/Drivers/STM32F4xx_HAL_Driver/Inc`)
3. Click **Scan** — the system extracts all functions, types, and macros
4. Enter vendor/SDK name, then click **Generate Profile**
5. The LLM analyzes the extracted metadata and creates a structured profile
6. Review and edit the generated profile in the Profile Editor tab

You can also upload reference `.c/.h` projects in the Reference Analyzer tab to improve code generation quality.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "LLM not configured" | Check `.env` has valid API key and correct `LLM_PROVIDER` |
| "No active plugin" | Set `EMBEDFORGE_PLUGIN=stm32_hal` in `.env` |
| "No module named dotenv" | Run `uv pip install python-dotenv` or `uv sync` |
| Compilation fails | Install `arm-none-eabi-gcc` and set `STM32CUBE_F4_PATH` |
| cppcheck not detected | Install cppcheck and add to PATH |
| pyOCD not detected | Run `uv pip install pyocd` or `uv pip install -e ".[flash]"` |
| Import errors | Run `uv sync` from project root |
| Slow generation | Use `gpt-4o` instead of `gpt-4` for faster (cheaper) results |
| `uv add` fails | Ensure `[tool.hatch.build.targets.wheel]` exists in pyproject.toml |
