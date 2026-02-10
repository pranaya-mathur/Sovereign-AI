# Development Notes

## 2026-02-10

Spent way too much time debugging timeout issues. Turns out regex patterns were causing catastrophic backtracking on certain inputs. Fixed by adding length limits and timeout protection.

Still not happy with the semantic detector performance. Takes forever to initialize on Windows. Need to figure out why HuggingFace keeps making network calls.

## 2026-02-08  

Started integrating the LLM agent tier. Groq API works well but Ollama setup is a pain. Might just drop Ollama support.

Decision caching is working but I'm not sure about the cache key strategy. Currently using hash of input text but this might miss semantically similar inputs.

## 2026-02-05

Initial commit. Basic regex detection is working. Copied some patterns from other projects, need to customize for our use case.

API structure is messy right now. Need to refactor the dependencies module.

## Todo Later

- The policy.yaml structure is confusing. Should simplify.
- Way too many test files in root directory. Move them.
- Documentation is scattered everywhere.
- Need to decide on final architecture before adding more features.
- Consider rewriting tier router logic - current implementation is convoluted.

## Questions

- Do we really need 3 tiers? Maybe 2 is enough?
- Should we use Redis for caching or stick with in-memory?
- How to handle multilingual inputs?
- What's the right threshold for semantic similarity?

## Bugs to Fix

- [ ] Windows timeout issues
- [ ] Slow embedding model loading
- [ ] False positives on acronym detection  
- [ ] Memory leak in long-running processes?
- [ ] API sometimes returns 500 on valid inputs
