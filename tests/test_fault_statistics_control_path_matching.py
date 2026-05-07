import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAULT_STATS_CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "FaultStatisticsControl.js"
)
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
API_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "utils" / "api.js"


class FaultStatisticsControlPathMatchingTestCase(unittest.TestCase):
    def test_fault_mode_cache_busts_fault_statistics_control(self) -> None:
        source = MAP_MODES_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "'controls/FaultStatisticsControl.js?v=top5-path-reverse-2'",
            source,
        )
        self.assertIn(
            "'utils/api.js?v=path-pagination-1'",
            source,
        )

    def test_reversed_top5_path_matches_path_name_fallback(self) -> None:
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(FAULT_STATS_CONTROL_PATH)!r}, 'utf8')
              + '\\nglobalThis.FaultStatisticsControl = FaultStatisticsControl;';
            const sandbox = {{
              console,
              window: {{}},
              requestAnimationFrame: () => 0,
              cancelAnimationFrame: () => {{}},
            }};
            vm.runInNewContext(source, sandbox);

            const control = new sandbox.FaultStatisticsControl();
            const paths = [{{
              type: 'Feature',
              geometry: {{ type: 'LineString', coordinates: [[119.4, 32.4], [119.5, 32.8]] }},
              properties: {{ id: 1, name: '高邮-江都' }},
            }}];
            const matched = control.findMatchingPathsByEndpoints(paths, '江都', ['高邮']);
            if (matched.length !== 1 || matched[0].properties.name !== '高邮-江都') {{
              throw new Error(`expected reversed name fallback match, got ${{matched.length}}`);
            }}
            """
        )

        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_path_metadata_fetch_follows_paginated_api_results(self) -> None:
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(API_JS_PATH)!r}, 'utf8');
            const calls = [];
            const sandbox = {{
              console,
              window: {{}},
              fetch: async (url, options) => {{
                calls.push(url);
                return {{
                  ok: true,
                  status: 200,
                  json: async () => {{
                    if (calls.length === 1) {{
                      return {{
                        results: [],
                        next: '/api/plugins/otnfaults/paths/?limit=50&offset=50',
                      }};
                    }}
                    return {{
                      results: [{{
                        id: 42,
                        name: '高邮-江都',
                        geometry: [[119.4, 32.4], [119.5, 32.8]],
                        site_a: {{ id: 100, name: '高邮' }},
                        site_z: {{ id: 101, name: '江都' }},
                      }}],
                      next: null,
                    }};
                  }},
                }};
              }},
            }};
            vm.runInNewContext(source, sandbox);

            sandbox.window.OTNFaultMapAPI.fetchPaths('token').then((paths) => {{
              if (calls.length !== 2) {{
                throw new Error(`expected two paginated fetches, got ${{calls.length}}`);
              }}
              if (paths.length !== 1 || paths[0].properties.name !== '高邮-江都') {{
                throw new Error(`expected second-page path metadata, got ${{paths.length}}`);
              }}
            }}).catch((error) => {{
              console.error(error);
              process.exit(1);
            }});
            """
        )

        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_path_metadata_fetch_prefers_api_token_when_csrf_exists(self) -> None:
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(API_JS_PATH)!r}, 'utf8');
            let requestHeaders = null;
            const sandbox = {{
              console,
              window: {{ OTNMapConfig: {{ csrfToken: 'csrf-from-config' }} }},
              document: {{ cookie: 'csrftoken=csrf-from-cookie' }},
              fetch: async (url, options) => {{
                requestHeaders = options.headers;
                return {{
                  ok: true,
                  status: 200,
                  json: async () => ({{ results: [], next: null }}),
                }};
              }},
            }};
            vm.runInNewContext(source, sandbox);

            sandbox.window.OTNFaultMapAPI.fetchPaths('netbox-api-token').then(() => {{
              if (requestHeaders.Authorization !== 'Token netbox-api-token') {{
                throw new Error(`expected Authorization token header, got ${{requestHeaders.Authorization}}`);
              }}
              if (requestHeaders['X-CSRFToken'] !== 'csrf-from-cookie') {{
                throw new Error(`expected CSRF header from cookie, got ${{requestHeaders['X-CSRFToken']}}`);
              }}
            }}).catch((error) => {{
              console.error(error);
              process.exit(1);
            }});
            """
        )

        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
