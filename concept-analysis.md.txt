---
name: conceptual-analysis
description: Analyse names and concepts in the code, looking for places the domain model and variable names could be clearer.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

Do a conceptual analysis of the code. For each argument and variable assignment, the question is what is this thing, and how are we referring to it in this bit of code? We're looking out in particular for places where we call different things by the same name, especially when related concepts could be confused. We're also looking for the same thing called different names in different places.
