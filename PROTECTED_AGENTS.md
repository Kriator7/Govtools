# Protected business agents

Mr North, realtor-agent, and TrueHold Wellness are production infrastructure. Do **not** delete, empty, or rename their folders as a cleanup step.

CI runs `python scripts/check_protected_agents.py` on every push and pull request.

## If an agent must actually be retired

Two different people have to confirm. One agent’s “already working elsewhere” comment is not enough.

1. Copy `.github/DELETE_AGENT_CONFIRMATION.example.json` to `.github/DELETE_AGENT_CONFIRMATION.json`.
2. Set `agent_id` to exactly one of: `mr-north`, `realtor-agent`, `truehold-wellness`.
3. Write a real `reason` (not the placeholder).
4. Person 1 fills `confirmer_1.name` and sets `confirmer_1.phrase` to:

   `I CONFIRM DELETE OF <agent_id> FROM BUSINESS INFRASTRUCTURE`

5. Person 2 fills `confirmer_2.name` (must differ from person 1) and sets `confirmer_2.phrase` to:

   `I INDEPENDENTLY CONFIRM DELETE OF <agent_id> FROM BUSINESS INFRASTRUCTURE`

6. Set `warning` to exactly:

   `THIS DELETES PRODUCTION BUSINESS INFRASTRUCTURE`

7. Only then remove that agent’s files. CI still fails if another protected agent is missing.
8. After the deletion merges, remove `.github/DELETE_AGENT_CONFIRMATION.json` so it cannot be reused.

The example file is not a valid override. A confirmation file left in the repo while all agents are still present also fails CI.
