# Getting Started

## Prerequisites

- **Python 3.11+** (3.12 or 3.13 recommended)
- **LLM API key** — one of: OpenAI, Azure OpenAI, or Anthropic
- **Git**
- **Optional**: `arm-none-eabi-gcc` for compilation validation (STM32 plugin)
- **Optional**: Docker for containerized deployment

## Installation

### Option A: Local Install

```bash
# Clone
git clone https://github.com/EchoSNS/embedforge.git
cd embedforge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\Activate.ps1  # Windows PowerShell

# Install
pip install -e .

# Optional: RAG support
pip install -e ".[rag]"

# Optional: Development tools
pip install -e ".[dev]"
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

## Running

```bash
# Backend
uvicorn server.main:app --reload

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "LLM not configured" | Check `.env` has valid API key |
| "No active plugin" | Set `EMBEDFORGE_PLUGIN=stm32_hal` in `.env` |
| Compilation fails | Install `arm-none-eabi-gcc` and set `STM32CUBE_F4_PATH` |
| Import errors | Run `pip install -e .` from project root |
| Slow generation | Use `gpt-4o` instead of `gpt-4` for faster (cheaper) results |
