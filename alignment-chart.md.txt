---
name: alignment-chart
description: Analyse functions in the code according to their correctness and collaboration
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

Here's a little conceptual model so we can do some analysis of this package. A function is 'lawful good' if it's correct in itself, and it forces its neighbours to be correct. A lawful good function knows when it gets invalid data, and it will always raise the alarm when it does that, in a way that makes the culprit easy to spot. A chaotic good function is a chill guy who's happy to help out his colleagues, even when they're commiting crimes. If some other function is giving it bad inputs and there's a fix, it will just fix it and get on with the job. If one function tries to pass it one type as an input and another function's calling it with a different type, whatever just accept the union. Evil functions are where the bugs are. 'Neutral' is maybe not _incorrect_, but it keeps up a pattern that's hard to tell apart from chaotic or evil. Neutral stuff makes you think a lot to decide whether it's a problem in this instance.
