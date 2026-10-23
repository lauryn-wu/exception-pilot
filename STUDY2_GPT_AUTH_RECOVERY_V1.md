# Recovery of confirmed authentication rejections

This is an explicit execution amendment to the GPT matched explanation experiment at commit `13b1538bda605b248d5035ef7cb5c22b7b602248`. Its scientific plan, 192 unique requests, prompts, model settings, scoring, and existing journals remain unchanged. The original frozen code contract remains `59ce83e4ffea153e1ad737d83a4c6fd97ff06d93117f39295e5dff8f07e4887f`.

## Reason for the amendment

The original runner permanently holds every failed dispatch. A run with four saved responses then received HTTP 401 with error code `invalid_api_key`. The user corrected the credential and successfully fetched model metadata. A confirmed authentication rejection contains no scientific answer to select or replace, so one documented retry of that exact request is permitted.

The amendment does not authorize resampling a returned answer, including an incorrect, invalid, refused, or truncated answer. Timeouts, ambiguous attempts, other HTTP errors, and a 401 without the exact saved `invalid_api_key` proof remain held. A failed or ambiguous recovery attempt is also held; it is not automatically retried.

## Evidence and execution

The additive root module `exception_study2_gpt_auth_recovery.py` reads the existing sealed plan using the original implementation. It adds an `auth-recovery-v1` directory containing amendment and attempt evidence. The original authentication failure, its raw HTTP response, the four saved responses, and their request/start/terminal records are preserved byte for byte.

The recovery attempt sends the identical scientific payload with the corrected credential supplied through the environment. It uses a separate attempt identity, records its own start and terminal state, and never substitutes a synthetic successful record into the original journal. Recovery evidence is bound to the original plan, rejected request, rejection evidence, and recovery implementation.

The wrapper's live run command performs eligible recovery work first, then uses the original runner for never-started requests. Its invocation limit counts both recovery dispatches and new original dispatches. The wrapper does not load a local model or make a live request unless `--live-openai` is supplied.

## Analysis and accounting

Combined analysis selects the original return where one exists and the single recorded recovery return only for an eligible authentication-rejected case. It explicitly reports the original rejection and selected attempt. The four-block estimators and all scoring rules are unchanged. Completion still requires 192 returned scientific outcomes, with returned invalid outcomes handled by the original fixed-budget rules.

HTTP dispatches and unique scientific cases are distinct: the observed run can finish with 192 scientific responses and 193 HTTP dispatches, including the authentication rejection. Pricing subtotals do not silently assign zero to missing usage or claim an exact bill.

Use the recovery wrapper for subsequent inspection, analysis, and export. Combined local reports are saved as `analysis-auth-recovery.json` and `analysis-auth-recovery.md`. The original commands intentionally continue to display the original failed attempt as unresolved. The wrapper's export includes both original and recovery journals, the amendment, combined `analysis.json` and `analysis.md`, raw returned outputs, review sheet, and checksums.

## Resume the existing run

Check out the recovery commit supplied with this amendment. Keep the existing run directory. Do not run `prepare`, change settings, delete a failed journal, or create a replacement experiment.

```sh
cd "$HOME/exception-pilot-gpt-explanation"
source .venv/bin/activate
export GPT_RUN="$HOME/study2-runs/gpt-explanation-v1-13b1538"

# This inspection is offline.
python -m exception_study2_gpt_auth_recovery inspect --output "$GPT_RUN"

# Uses OPENAI_API_KEY already set in this Terminal. This makes paid requests.
python -m exception_study2_gpt_auth_recovery run \
  --output "$GPT_RUN" --live-openai --max-new 192

python -m exception_study2_gpt_auth_recovery analyze --output "$GPT_RUN"
python -m exception_study2_gpt_auth_recovery export \
  --output "$GPT_RUN" \
  --destination "${GPT_RUN}-auth-recovered-$(date -u +%Y%m%dT%H%M%SZ).zip"
```

If a new Terminal needs the corrected key, enter it without placing it in command history:

```sh
export OPENAI_API_KEY="$(python -c 'import getpass; print(getpass.getpass("OpenAI API key: ").strip())')"
```

Offline tests use mocked HTTP responses only. No credentials, live API calls, or new model outputs are used to validate this amendment.
