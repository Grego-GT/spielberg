# Spielberg: AI-Powered Actor Generator - Product Requirements Document

## 1. Overview

**Product Name:** Spielberg  
**Version:** 1.0  
**Type:** Meta-Actor (Actor that creates other Actors)  
**Platform:** Apify

### 1.1 Purpose

Spielberg is an AI-powered meta-actor that enables users to create custom Apify Actors using natural language descriptions. It leverages OpenAI's GPT-4 to understand user intent, generate production-ready Actor code, deploy to the Apify platform, and iteratively fix any issues that arise during deployment.

### 1.2 Target Users

- Developers who want to quickly prototype Actors
- Non-technical users who need custom scrapers or automation tools
- Teams that need to rapidly deploy multiple similar Actors
- Anyone exploring the Apify platform without deep Actor development knowledge

## 2. Functional Requirements

### 2.1 Input Requirements

**Primary Input:**
- `userPrompt` (string, required): Natural language description of the desired Actor functionality
  - Format: Free-form text (textarea)
  - Examples:
    - "Create an Actor that scrapes product prices from Amazon"
    - "Build a tool that monitors cryptocurrency prices and saves them to a dataset"
    - "Make an Actor that downloads images from Instagram posts"

**Authentication:**
- `OPENAI_API_KEY` (environment variable, required): OpenAI API key for GPT-4 access
  - Configured as Actor secret in Apify Console
  - Not exposed in input schema
  - Validated at runtime

**Apify API Token:**
- Automatically available via Apify SDK when running on platform
- Required for creating and managing Actors programmatically

### 2.2 Output Requirements

**Primary Output (Dataset):**
```json
{
  "actorId": "string",
  "consoleUrl": "string",
  "status": "success|failed",
  "buildLogs": "string",
  "errorMessage": "string|null",
  "iterations": "number",
  "generatedFiles": ["array of file paths"]
}
```

**Fields:**
- `actorId`: Unique ID of the created Actor
- `consoleUrl`: Direct link to Actor in Apify Console
- `status`: Final deployment status
- `buildLogs`: Latest build logs (for debugging)
- `errorMessage`: Error details if deployment failed
- `iterations`: Number of fix attempts made
- `generatedFiles`: List of all files created

### 2.3 Core Functionality

#### Phase 1: Intent Analysis & Requirements Generation
**Input:** User's natural language prompt  
**Process:**
- Send prompt to OpenAI GPT-4 with specialized system prompt
- Extract Actor type (scraper, processor, automation)
- Identify required dependencies and libraries
- Determine data structures (input schema, output format)
- Generate technical requirements document

**Output:** Structured requirements object
```python
{
  "actor_name": "string",
  "actor_title": "string", 
  "description": "string",
  "actor_type": "scraper|processor|automation",
  "dependencies": ["list of packages"],
  "input_fields": [{"name", "type", "description"}],
  "output_structure": {"field definitions"},
  "technical_notes": "string"
}
```

#### Phase 2: Actor Code Generation
**Input:** Requirements from Phase 1  
**Process:**
- Use OpenAI to generate all required Actor files
- Apply Apify best practices from AGENTS.md
- Generate:
  - `src/main.py`: Core logic with async patterns
  - `src/__init__.py`: Package initialization
  - `.actor/actor.json`: Actor metadata
  - `.actor/input_schema.json`: Input validation
  - `Dockerfile`: Container configuration
  - `requirements.txt`: Python dependencies
  - `README.md`: Actor documentation

**Output:** Dictionary mapping file paths to content

#### Phase 3: Actor Deployment
**Input:** Generated files from Phase 2  
**Process:**
1. Create Actor via Apify API POST `/v2/acts`
2. Create Actor version with source files
3. Trigger build via Build Actor API
4. Monitor build progress
5. Wait for build completion

**Output:** Deployment metadata
```python
{
  "actor_id": "string",
  "build_id": "string",
  "build_status": "BUILDING|SUCCEEDED|FAILED",
  "console_url": "string"
}
```

#### Phase 4: Validation & Iterative Fixing
**Input:** Build result from Phase 3  
**Process:**
- If build succeeds: Return success
- If build fails:
  1. Fetch build logs from Apify API
  2. Send logs + original requirements to OpenAI
  3. Request corrected code
  4. Update Actor version with fixes
  5. Trigger new build
  6. Repeat up to 3 times

**Output:** Final status with complete build information

### 2.4 Error Handling

**Scenarios:**
1. **Missing OpenAI API Key**: Fail immediately with clear error message
2. **OpenAI API Error**: Retry once, then fail with error details
3. **Build Failure**: Attempt to fix up to 3 times
4. **Apify API Error**: Log detailed error and fail gracefully
5. **Invalid Requirements**: Return error with explanation

**Logging Strategy:**
- Log all major steps with `Actor.log.info()`
- Log errors with `Actor.log.error()`
- Include timestamps for debugging
- Store detailed logs in Key-Value store for post-mortem analysis

## 3. Technical Requirements

### 3.1 Architecture

**Design Pattern:** Pipeline architecture with four distinct stages
- Each stage is a separate module
- Clear interfaces between stages
- Testable components
- Error propagation through stages

**Module Structure:**
```
spielberg/
├── .actor/
│   ├── actor.json
│   └── input_schema.json
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py              # Orchestrator
│   ├── intent_analyzer.py   # Phase 1
│   ├── actor_generator.py   # Phase 2
│   ├── deployer.py          # Phase 3
│   └── validator.py         # Phase 4
├── Dockerfile
├── requirements.txt
└── README.md
```

### 3.2 Dependencies

**Required Python Packages:**
- `apify>=1.0.0` - Apify SDK for Actor runtime
- `apify-client>=1.0.0` - Apify API client for creating Actors
- `openai>=1.0.0` - OpenAI API client for GPT-4
- `aiohttp>=3.8.0` - Async HTTP client

### 3.3 OpenAI Integration

**Model:** GPT-4 (gpt-4 or gpt-4-turbo)  
**Usage:**
- Intent Analysis: ~500-1000 tokens
- Code Generation: ~2000-4000 tokens
- Error Fixing: ~1000-2000 tokens per iteration

**Estimated Cost per Run:** $0.10 - $0.50 depending on complexity

**System Prompts:**
- Intent Analyzer: Focused on extracting structured requirements
- Code Generator: Includes AGENTS.md best practices, example Actor structure
- Error Fixer: Includes original requirements + build errors

### 3.4 Apify API Integration

**Endpoints Used:**
1. `POST /v2/acts` - Create new Actor
2. `POST /v2/acts/{actorId}/versions` - Create Actor version
3. `POST /v2/acts/{actorId}/builds` - Trigger build
4. `GET /v2/acts/{actorId}/builds/{buildId}` - Get build status
5. `GET /v2/acts/{actorId}/builds/{buildId}/log` - Get build logs

**Authentication:** Via `APIFY_TOKEN` environment variable (automatically set by platform)

### 3.5 Performance Requirements

- **Maximum Execution Time:** 15 minutes
- **Memory Limit:** 2048 MB
- **Cold Start Time:** < 30 seconds
- **Average End-to-End Time:** 2-5 minutes

### 3.6 Constraints

**Limitations:**
- Maximum 3 fix iterations to prevent infinite loops
- Only Python Actors supported in v1.0
- No support for multi-file complex architectures
- Generated Actors are basic/intermediate complexity
- No custom Dockerfile modifications beyond base selection

**Rate Limits:**
- OpenAI: Subject to user's API rate limits
- Apify API: 60 requests/second per resource

## 4. Non-Functional Requirements

### 4.1 Reliability
- Handle OpenAI API timeouts gracefully
- Retry transient Apify API failures
- Validate all inputs before processing
- Fail fast on unrecoverable errors

### 4.2 Security
- Never log API keys
- Use environment variables for secrets
- Validate Actor names to prevent injection
- Sanitize generated code for malicious patterns

### 4.3 Maintainability
- Clear code structure with comments
- Type hints in Python code
- Comprehensive error messages
- Logging at all major decision points

### 4.4 Usability
- Clear input field descriptions
- Helpful examples in input schema
- Detailed error messages for users
- Link to generated Actor in output

## 5. Success Criteria

### 5.1 Minimum Viable Product (MVP)
- ✅ Accept natural language prompts
- ✅ Generate basic "Hello World" type Actors
- ✅ Deploy to Apify successfully
- ✅ Return console link to created Actor
- ✅ Handle at least one error fix iteration

### 5.2 Success Metrics
- **Build Success Rate:** >70% on first attempt
- **Fix Success Rate:** >85% after 3 iterations
- **Average Generation Time:** <5 minutes
- **User Satisfaction:** Positive feedback on generated Actors

## 6. Future Enhancements (Post-v1.0)

### 6.1 Phase 2 Features
- Support for JavaScript/TypeScript Actors
- Complex multi-file architectures
- Custom Dockerfile generation
- Integration with existing Git repositories
- Actor cloning and modification
- Template library for common patterns

### 6.2 Phase 3 Features
- Visual Actor builder integration
- A/B testing of generated code
- Performance optimization suggestions
- Automated testing of generated Actors
- Cost estimation for Actor runs
- Publishing to Apify Store

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each module independently
- Mock OpenAI and Apify API calls
- Validate data transformations
- Test error handling paths

### 7.2 Integration Tests
- End-to-end test with simple prompts
- Test error recovery scenarios
- Validate API interactions
- Check output format

### 7.3 Test Cases

**Test Case 1: Simple Hello World**
- Input: "Create an Actor that logs 'Hello World' and saves it to dataset"
- Expected: Successfully deployed Actor, build succeeds

**Test Case 2: Basic Data Processing**
- Input: "Create an Actor that takes a list of URLs as input and counts them"
- Expected: Actor with proper input schema, successful deployment

**Test Case 3: Error Recovery**
- Input: Intentionally ambiguous prompt
- Expected: System attempts fixes, provides helpful error if fails

## 8. Documentation

### 8.1 User Documentation
- README.md with usage examples
- Input field descriptions in schema
- Example prompts for common use cases
- Troubleshooting guide

### 8.2 Developer Documentation
- Code comments in all modules
- Architecture decision record
- API integration guide
- Extension guide for future developers

## 9. Deployment

### 9.1 Environment Variables
- `OPENAI_API_KEY`: Required, set by user in Actor settings
- `APIFY_TOKEN`: Auto-provided by platform

### 9.2 Actor Configuration
- Memory: 2048 MB
- Timeout: 900 seconds (15 minutes)
- Build tag: latest
- Public: No (initially private)

## 10. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OpenAI generates invalid code | High | Medium | Iterative fixing with build validation |
| OpenAI API rate limits | Medium | Low | Implement exponential backoff |
| Apify API changes | High | Low | Use official client library, pin versions |
| Generated Actors are too complex | Medium | Medium | Limit scope in prompts, validate complexity |
| Security vulnerabilities in generated code | High | Low | Code sanitization, security scanning |

## 11. Appendix

### 11.1 Glossary
- **Meta-Actor**: An Actor that creates other Actors
- **Intent Analysis**: Process of understanding user requirements from natural language
- **Build**: Compilation of Actor source code into runnable Docker image
- **Iteration**: One cycle of error detection and fixing

### 11.2 References
- [Apify Actor Documentation](https://docs.apify.com/platform/actors)
- [Apify API Reference](https://docs.apify.com/api/v2)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [AGENTS.md Best Practices](test/AGENTS.md)

