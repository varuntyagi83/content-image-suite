---
description: Manage Content Image Suite activation. Toggle which platform skills are loaded at session start without reinstalling. Subcommands: list, enable <name>, disable <name>, enable-all, disable-all, status.
---

You are managing activation of the Content Image Suite for the user.

The suite stages every skill under `~/.claude/skills-suite/` at install time. Only the skills symlinked into `~/.claude/skills/` are loaded by Claude Code at session start, so disabling a skill is the right move when the user does not plan to post on that platform — it reduces token cost at every session start.

Run the controller script and report its output to the user.

Argument parsing:
- No arguments, or "list": run `bash ~/.claude/skills-suite/bin/suite.sh list`
- "enable <name>" or "on <name>": run `bash ~/.claude/skills-suite/bin/suite.sh enable <name>`
- "disable <name>" or "off <name>": run `bash ~/.claude/skills-suite/bin/suite.sh disable <name>`
- "enable-all" or "all on": run `bash ~/.claude/skills-suite/bin/suite.sh enable-all`
- "disable-all" or "all off": run `bash ~/.claude/skills-suite/bin/suite.sh disable-all`
- "status": run `bash ~/.claude/skills-suite/bin/suite.sh status`
- Anything else: run `bash ~/.claude/skills-suite/bin/suite.sh --help`

Short aliases the controller accepts for skill names: linkedin, medium, twitter (or x), instagram (or ig), meta (or facebook, fb), infographic.

After running enable or disable, remind the user that the change takes effect on next session start. Do not restart Claude Code yourself.

If the controller script is missing, tell the user: "The /suite controller is not installed. Run install-team.sh from the Content Image Suite folder."

The user's argument is: $ARGUMENTS
