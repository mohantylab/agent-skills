"""
skill_loader.py — loads skill folders (skills/<folder>/)
Each folder has: SKILL.md, PROMPT.md, INSTRUCTIONS.md, examples.json
"""
import re, json, logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class SkillDefinition:
    id: str
    name: str
    folder: str
    version: str
    enabled: bool
    icon: str
    color: str
    category: str
    description: str
    landing_examples: list
    trigger_keywords: list
    tools: list
    schema_hint: Optional[str]
    output_format: dict
    data_governance: dict
    prompts: dict
    instructions: str
    examples: list
    folder_path: str = ""


class SkillLoader:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)

    def load_all(self) -> dict:
        skills = {}
        if not self.skills_dir.exists():
            raise FileNotFoundError(f"Skills dir not found: {self.skills_dir}")
        for folder in sorted(self.skills_dir.iterdir()):
            if not folder.is_dir():
                continue
            try:
                skill = self._load_folder(folder)
                if skill and skill.enabled:
                    skills[skill.id] = skill
                    logger.info("  loaded skill: %s  tools=%s", skill.id, skill.tools)
            except Exception as e:
                logger.error("  failed: %s — %s", folder.name, e)
        logger.info("Total skills: %d", len(skills))
        return skills

    def reload(self, skill_id: str, skills: dict) -> dict:
        for folder in self.skills_dir.iterdir():
            if folder.is_dir():
                skill = self._load_folder(folder)
                if skill and skill.id == skill_id:
                    skills[skill_id] = skill
                    return skills
        raise FileNotFoundError(f"Skill folder for '{skill_id}' not found")

    def _load_folder(self, folder: Path) -> Optional[SkillDefinition]:
        skill_md = folder / "SKILL.md"
        if not skill_md.exists():
            return None
        sections = self._split(skill_md.read_text(encoding="utf-8"))
        meta     = self._kv(sections.get("metadata", ""))
        landing  = [v for k, v in sorted(meta.items()) if k.startswith("landing_example")]
        prompt_md = folder / "PROMPT.md"
        instr_md  = folder / "INSTRUCTIONS.md"
        ex_json   = folder / "examples.json"
        return SkillDefinition(
            id              = meta.get("id", folder.name),
            name            = meta.get("name", folder.name),
            folder          = folder.name,
            version         = meta.get("version", "1.0.0"),
            enabled         = meta.get("enabled", "true").lower() == "true",
            icon            = meta.get("icon", "🔧"),
            color           = meta.get("color", "#4f8ef7"),
            category        = meta.get("category", "general"),
            description     = meta.get("description", ""),
            landing_examples= landing,
            trigger_keywords= self._list(sections.get("trigger_keywords", "")),
            tools           = self._list(sections.get("tools", "")),
            schema_hint     = sections.get("schema_hint", "").strip() or None,
            output_format   = self._kv(sections.get("output_format", "")),
            data_governance = self._kv(sections.get("data_governance", "")),
            prompts         = self._prompts(prompt_md) if prompt_md.exists() else {},
            instructions    = instr_md.read_text(encoding="utf-8") if instr_md.exists() else "",
            examples        = json.loads(ex_json.read_text()).get("examples", []) if ex_json.exists() else [],
            folder_path     = str(folder),
        )

    def _prompts(self, path: Path) -> dict:
        prompts, cur, buf = {}, None, []
        for line in path.read_text(encoding="utf-8").splitlines():
            h2 = re.match(r'^##\s+(.+)', line)
            if h2:
                if cur: prompts[cur] = "\n".join(buf).strip()
                cur = h2.group(1).strip().lower().replace(" ", "_")
                buf = []
            else:
                buf.append(line)
        if cur: prompts[cur] = "\n".join(buf).strip()
        return prompts

    def _split(self, text: str) -> dict:
        sections, cur, buf = {}, None, []
        for line in text.splitlines():
            h2 = re.match(r'^##\s+(.+)', line)
            if h2:
                if cur: sections[cur] = "\n".join(buf).strip()
                cur = h2.group(1).strip().lower().replace(" ", "_")
                buf = []
            else: buf.append(line)
        if cur: sections[cur] = "\n".join(buf).strip()
        return sections

    def _kv(self, text: str) -> dict:
        r = {}
        for line in text.splitlines():
            m = re.match(r'-\s+([\w_]+):\s+(.+)', line)
            if m: r[m.group(1).strip()] = m.group(2).strip()
        return r

    def _list(self, text: str) -> list:
        items = []
        for line in text.splitlines():
            line = re.sub(r'^-\s*', '', line).strip()
            if line:
                items.extend([k.strip().lower() for k in line.split(",") if k.strip()])
        return items


class SkillRouter:
    def __init__(self, skills: dict):
        self.skills = skills

    def route(self, question: str, force_skill_id: str = None) -> SkillDefinition:
        if force_skill_id and force_skill_id in self.skills:
            return self.skills[force_skill_id]
        q = question.lower()
        best_id, best_score = None, 0
        for sid, skill in self.skills.items():
            score = sum(1 for kw in skill.trigger_keywords if kw in q)
            if score > best_score:
                best_score, best_id = score, sid
        fallback = "data_analysis" if "data_analysis" in self.skills else next(iter(self.skills))
        return self.skills[best_id or fallback]
