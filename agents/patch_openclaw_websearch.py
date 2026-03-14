#!/usr/bin/env python3
"""
Patch OpenClaw to add 'openai' as a web_search provider.

This patches the installed OpenClaw (2026.3.12) to use OpenAI's Responses API
with web_search_preview for web searches, reusing the existing OPENAI_API_KEY.

Run after installing/updating OpenClaw:
    python3 agents/patch_openclaw_websearch.py

The upstream PR (openclaw/openclaw#28333) adds this natively. Once that ships
in a release, this patch is no longer needed and can be removed.
"""

import os
import subprocess
import sys

DIST_DIR = None

def find_dist_dir():
    result = subprocess.run(
        ["npm", "root", "-g"], capture_output=True, text=True
    )
    root = result.stdout.strip()
    candidate = os.path.join(root, "openclaw", "dist")
    if os.path.isdir(candidate):
        return candidate
    print(f"Error: OpenClaw dist not found at {candidate}", file=sys.stderr)
    sys.exit(1)


def patch_zod_schemas(dist_dir):
    """Add z.literal("openai") to all Zod schema provider unions."""
    count = 0
    for root, dirs, files in os.walk(dist_dir):
        for f in files:
            if not f.endswith(".js"):
                continue
            path = os.path.join(root, f)
            content = open(path, "r").read()
            if 'z.literal("openai")' in content:
                continue
            if 'z.literal("kimi")' not in content:
                continue
            content = content.replace(
                'z.literal("kimi")',
                'z.literal("kimi"),\n\t\tz.literal("openai")',
            )
            open(path, "w").write(content)
            count += 1
    print(f"  Zod schemas: {count} files patched")


def patch_web_search_bundles(dist_dir):
    """Patch all bundled JS files that contain the web search runtime."""
    count = 0
    for root, dirs, files in os.walk(dist_dir):
        for f in files:
            if not f.endswith(".js"):
                continue
            path = os.path.join(root, f)
            content = open(path, "r").read()
            if "function runGrokSearch" not in content:
                continue

            original = content

            # 1. Add OPENAI constants
            if "OPENAI_SEARCH_ENDPOINT" not in content:
                content = content.replace(
                    'const XAI_API_ENDPOINT = "https://api.x.ai/v1/responses";\nconst DEFAULT_GROK_MODEL = "grok-4-1-fast";',
                    'const XAI_API_ENDPOINT = "https://api.x.ai/v1/responses";\nconst OPENAI_SEARCH_ENDPOINT = "https://api.openai.com/v1/responses";\nconst DEFAULT_OPENAI_SEARCH_MODEL = "gpt-5.2";\nconst DEFAULT_GROK_MODEL = "grok-4-1-fast";',
                )

            # 2. Add runOpenAISearch function
            if "function runOpenAISearch" not in content:
                content = content.replace(
                    "\t});\n}\nfunction extractKimiMessageText(message) {",
                    '\t});\n}\nasync function runOpenAISearch(params) {\n\tconst body = {\n\t\tmodel: params.model,\n\t\tinput: [{\n\t\t\trole: "user",\n\t\t\tcontent: params.query\n\t\t}],\n\t\ttools: [{ type: "web_search_preview" }]\n\t};\n\treturn withTrustedWebSearchEndpoint({\n\t\turl: OPENAI_SEARCH_ENDPOINT,\n\t\ttimeoutSeconds: params.timeoutSeconds,\n\t\tinit: {\n\t\t\tmethod: "POST",\n\t\t\theaders: {\n\t\t\t\t"Content-Type": "application/json",\n\t\t\t\tAuthorization: `Bearer ${params.apiKey}`\n\t\t\t},\n\t\t\tbody: JSON.stringify(body)\n\t\t}\n\t}, async (res) => {\n\t\tif (!res.ok) return await throwWebSearchApiError(res, "OpenAI");\n\t\tconst data = await res.json();\n\t\tconst { text: extractedText, annotationCitations } = extractGrokContent(data);\n\t\treturn {\n\t\t\tcontent: extractedText ?? "No response",\n\t\t\tcitations: (data.citations ?? []).length > 0 ? data.citations : annotationCitations,\n\t\t\tinlineCitations: data.inline_citations\n\t\t};\n\t});\n}\nfunction extractKimiMessageText(message) {',
                )

            # 3. Add "openai" to resolveSearchProvider
            if 'if (raw === "openai") return "openai";' not in content:
                content = content.replace(
                    'if (raw === "perplexity") return "perplexity";\n\tif (raw === "") {',
                    'if (raw === "perplexity") return "perplexity";\n\tif (raw === "openai") return "openai";\n\tif (raw === "") {',
                )

            # 4. Add openai auto-detection (lowest priority)
            if 'auto-detected "openai"' not in content:
                content = content.replace(
                    "\t}\n\treturn \"brave\";\n}\nfunction resolveBraveConfig",
                    '\t\tif (process.env.OPENAI_API_KEY) {\n\t\t\tlogVerbose(\'web_search: no provider configured, auto-detected "openai" from OPENAI_API_KEY\');\n\t\t\treturn "openai";\n\t\t}\n\t}\n\treturn "brave";\n}\nfunction resolveBraveConfig',
                )

            # 5. Add openai missing key payload
            if "missing_openai_api_key" not in content:
                content = content.replace(
                    'if (provider === "kimi") return {\n\t\terror: "missing_kimi_api_key",',
                    'if (provider === "openai") return {\n\t\terror: "missing_openai_api_key",\n\t\tmessage: "web_search (openai) needs an OpenAI API key. Set OPENAI_API_KEY in the Gateway environment.",\n\t\tdocs: "https://docs.openclaw.ai/tools/web"\n\t};\n\tif (provider === "kimi") return {\n\t\terror: "missing_kimi_api_key",',
                )

            # 6. Add openai dispatch case
            if 'params.provider === "openai"' not in content:
                old = 'writeCache(SEARCH_CACHE, cacheKey, payload, params.cacheTtlMs);\n\t\treturn payload;\n\t}\n\tif (params.provider === "kimi") {'
                new = 'writeCache(SEARCH_CACHE, cacheKey, payload, params.cacheTtlMs);\n\t\treturn payload;\n\t}\n\tif (params.provider === "openai") {\n\t\tconst openaiApiKey = process.env.OPENAI_API_KEY ?? "";\n\t\tconst openaiModel = DEFAULT_OPENAI_SEARCH_MODEL;\n\t\tconst { content, citations, inlineCitations } = await runOpenAISearch({\n\t\t\tquery: params.query,\n\t\t\tapiKey: openaiApiKey,\n\t\t\tmodel: openaiModel,\n\t\t\ttimeoutSeconds: params.timeoutSeconds\n\t\t});\n\t\tconst payload = {\n\t\t\tquery: params.query,\n\t\t\tprovider: params.provider,\n\t\t\tmodel: openaiModel,\n\t\t\ttookMs: Date.now() - start,\n\t\t\texternalContent: {\n\t\t\t\tuntrusted: true,\n\t\t\t\tsource: "web_search",\n\t\t\t\tprovider: params.provider,\n\t\t\t\twrapped: true\n\t\t\t},\n\t\t\tcontent: wrapWebContent(content),\n\t\t\tcitations,\n\t\t\tinlineCitations\n\t\t};\n\t\twriteCache(SEARCH_CACHE, cacheKey, payload, params.cacheTtlMs);\n\t\treturn payload;\n\t}\n\tif (params.provider === "kimi") {'
                content = content.replace(old, new, 1)

            # 7. Patch apiKey resolution
            if 'provider === "openai" ? (process.env.OPENAI_API_KEY' not in content:
                content = content.replace(
                    'provider === "grok" ? resolveGrokApiKey(grokConfig) : provider === "kimi"',
                    'provider === "grok" ? resolveGrokApiKey(grokConfig) : provider === "openai" ? (process.env.OPENAI_API_KEY ?? "") : provider === "kimi"',
                )

            # 8. Add openai to WEB_SEARCH_PROVIDERS array
            if content.count('"openai"') < 2:
                old_arr = '"perplexity"\n];'
                new_arr = '"perplexity",\n\t"openai"\n];'
                content = content.replace(old_arr, new_arr, 1)

            if content != original:
                open(path, "w").write(content)
                count += 1
                print(f"  Runtime:     {f}")

    print(f"  Runtime bundles: {count} files patched")


def main():
    dist_dir = find_dist_dir()
    version = subprocess.run(
        ["openclaw", "--version"], capture_output=True, text=True
    ).stdout.strip()
    print(f"Patching OpenClaw ({version}) at {dist_dir}")
    print()
    patch_zod_schemas(dist_dir)
    patch_web_search_bundles(dist_dir)
    print()
    print("Done. Restart agent gateways to pick up changes.")
    print('Config: set tools.web.search.provider to "openai" in openclaw.json')


if __name__ == "__main__":
    main()
