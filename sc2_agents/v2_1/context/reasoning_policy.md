# V2.1 Reasoning Policy

Use deterministic evidence as the source of truth. The final answer must preserve the endpoint requested by the user and every requested output field.

Do not collapse different graph roles into one concept:
- A direct producer is the entity that trains, builds, morphs, researches, or otherwise creates another entity.
- A prerequisite or requirement is an entity needed before an action is available.
- A tech-chain node is part of a prerequisite path and may not be the direct producer.
- An ability result is the entity produced by executing an ability.
- A morph source and morph result are directional; in `A morphs_into B`, A is the source and B is the result.
- An alias or variant may share statistics with a normal form but still be a different canonical endpoint.

When a subanswer contains several candidates, first check whether the user's wording selects one role. If the wording does not uniquely select one role, ask a narrower follow-up. If ambiguity remains, give a detailed answer with every defensible candidate and the requested fields for each one.

When a researcher, producer, source unit, or prerequisite returns several candidate branches, evaluate the candidate set as a set. Do not inspect only the first candidate and then finalize. Ask the DataSubAgent to compare all candidates against the relation phrase that still needs to be satisfied.

Do not output a failure message just because the round limit is near. If any useful facts have been gathered, provide the best supported answer, state what is confirmed, and state what remains uncertain.
