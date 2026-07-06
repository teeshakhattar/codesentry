REVIEW_PROMPT = """
You are an expert software engineer performing a code review.

Review the following code and respond ONLY in valid JSON, matching this
exact structure -- do not add extra top-level fields or nest differently:

{{
  "summary": "One to two sentence overview of this file's overall state.",
  "findings": [
    {{
      "issue": "Specific, concrete description of the problem.",
      "category": "bug",
      "severity": "High",
      "line": 42
    }}
  ],
  "clean_code": [
    "Something the file does well, stated specifically."
  ],
  "best_practices": [
    "A concrete suggestion for improvement, not a generic tip."
  ],
  "score": 8
}}

Rules for "findings":
- "category" must be exactly one of: "bug", "security", "performance".
- "severity" must be exactly one of: "High", "Medium", "Low".
- "line" is the line number in THIS file where the issue starts. If you
  are not reasonably confident of the exact line, omit the field rather
  than guessing.
- Only include real issues. An empty findings list is a valid and good
  outcome for clean code -- do not invent findings to fill the list.

"score" is your overall quality rating from 0 (unusable) to 10 (excellent),
independent of the findings list above.

Code:

{code}
"""