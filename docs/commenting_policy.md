# Commenting policy

Every meaningful executable Python and JavaScript line must have an inline or immediately adjacent comment that explains what it does.

## Python and JavaScript

- Comment every import, assignment, branch, loop, function, class, return, raise, API call, and state mutation.
- Comments should explain purpose, not merely repeat syntax.
- Closing braces, blank lines, and pure punctuation are exempt.

## HTML, CSS, YAML, OpenAPI, and Markdown

- Use section-level comments because per-line comments are not always syntactically valid or readable.
- JSON cannot contain comments; create adjacent Markdown documentation for complex JSON.

## Enforcement

Run:

```bash
python scripts/check_comment_density.py
```

The checker reports meaningful executable lines that appear to lack comments. CI may treat these as warnings during bootstrap and as required checks after the baseline is normalized.
