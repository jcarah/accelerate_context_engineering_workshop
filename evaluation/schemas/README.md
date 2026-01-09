# Schemas Directory

This directory contains JSON schemas used for evaluation.

## Note on Payload Schemas

The `retail_payload_schema.json` (or any return payload schema) is intended for future use when the root agent's output is strictly controlled and follows a defined schema. 

Currently, the `retail_location_strategy` agent's primary output mechanism is via state variables populated by its sub-agents, rather than a single structured return payload from the root agent itself. Therefore, evaluation relies heavily on the `retail_state_variables_schema.json` to identify and extract the necessary data points from the session state.
