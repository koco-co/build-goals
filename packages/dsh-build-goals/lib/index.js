/**
 * Bundled build-goals skill provider.
 *
 * Registers the nine build-goals skills (shape-idea, build-skill,
 * build-plugin, build-prd, vibe-coding, build-readme, build-agents-md,
 * handoff, obsidian-learn-topic) on the host `skills` registry. Summaries come from the generated
 * lib/skills.generated.js manifest; bodies are read lazily from the mirrored
 * assets. Users can override any bundled skill by placing a same-named
 * bundle in ~/.dsh/skills/ (filesystem provider rank 400 beats the bundled
 * rank 600).
 *
 * @module @koco-co/dsh-build-goals
 */
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SKILLS } from "./skills.generated.js";

const PROVIDER_NAME = "build-goals";

// Inlined from @deepseek-ai/dsh-skill's exported BUNDLED_SKILL_RANK (600).
// Inlining keeps this bundle free of runtime peer imports, so it resolves
// identically under link:, file:, and git installs even with the profile's
// autoInstallPeers disabled.
const BUNDLED_SKILL_RANK = 600;

const CANDIDATES = SKILLS.map((skill) => {
  const resourceBase = {
    kind: "directory",
    path: fileURLToPath(
      new URL(`../assets/skills/${skill.name}/`, import.meta.url),
    ),
  };
  return {
    name: skill.name,
    description: skill.description,
    invocation: {
      modelInvocable: skill.modelInvocable,
      userInvocable: skill.userInvocable,
    },
    provider: PROVIDER_NAME,
    source: "bundled",
    resourceBase,
    rank: BUNDLED_SKILL_RANK,
    locator: new URL(`../assets/skills/${skill.name}/SKILL.md`, import.meta.url),
  };
});

const provider = {
  name: PROVIDER_NAME,
  list: () => Promise.resolve(CANDIDATES),
  async get(candidate) {
    const skill = SKILLS.find((entry) => entry.name === candidate.name);
    if (skill === undefined) {
      throw new Error(`unknown build-goals skill: ${candidate.name}`);
    }
    return {
      name: candidate.name,
      description: candidate.description,
      invocation: candidate.invocation,
      provider: PROVIDER_NAME,
      source: "bundled",
      resourceBase: candidate.resourceBase,
      content: await readFile(candidate.locator, "utf8"),
    };
  },
};

/** Cordis plugin name. */
export const name = "build-goals-skill-provider";
/** Service required by the bundled provider. */
export const inject = ["skills"];
/** Register the bundled build-goals provider on `ctx.skills`. */
export function apply(ctx) {
  ctx.skills.registerProvider(() => provider);
}
