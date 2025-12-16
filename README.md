# Spielberg - AI-Powered Actor Generator

**Spielberg** is a meta-actor that generates and deploys custom Apify Actors from natural language descriptions. Simply describe what you want your Actor to do, and Spielberg will create it for you!

Find the actor [here](https://console.apify.com/actors/Yl93bV0rYg5k140at/source)

## 🎬 Features

- **Natural Language Input**: Describe your Actor in plain English
- **Intelligent Code Generation**: Uses GPT-4 to create production-ready Actor code
- **Automatic Deployment**: Deploys directly to your Apify account
- **Iterative Error Fixing**: Automatically fixes build errors (up to 3 attempts)
- **Complete Actor Files**: Generates all necessary files (main.py, actor.json, input_schema.json, etc.)

## 🚀 Quick Start

### Prerequisites

1. An Apify account
2. An OpenAI API key (with GPT-4 access)

### Setup

1. **Set up OpenAI API Key**:
   - Go to Actor Settings → Environment Variables
   - Add a new secret: `OPENAI_API_KEY` with your OpenAI API key
   - Get your API key from: https://platform.openai.com/api-keys

2. **Run Spielberg**:
   - Provide a description of your desired Actor in the input field
   - Click "Start"
   - Wait for Spielberg to generate and deploy your Actor

### Example Prompts

**Simple Hello World:**
```
Create an Actor that logs 'Hello World' and saves it to a dataset
```

**Data Processing:**
```
Create an Actor that takes a list of URLs as input and counts how many there are
```

**Web Scraper:**
```
Create an Actor that scrapes product prices from a given URL and saves them to a dataset
```

**Custom Task:**
```
Build an Actor that generates random quotes and saves them with timestamps
```

## 📋 Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `userPrompt` | string | Yes | Natural language description of what your Actor should do |

## 📤 Output

The Actor outputs a single dataset item with the following structure:

```json
{
  "status": "success|failed",
  "actorId": "xyz123",
  "consoleUrl": "https://console.apify.com/actors/xyz123",
  "actorName": "generated-actor-name",
  "actorTitle": "Generated Actor Title",
  "buildId": "build123",
  "iterations": 1,
  "message": "Actor built successfully",
  "error": null,
  "generatedFiles": ["src/main.py", ".actor/actor.json", ...],
  "requirements": {
    "actor_type": "scraper",
    "description": "...",
    "dependencies": ["apify", "requests"]
  }
}
```

## 🏗️ How It Works

Spielberg follows a four-phase pipeline:

### Phase 1: Intent Analysis
- Analyzes your natural language prompt
- Extracts technical requirements
- Determines Actor type and dependencies
- Generates structured specifications

### Phase 2: Code Generation
- Uses GPT-4 to generate complete Actor source code
- Creates all necessary files:
  - `src/main.py` - Core Actor logic
  - `.actor/actor.json` - Actor metadata
  - `.actor/input_schema.json` - Input validation
  - `Dockerfile` - Container configuration
  - `requirements.txt` - Dependencies
  - `README.md` - Documentation

### Phase 3: Deployment
- Creates Actor in your Apify account using the API
- Uploads source code
- Triggers build
- Returns Actor ID and console URL

### Phase 4: Validation & Fixing
- Monitors build progress
- If build fails:
  - Fetches error logs
  - Sends logs to GPT-4 for analysis
  - Generates fixed code
  - Updates Actor and rebuilds
  - Repeats up to 3 times

## 🛠️ Technical Details

### Architecture

- **Language**: Python 3.13
- **Framework**: Apify SDK
- **AI Model**: OpenAI GPT-4 Turbo
- **API**: Apify API v2

### Dependencies

- `apify>=1.7.0` - Apify SDK
- `apify-client>=1.7.0` - Apify API client
- `openai>=1.0.0` - OpenAI API client
- `aiohttp>=3.9.0` - Async HTTP client

### Modules

- `intent_analyzer.py` - Intent analysis and requirements generation
- `actor_generator.py` - Actor code generation
- `deployer.py` - Apify API integration and deployment
- `validator.py` - Build monitoring and error fixing
- `main.py` - Main orchestrator

## 📊 Limitations

### Current Version (1.0)

- Only generates Python Actors
- Basic to intermediate complexity Actors
- Maximum 3 error fix iterations
- Single-file Actor structures
- Requires GPT-4 API access

### Future Enhancements

- JavaScript/TypeScript Actor support
- Multi-file complex architectures
- Template library for common patterns
- Actor cloning and modification
- Automated testing of generated Actors

## 💰 Cost Considerations

Each Spielberg run makes several OpenAI API calls:

- Intent Analysis: ~500-1000 tokens
- Code Generation: ~2000-4000 tokens
- Error Fixing (if needed): ~1000-2000 tokens per iteration

**Estimated cost per run**: $0.10 - $0.50 USD

## 🐛 Troubleshooting

### "OPENAI_API_KEY environment variable is required"
- Make sure you've set the `OPENAI_API_KEY` in Actor environment variables
- The key should have access to GPT-4 models

### "APIFY_TOKEN is required for deployment"
- This should be automatically available when running on Apify platform
- If running locally, set `APIFY_TOKEN` environment variable

### Build fails multiple times
- Check the build logs in the Actor console
- Try being more specific in your prompt
- Simplify the Actor requirements

### Generated Actor doesn't work as expected
- Review the generated code in the Actor's source tab
- Modify the code directly if needed
- Try running Spielberg again with a more detailed prompt

## 📚 Best Practices

### Writing Good Prompts

**Be Specific:**
✅ "Create an Actor that scrapes article titles and URLs from a blog"
❌ "Create a scraper"

**Include Input/Output Details:**
✅ "Accept a startUrl input and save results with title, price, and link fields"
❌ "Scrape products"

**Mention Special Requirements:**
✅ "Handle pagination and extract all products, limit to 100 items"
❌ "Get all products"

## 🤝 Contributing

This is version 1.0 of Spielberg. Future versions may include:

- More sophisticated error recovery
- Support for multiple programming languages
- Template-based generation
- Custom Actor modification
- Integration with Git repositories

## 📄 License

This Actor is part of the Apify platform ecosystem.

## 🔗 Links

- [Apify Platform](https://apify.com)
- [Apify Documentation](https://docs.apify.com)
- [OpenAI Platform](https://platform.openai.com)

---

**Generated by**: Spielberg v1.0  
**Model**: Claude Sonnet 4.5  
**Last Updated**: December 6, 2025

