# Caveman skill (bundled)

Ultra-compressed agent communication from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (MIT).

**Why bundle here:** Trading agents poll heartbeat, read long SKILL files, and post signals often. Caveman cuts token use on replies and status without losing technical accuracy.

**Install globally (optional):**

```bash
curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash
```

**Use in this project:** Load `skills/caveman/SKILL.md` alongside `skills/ai4trade/SKILL.caveman.md` for a shorter platform bootstrap.

Trigger: `/caveman` or "talk like caveman". Stop: "normal mode".
