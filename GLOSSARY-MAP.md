# Glossary Map

Govtools is three independent products plus repo-wide rules. Product language
never crosses folders. `/grill-with-docs` writes terms into the matching
glossary the moment they resolve.

## Contexts

- [Govtools repo](./GLOSSARY.md): Cross-product repo rules only — protected agents, CI, Grill with Docs. ADRs: `docs/adr/`
- [Mr North](./mr_north/GLOSSARY.md): TrueHold crypto alerts and hourly BLS on @Mr_North_bot. ADRs: `mr_north/docs/adr/`
- [Realtor acquisition](./realtor-agent/GLOSSARY.md): Nevada realtor matching on @PirateEye_bot. ADRs: `realtor-agent/docs/adr/`
- [TrueHold Wellness](./truehold-wellness/GLOSSARY.md): Order/inbox workflow on @THWellness_bot. ADRs: `truehold-wellness/docs/adr/`

## Relationships

- **None across products.** These agents do not share Telegram bots, databases, or application code.
- **Govtools repo → all three**: repo-wide protection and Grill with Docs live at the root; product terms stay in the product glossary.
- **Desktop Jarvis is not a context here.** FatihMakes Mark-LVII lives on the Mac at `projects/Jarvis`, not in this git tree and not in TrueHold Wellness.
