from __future__ import annotations

import shutil
import subprocess
import base64
import json
import re
from typing import Sequence

from .curriculum import ContractError


class ObsidianCLI:
    def __init__(self, vault: str | None = None) -> None:
        executable = shutil.which("obsidian")
        if not executable:
            raise ContractError("obsidian CLI is not available")
        self.executable = executable
        self.vault = vault

    def run(self, arguments: Sequence[str], *, target_vault: bool = True) -> str:
        command = [self.executable]
        if target_vault and self.vault:
            command.append(f"vault={self.vault}")
        command.extend(arguments)
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0 or "Unknown command" in combined or "Error:" in combined:
            raise ContractError(f"obsidian command failed: {combined.strip()}")
        return completed.stdout.strip()

    def read(self, path: str) -> str:
        return self.run(["read", f"path={path}"])

    def create(self, path: str, content: str) -> None:
        self.run(["create", f"path={path}", f"content={content}", "silent"])

    def move(self, source: str, target: str) -> None:
        self.run(["move", f"path={source}", f"to={target}"])

    def eval(self, operation: str, payload: dict) -> dict:
        encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        code = f'''(async () => {{
          const payload = JSON.parse(atob("{encoded}"));
          const adapter = app.vault.adapter;
          if ("{operation}" === "write") {{
            const exists = await adapter.exists(payload.path);
            const current = exists ? await adapter.read(payload.path) : null;
            if (payload.expected === null && exists) throw new Error("target already exists");
            if (payload.expected !== null && current !== payload.expected) throw new Error("compare-and-swap failed");
            await adapter.write(payload.path, payload.content);
            const actual = await adapter.read(payload.path);
            if (actual !== payload.content) throw new Error(`read-back mismatch: ${{payload.path}}`);
            return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, path: payload.path}});
          }}
          if ("{operation}" === "mkdir") {{
            if (!(await adapter.exists(payload.path))) await adapter.mkdir(payload.path);
            if (!(await adapter.exists(payload.path))) throw new Error(`mkdir read-back mismatch: ${{payload.path}}`);
            return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, path: payload.path}});
          }}
          if ("{operation}" === "remove-if-exists") {{
            if (await adapter.exists(payload.path)) await adapter.rmdir(payload.path, true);
            if (await adapter.exists(payload.path)) throw new Error(`remove read-back mismatch: ${{payload.path}}`);
            return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, path: payload.path}});
          }}
          if ("{operation}" === "batch-create") {{
            const createdFiles = [];
            const createdDirectories = [];
            try {{
              for (const path of [...payload.directories, ...payload.files.map((item) => item.path)]) {{
                if (await adapter.exists(path)) throw new Error(`target already exists: ${{path}}`);
              }}
              for (const path of payload.directories) {{
                createdDirectories.push(path);
                await adapter.mkdir(path);
                if (!(await adapter.exists(path))) throw new Error(`mkdir read-back mismatch: ${{path}}`);
              }}
              for (const item of payload.files) {{
                createdFiles.push(item.path);
                await adapter.write(item.path, item.content);
              }}
              for (const item of payload.files) {{
                if (await adapter.read(item.path) !== item.content) throw new Error(`read-back mismatch: ${{item.path}}`);
              }}
              return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, files: createdFiles}});
            }} catch (error) {{
              const rollbackErrors = [];
              for (const path of createdFiles.reverse()) {{
                try {{
                  if (await adapter.exists(path)) await adapter.remove(path);
                  if (await adapter.exists(path)) throw new Error(`file still exists: ${{path}}`);
                }} catch (rollbackError) {{
                  rollbackErrors.push(`${{path}}: ${{String(rollbackError)}}`);
                }}
              }}
              for (const path of createdDirectories.reverse()) {{
                try {{
                  if (await adapter.exists(path)) await adapter.rmdir(path, true);
                  if (await adapter.exists(path)) throw new Error(`directory still exists: ${{path}}`);
                }} catch (rollbackError) {{
                  rollbackErrors.push(`${{path}}: ${{String(rollbackError)}}`);
                }}
              }}
              if (rollbackErrors.length) throw new Error(`batch-create failed and rollback was incomplete: ${{String(error)}}; ${{rollbackErrors.join("; ")}}`);
              throw error;
            }}
          }}
          if ("{operation}" === "batch-write") {{
            const originals = [];
            try {{
              for (const item of payload.files) {{
                const exists = await adapter.exists(item.path);
                const current = exists ? await adapter.read(item.path) : null;
                if (current !== item.expected) throw new Error(`compare-and-swap failed: ${{item.path}}`);
                originals.push({{path: item.path, exists, content: current}});
              }}
              for (const item of payload.files) await adapter.write(item.path, item.content);
              for (const item of payload.files) {{
                if (await adapter.read(item.path) !== item.content) throw new Error(`read-back mismatch: ${{item.path}}`);
              }}
              return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, files: payload.files.map((item) => item.path)}});
            }} catch (error) {{
              const rollbackErrors = [];
              for (const item of originals.reverse()) {{
                try {{
                  if (item.exists) await adapter.write(item.path, item.content);
                  else if (await adapter.exists(item.path)) await adapter.remove(item.path);
                  const restored = await adapter.exists(item.path);
                  if (restored !== item.exists) throw new Error(`existence mismatch: ${{item.path}}`);
                  if (item.exists && await adapter.read(item.path) !== item.content) throw new Error(`content mismatch: ${{item.path}}`);
                }} catch (rollbackError) {{
                  rollbackErrors.push(`${{item.path}}: ${{String(rollbackError)}}`);
                }}
              }}
              if (rollbackErrors.length) throw new Error(`batch-write failed and rollback was incomplete: ${{String(error)}}; ${{rollbackErrors.join("; ")}}`);
              throw error;
            }}
          }}
          if ("{operation}" === "list-directories") {{
            const listing = await adapter.list(payload.path);
            return "LEARN_TOPIC_JSON:" + JSON.stringify({{ok: true, folders: listing.folders.sort()}});
          }}
          throw new Error("unsupported operation");
        }})()'''
        raw = self.run(["eval", f"code={code}"])
        matches = re.findall(r"LEARN_TOPIC_JSON:(\{.*\})", raw)
        try:
            if len(matches) != 1:
                raise ValueError(f"expected one result sentinel, got {len(matches)}")
            result = json.loads(matches[0])
        except (json.JSONDecodeError, ValueError) as error:
            raise ContractError(f"obsidian eval returned invalid JSON: {raw}") from error
        if result.get("ok") is not True:
            raise ContractError(f"obsidian eval {operation} failed")
        return result
