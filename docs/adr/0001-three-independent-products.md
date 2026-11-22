# Three independent products, no shared runtime

Govtools holds Mr North, realtor-agent, and TrueHold Wellness in one git repo so they can share CI and agent workflow, not because they are one system. They do not share Telegram bots, databases, or application code; mixing tokens or domain language is treated as a defect. We keep them as sibling packages instead of a shared platform so a change in one product cannot silently page or debit another.
