# Expanded Qwen3-32B exploratory screen

Bounded exploratory diagnostic: next four frozen selection worlds (2–5), 16 task cells
(8 visible reasoning, 8 matched direct), 2048 token maximum each.
Separate directory; does not modify or replace the v4 pilot or its 512-token protocol.
Strict output format and Markdown-tolerant final answers are reported separately.
Requires original LIVE pilot, valid technical gate, pinned backend identity, and original source files.
Failed/interrupted operations are not automatically resent.

Run on the OLD Pod whose GPU/backend identity matches the original v4 pilot:

    cd /workspace/exception-pilot
    git status --short
    git fetch origin codex/study2-qwen-expanded-screen
    git switch --no-track -c codex/study2-qwen-expanded-screen FETCH_HEAD
    source /workspace/venvs/study2-qwen3/bin/activate
    export RUN_V4=$(cat /workspace/study2-v4-run-path.txt)
    export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EXPANDED_SCREEN=$(mktemp -d /workspace/exception-pilot/runs/qwen3-expanded-screen-XXXXXXXX)
    echo "$EXPANDED_SCREEN" | tee /workspace/study2-expanded-screen-path.txt
    python scripts/study2_qwen_expanded_screen.py --source "$RUN_V4" --output "$EXPANDED_SCREEN"

Check that the preceding command prepared a plan with no inference.
Then explicitly authorize the 16 operations:

    python scripts/study2_qwen_expanded_screen.py --source "$RUN_V4" --output "$EXPANDED_SCREEN" --live-qwen

Outputs:
    $EXPANDED_SCREEN/screen-results.json
    $EXPANDED_SCREEN/screen-traces.txt

Re-run rsync AFTER inference finishes to move these new outputs to the new Pod's persistent Network Volume.
Do not terminate the old Pod before verifying copies. Do not treat exploratory evidence as confirmation.
