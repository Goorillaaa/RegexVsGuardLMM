# RegexVsGuardLMM
Comparing two guardrails that do the same job, deciding if a response is safe or unsafe, but with opposite approaches: a keyword filter (Regex) and a small trained Guard LLM. The heart of the project is the speed versus intelligence trade-off: the regex is super fast but fragile, the Guard LLM is slower but can catch hidden and obfuscated attacks.
