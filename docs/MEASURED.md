# What was measured (November 2026)

This page reports what happened when the recursive tree was measured against
simpler ways of asking the same question. Most of it is a negative result, and
two defaults of the tool changed because of it.

## Summary

- On questions a model can answer from memory, the tree did not find more than
  the same number of plain calls on the undivided question, and one plain call
  covered more of an expert checklist than the tree's final answer.
- The earlier synthesis prompt dropped a third to a half of what the leaves had
  found. A prompt that asks to keep the specific findings keeps about nine
  tenths. It is now the default.
- The earlier explore prompt listed every angle. The default now lets a node
  answer an atomic question itself; the median number of sub-questions fell from
  27 to 10.5.
- Two judges from different model families disagreed about which answer was
  "better" when asked for a preference. Counting stated points against a
  published list is what the two families agreed on, so the numbers below are
  counts.
- With a web search tool, on questions about events after the models' training:
  see [Search](#search).

## How it was measured

**Questions and keys.** Seven open questions, each paired with one published
expert source that enumerates its points. One key point per enumerated item,
99 points in all.

| Question | Source of the key | Points |
|---|---|---|
| What makes a startup successful? | Paul Graham, "The 18 Mistakes That Kill Startups" | 18 |
| What makes good coffee? | National Coffee Association, drip brewing guide | 9 |
| What makes a good API design? | Joshua Bloch, "Bumper-Sticker API Design" | 38 |
| PostgreSQL or SQLite for a small team's internal tool? | SQLite project, "Appropriate Uses For SQLite" | 5 |
| What causes inflation? | IMF, "Inflation: Prices on the Rise" | 4 |
| How does a hash table handle collisions? | Wikipedia, "Hash table" | 16 |
| Should a 10-person company adopt microservices? | Martin Fowler, "Microservice Trade-Offs" and "Microservice Prerequisites" | 9 |

**Arms.** The tree explored with `claude-opus-5-5`, answered leaves with
`claude-haiku-5-5` and synthesized with `claude-opus-5-5`, depth 2. The plain
call is one `claude-opus-5-5` call with the leaf prompt. No arm had tools in
these runs.

**Matching.** A matcher model reads one answer and the list of key points, plus
three decoy points taken from other questions, and marks the points the answer
states. Each answer is matched twice with the points in a different order, and a
point counts only when both runs mark it. Two matcher families were used,
`claude-sonnet-5-5` and `gpt-6.1-sol`; both numbers are given, in that order.
The matchers marked 51 of 51 planted points in a calibration, and across the
runs they marked 0 to 2 decoys out of 84 to 402.

## Results

### One plain call covered more than the tree's answer

Answers held to about 700 words. Mean share of the key covered:

| Arm | Sonnet matcher | Sol matcher |
|---|---|---|
| One plain call | 0.62 | 0.59 |
| Tree with the node-decides explore prompt | 0.50 | 0.44 |
| Tree with the earlier explore prompt | 0.38 | 0.38 |
| Same leaves, a direct answer-the-question synthesis prompt | 0.52 | 0.42 |

On the coffee question the earlier tree spent 17 of its 24 sub-questions on
growing, processing, chemistry, culture and history. Its answer stated 1 or 2 of
the 9 brewing points; the plain call stated 6 or 7.

### The leaves found about as much as repeating the question

Points of 99, natural length:

| Text matched | Sonnet matcher | Sol matcher |
|---|---|---|
| The tree's 195 leaf answers together | 57 | 67 |
| 195 plain answers to the undivided questions, same model and prompt | 60 | 63 |
| One plain call asked for about 2,500 words | 54 | 59 |
| One ordinary plain call | 49 | 47 |
| The tree's final answer, earlier synthesis prompt | 35 | 35 |
| The tree's final answer, current synthesis prompt | 54 | 60 |

A tree without tools is one model asked smaller questions. The fair control for
"decomposition finds more" is the same number of calls on the whole question,
and against that control the leaves were not ahead (-3 and +4 points).

### The earlier synthesis prompt lost what the leaves found

The earlier prompt asked for connections, tensions and a nuanced perspective.
Its answer lacked 23 of the 57 points its own leaves stated (33 of 67 for the
second matcher). The current prompt asks for a direct answer that keeps every
specific finding. On the same leaves it kept 51 of 57 and 59 of 67, won 6 of 7
questions against the earlier prompt for both matchers and lost none. Its
answers are two to four times longer (roughly 34,000 characters against 13,000),
so part of the gain is length.

A second draw of the earlier prompt scored 38 and 35, so the two draws of one
prompt differ by 0 to 3 points in total. Question by question they differ more:
the bench's own rule, written before the run, called the result undecided for
that reason. The totals are far outside that noise.

### Preference judges disagreed

At equal answer length, a `claude-sonnet-5-5` judge preferred the tree's answer
to the plain call's on 7 of 8 questions. A `gpt-6.1-sol` judge preferred the
plain call on 6 and the tree on none. Both judges had passed the same
calibration. A preference from one model family is not evidence here.

## Search

The runs above gave no arm a tool. A separate run asked seven questions about
events of September to November 2026, after the models' training: national
elections, the Nobel prizes, Atlantic storms, ten central-bank decisions, Emmy
categories, and the United States governor and Senate races of 3 November (34
points each). The keys, 119 points, were built the same day by web-searching
agents from pages they fetched. Searching seats had a web search and a page
fetch tool and nothing else.

Points of 119:

| Arm | Sonnet matcher | Sol matcher | Searches | Metered cost |
|---|---|---|---|---|
| One `claude-opus-5-5` call, no tools | 0 | 3 | 0 | $0.28 |
| One searching `claude-haiku-5-5` agent | 112 | 109 | | |
| One searching `claude-opus-5-5` agent | 117 | 117 | 40 | $1.91 |
| 57 searching haiku agents on the undivided questions | 113 | 113 | 433 | $5.78 |
| The tree's 57 searching haiku leaves | 115 | 112 | 295 | $4.25 |
| Synthesis of those leaves, current prompt | 116 | 116 | 0 | $1.39 |

- A search tool is what answers a question about recent facts. Without one the
  model stated 0 to 3 of 119 points.
- The tree added nothing to one searching agent: 2 to 5 fewer points, at two to
  three times the metered cost and seven to eleven times the searches.
- Both 34-item sets were stated in full by every searching arm, the single
  small agent included. One page lists each of them and the fetch returned it
  whole.
- The one place the tree's leaves beat the same number of repeated agents was
  the Emmy question: every haiku agent given the whole question stated the same
  9 of 15 categories, and the leaves stated 15.
- The synthesis lost nothing the leaves stated.

Not tested: a set that no page lists and that runs to several hundred items.
The keys were built with the same search tool, so a fact the tool cannot find is
not in them. One draw per arm.

On the Python CLI `-w/--web` is still not wired. This run used the model CLI's
own search tool directly.

## What changed in the tool

- The default explore prompt lets a node answer an atomic question directly.
  `--thorough` restores the earlier prompt.
- The default synthesis prompt is the keeping one, in the Python API and in
  `deep-research.sh`. `Provider.synthesize(..., connect=True)` restores the
  earlier prompt.
- The Python CLI never made a synthesis call; its report is the exploration plus
  every child's answer. `--synthesize` adds one answer per exploring node.

## Limits

- Each key is one author's list. Coverage of it is not correctness, and an
  answer can be good in ways the list does not hold.
- Seven questions, one generation per arm and question, with one extra draw as
  the only measure of generation noise.
- All answers came from Claude models. Leaves and plain repeats used one model.
- The seven sources are public and probably in every model's training data, the
  same for all arms.
- The keeping synthesis prompt was written after the result it answers.
- Equal numbers of calls are not equal amounts of text: the leaves wrote 1.07
  million characters, the plain repeats 0.72 million.
