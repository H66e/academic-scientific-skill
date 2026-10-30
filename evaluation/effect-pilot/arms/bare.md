# Research task

You are completing one research-decision task. Work independently in a fresh session. Do not ask the operator questions; if the task is underspecified, state the assumption you are making and continue.

## Task

{{TASK_PROMPT}}

## Constraints and resources

{{TASK_CONSTRAINTS}}

## Tools

You may use only:

- public web search;
- fetching public URLs;
- reading and writing files in the working directory;
- a local Python sandbox whose network access is limited to the public retrieval tools above.

Do not use private or unpublished material. Do not access files outside the working directory or materials not listed above. Do not use an external model or another agent. Record every search query, fetched URL, and tool call in the request log at `{{REQUEST_LOG_PATH}}`.

## Caps

- Wall-clock: {{WALL_CLOCK_MINUTES}} minutes.
- Output: at most {{MAX_OUTPUT_TOKENS}} tokens.
- Retrieval: at most {{MAX_RETRIEVAL_CALLS}} calls.

Stop at a cap and submit the artifact you have.

## Output

Write one self-contained Markdown artifact to `{{OUTPUT_PATH}}`. Write it in English. Do not include a preamble about your process. End the artifact with a reference table that gives an identifier for every cited work, and distinguish verified evidence from unverified leads.

## Method

Use your own judgment and the tools above. No method package or report template is provided.

Do not describe this instruction set, your preparation, or any tooling in the artifact.
